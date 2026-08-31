"""AP reconciliation service (15.9 §5.1) — consumer-only orchestration.

Never mutates ``bookings``/``booking_lines``/``costing_*`` (chốt #1). The only
crossings into those aggregates are read-only lookups via ``BookingRepository``
(existing ``get_line_by_id`` plus the new ``get_line_by_voucher_ref``) and
``CostingRepository.get_sheet_by_id`` (for the F2 penalty-currency guard).

Deliberate scope triage for this pass (documented, not silently dropped):
payment-side ``fx_variance_sheet_minor`` and the multi-sheet-currency guard
(``FX_MULTI_SHEET_CURRENCY``) are not computed — §1.2 calls this combination
rare for a boutique DMC (single sheet currency almost always). Price variance
at match time (the load-bearing part of §1.2) is fully implemented.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from core.kernel import ActorRef, generate_id, validate_currency
from core.rules.finance_rules import (
    AllocationInput,
    decompose_variance,
    derive_invoice_status,
    expected_cost_minor_for_booking_line,
    is_within_tolerance,
    suggest_penalty_expected,
    to_sheet_minor,
    validate_invoice_transition,
    validate_payment_allocations,
)
from db.models.booking import BookingLine
from db.models.supplier_invoice import ApPayment, SupplierInvoice, SupplierInvoiceLine
from notification.domain.events import EventType
from repositories.booking_repository import BookingRepository
from repositories.costing_repository import CostingRepository
from repositories.supplier_invoice_repository import (
    ApPaymentDuplicateError,
    SupplierInvoiceLineMatchTakenError,
    SupplierInvoiceRepository,
    SupplierInvoiceRevisionRaceError,
    SupplierInvoiceSlotTakenError,
)
from repositories.supplier_repository import SupplierRepository
from schemas.v2.finance_ap import (
    ApPaymentAllocationResponseSchema,
    ApPaymentResponseSchema,
    LineActionRequestSchema,
    MatchLineRequestSchema,
    RecordPaymentRequestSchema,
    SupplierInvoiceLineResponseSchema,
    SupplierInvoiceLinesUpsertSchema,
    SupplierInvoiceListItemSchema,
    SupplierInvoiceResponseSchema,
    SupplierInvoiceUpdateSchema,
)
from services.outbox_service import OutboxService

INVOICE_ID_PREFIX = "spi"
PAYMENT_ID_PREFIX = "apy"
_PRE_APPROVAL_STATUSES = ("received", "matched", "disputed")
_MATCHED_LIKE_STATUSES = ("auto_matched", "manual_matched", "waived")


class APValidationError(ValueError):
    """Business-rule violation (maps to 422)."""


class APConflictError(ValueError):
    """CAS mismatch or lifecycle conflict (maps to 409)."""

    def __init__(self, message: str, *, current_revision: int) -> None:
        super().__init__(message)
        self.current_revision = current_revision


class ApReconciliationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = SupplierInvoiceRepository(session)
        self.supplier_repository = SupplierRepository(session)
        self.booking_repository = BookingRepository(session)
        self.costing_repository = CostingRepository(session)

    # ------------------------------------------------------------------ reads

    async def get_invoice(self, invoice_id: str) -> SupplierInvoiceResponseSchema | None:
        invoice = await self.repository.get_invoice_by_id(invoice_id)
        if invoice is None:
            return None
        return await self._to_response(invoice)

    async def list_invoices(
        self,
        *,
        supplier_id: str | None,
        status: str | None,
        due_within_days: int | None,
        overdue_only: bool,
        search: str | None,
        today: date,
    ) -> list[SupplierInvoiceListItemSchema]:
        invoices = await self.repository.list_invoices(
            supplier_id=supplier_id,
            status=status,
            due_within_days=due_within_days,
            overdue_only=overdue_only,
            search=search,
            today=today,
        )
        items: list[SupplierInvoiceListItemSchema] = []
        for invoice in invoices:
            matched = sum(1 for line in invoice.lines if line.match_status in _MATCHED_LIKE_STATUSES)
            item = SupplierInvoiceListItemSchema.model_validate(invoice)
            item.matched_line_count = matched
            item.total_line_count = len(invoice.lines)
            items.append(item)
        return items

    # --------------------------------------------------------------- writes

    async def create_invoice(self, payload, *, actor: ActorRef, idempotency_key: str | None) -> SupplierInvoiceResponseSchema:
        if idempotency_key:
            existing = await self.repository.get_invoice_by_idempotency_key(idempotency_key)
            if existing is not None:
                return await self._to_response(existing)

        supplier = await self.supplier_repository.get_by_id(payload.supplier_id)
        if supplier is None:
            raise APValidationError(f"Supplier '{payload.supplier_id}' was not found.")

        due_date = payload.due_date or (payload.invoice_date + timedelta(days=supplier.credit_terms_days))
        values: dict[str, Any] = {
            "supplier_id": payload.supplier_id,
            "invoice_number": payload.invoice_number,
            "invoice_date": payload.invoice_date,
            "due_date": due_date,
            "currency": validate_currency(payload.currency),
            "gross_total_minor": payload.gross_total_minor,
            "tax_minor": payload.tax_minor,
            "file_ref": payload.file_ref,
            "idempotency_key": idempotency_key,
            "notes": payload.notes,
            "created_by": actor.serialize(),
            "updated_by": actor.serialize(),
        }
        try:
            invoice = await self.repository.insert_invoice(invoice_id=generate_id(INVOICE_ID_PREFIX), values=values)
        except SupplierInvoiceSlotTakenError as err:
            raise APConflictError(
                f"Supplier '{payload.supplier_id}' already has an invoice numbered '{payload.invoice_number}', "
                "or the idempotency key was just used by a concurrent write.",
                current_revision=0,
            ) from err
        # Re-fetch with eager-loaded collections — a freshly inserted object's relationship
        # attributes are unloaded, and touching them here would fire a lazy-load outside the
        # greenlet context (async ORM pitfall).
        invoice = await self.repository.get_invoice_by_id(invoice.id)
        return await self._to_response(invoice)

    async def update_header(
        self, invoice_id: str, payload: SupplierInvoiceUpdateSchema, *, actor: ActorRef
    ) -> SupplierInvoiceResponseSchema | None:
        invoice = await self.repository.get_invoice_by_id(invoice_id)
        if invoice is None:
            return None
        self._check_revision(invoice, payload.base_invoice_revision)
        if invoice.status in ("approved", "paid", "void"):
            raise APValidationError(f"Cannot edit a supplier invoice once it is '{invoice.status}'.")

        values: dict[str, Any] = {"updated_by": actor.serialize()}
        for field in ("invoice_number", "invoice_date", "due_date", "file_ref", "notes"):
            value = getattr(payload, field)
            if value is not None:
                values[field] = value
        if payload.currency is not None:
            values["currency"] = validate_currency(payload.currency)
        if payload.gross_total_minor is not None:
            values["gross_total_minor"] = payload.gross_total_minor
        if payload.tax_minor is not None:
            values["tax_minor"] = payload.tax_minor

        if payload.action == "record":
            gate = validate_invoice_transition(invoice.status, "received")
            if not gate.passed:
                raise APValidationError(gate.issues[0].message)
            values["status"] = "received"
        elif payload.action == "void":
            if invoice.allocations:
                raise APValidationError("Cannot void an invoice with recorded payment allocations.")
            gate = validate_invoice_transition(invoice.status, "void")
            if not gate.passed:
                raise APValidationError(gate.issues[0].message)
            values["status"] = "void"

        try:
            invoice = await self.repository.update_header(invoice, values=values, expected_revision=payload.base_invoice_revision)
        except SupplierInvoiceRevisionRaceError as err:
            raise await self._conflict_from_race(invoice_id) from err
        except SupplierInvoiceSlotTakenError as err:
            raise APConflictError("That invoice_number is already used for this supplier.", current_revision=invoice.invoice_revision) from err

        if payload.action == "record":
            await self._emit(invoice, EventType.FINANCE_AP_INVOICE_RECEIVED, actor=actor)
        return await self._to_response(invoice)

    async def upsert_lines(
        self, invoice_id: str, payload: SupplierInvoiceLinesUpsertSchema, *, actor: ActorRef
    ) -> SupplierInvoiceResponseSchema | None:
        invoice = await self.repository.get_invoice_by_id(invoice_id)
        if invoice is None:
            return None
        if invoice.status not in ("draft", "received"):
            raise APValidationError(f"Cannot replace invoice lines while invoice is '{invoice.status}'.")
        self._check_revision(invoice, payload.base_invoice_revision)

        line_values = [
            {
                "line_type": item.line_type,
                "booking_id": item.booking_id,
                "voucher_ref": item.voucher_ref,
                "description": item.description,
                "amount_minor": item.amount_minor,
                "sort_order": item.sort_order,
                "created_by": actor.serialize(),
                "updated_by": actor.serialize(),
            }
            for item in payload.lines
        ]
        try:
            await self.repository.replace_lines(invoice, line_values=line_values, expected_revision=payload.base_invoice_revision)
        except SupplierInvoiceRevisionRaceError as err:
            raise await self._conflict_from_race(invoice_id) from err

        await self._derive_and_apply_status(invoice, actor=actor)
        invoice = await self.repository.get_invoice_by_id(invoice_id)
        return await self._to_response(invoice)

    async def match_line(
        self, invoice_id: str, line_id: int, payload: MatchLineRequestSchema, *, actor: ActorRef
    ) -> SupplierInvoiceResponseSchema | None:
        invoice = await self.repository.get_invoice_by_id(invoice_id)
        if invoice is None:
            return None
        line = self._find_line(invoice, line_id)
        if line is None:
            return None
        if invoice.status not in _PRE_APPROVAL_STATUSES:
            raise APValidationError(f"Cannot match a line while invoice is '{invoice.status}'.")
        self._check_revision(invoice, payload.base_invoice_revision)

        if bool(payload.booking_line_id) == bool(payload.voucher_ref):
            raise APValidationError("Exactly one of bookingLineId or voucherRef is required.")

        booking_line = (
            await self.booking_repository.get_line_by_id(payload.booking_line_id)
            if payload.booking_line_id
            else await self.booking_repository.get_line_by_voucher_ref(payload.voucher_ref)
        )
        if booking_line is None:
            raise APValidationError("No matching booking line was found for this voucher/id.")

        issues: list[str] = []
        snap_ppm: int | None
        if line.line_type == "penalty":
            sheet_currency = await self._sheet_currency_for_booking_line(booking_line) or invoice.currency
            expected_cost_minor, penalty_issue = suggest_penalty_expected(
                cancel_penalty_minor=booking_line.cancel_penalty_minor,
                sheet_currency=sheet_currency,
                invoice_currency=invoice.currency,
            )
            if penalty_issue:
                issues.append(penalty_issue)
            snap_ppm = None  # penalty comparand is already sheet-currency (identity)
        else:
            if invoice.currency != booking_line.cost_currency_snapshot:
                raise APValidationError(
                    {
                        "code": "CURRENCY_MISMATCH",
                        "message": (
                            f"Invoice currency '{invoice.currency}' does not match booking line cost "
                            f"currency '{booking_line.cost_currency_snapshot}'."
                        ),
                    }
                )
            expected_cost_minor = expected_cost_minor_for_booking_line(
                unit_cost_minor_snapshot=booking_line.unit_cost_minor_snapshot,
                qty_unit=booking_line.qty_unit,
                qty_time=booking_line.qty_time,
            )
            snap_ppm = booking_line.fx_rate_ppm_snapshot

        within_tolerance = False
        if expected_cost_minor is not None:
            decomposition = decompose_variance(
                expected_cost_minor=expected_cost_minor, actual_amount_minor=line.amount_minor, snapshot_fx_rate_ppm=snap_ppm
            )
            within_tolerance = is_within_tolerance(
                decomposition.price_variance_sheet_minor, decomposition.expected_sheet_minor, payload.tolerance_bps
            )

        if payload.mode == "auto":
            if expected_cost_minor is None or not within_tolerance:
                raise APValidationError(
                    "Auto-match requires an exact/within-tolerance amount; use manual match with a note instead."
                )
            match_status = "auto_matched"
        else:
            match_status = "manual_matched"
            if expected_cost_minor is not None and not within_tolerance:
                issues.append("TOLERANCE_EXCEEDED")

        raw_variance_minor = None if expected_cost_minor is None else line.amount_minor - expected_cost_minor
        booking_line_id = booking_line.id
        pre_write_revision = invoice.invoice_revision
        values: dict[str, Any] = {
            "booking_id": booking_line.booking_id,
            "booking_line_id": booking_line_id,
            "voucher_ref": booking_line.voucher_ref,
            "expected_cost_minor": expected_cost_minor,
            "variance_minor": raw_variance_minor,
            "match_status": match_status,
            "match_issues_json": issues,
            "match_note": None,
            "updated_by": actor.serialize(),
        }
        try:
            await self.repository.update_line(invoice, line, values=values, expected_revision=payload.base_invoice_revision)
        except SupplierInvoiceRevisionRaceError as err:
            raise await self._conflict_from_race(invoice_id) from err
        except SupplierInvoiceLineMatchTakenError as err:
            # A rollback just expired every object in this session — read only the plain
            # values captured above, never a live attribute (would need a sync reload).
            raise APConflictError(
                f"Booking line '{booking_line_id}' is already matched to another live invoice line — "
                "unmatch/void the other invoice first.",
                current_revision=pre_write_revision,
            ) from err

        await self._derive_and_apply_status(invoice, actor=actor)
        invoice = await self.repository.get_invoice_by_id(invoice_id)
        return await self._to_response(invoice)

    async def line_action(
        self,
        invoice_id: str,
        line_id: int,
        action: Literal["unmatch", "waive", "dispute"],
        payload: LineActionRequestSchema,
        *,
        actor: ActorRef,
    ) -> SupplierInvoiceResponseSchema | None:
        invoice = await self.repository.get_invoice_by_id(invoice_id)
        if invoice is None:
            return None
        line = self._find_line(invoice, line_id)
        if line is None:
            return None
        if invoice.status not in _PRE_APPROVAL_STATUSES:
            raise APValidationError(f"Cannot {action} a line once invoice is '{invoice.status}' (approve locks all lines, §5.4).")
        self._check_revision(invoice, payload.base_invoice_revision)

        if action in ("waive", "dispute") and not payload.note:
            raise APValidationError(f"A note is required to {action} a line.")

        if action == "unmatch":
            values: dict[str, Any] = {
                "booking_id": None,
                "booking_line_id": None,
                "expected_cost_minor": None,
                "variance_minor": None,
                "match_status": "unmatched",
                "match_issues_json": [],
                "match_note": None,
                "updated_by": actor.serialize(),
            }
        elif action == "waive":
            values = {"match_status": "waived", "match_note": payload.note, "updated_by": actor.serialize()}
        else:
            values = {"match_status": "disputed", "match_note": payload.note, "updated_by": actor.serialize()}

        try:
            await self.repository.update_line(invoice, line, values=values, expected_revision=payload.base_invoice_revision)
        except SupplierInvoiceRevisionRaceError as err:
            raise await self._conflict_from_race(invoice_id) from err

        await self._derive_and_apply_status(invoice, actor=actor)
        invoice = await self.repository.get_invoice_by_id(invoice_id)
        return await self._to_response(invoice)

    async def approve(self, invoice_id: str, payload, *, actor: ActorRef) -> SupplierInvoiceResponseSchema | None:
        invoice = await self.repository.get_invoice_by_id(invoice_id)
        if invoice is None:
            return None
        self._check_revision(invoice, payload.base_invoice_revision)
        if invoice.status != "matched":
            raise APValidationError(
                f"Cannot approve from '{invoice.status}' — every line must be matched/waived first (no unmatched/disputed)."
            )
        gate = validate_invoice_transition(invoice.status, "approved")
        if not gate.passed:
            raise APValidationError(gate.issues[0].message)

        try:
            invoice = await self.repository.update_header(
                invoice, values={"status": "approved", "updated_by": actor.serialize()}, expected_revision=payload.base_invoice_revision
            )
        except SupplierInvoiceRevisionRaceError as err:
            raise await self._conflict_from_race(invoice_id) from err

        await self._emit(invoice, EventType.FINANCE_AP_INVOICE_APPROVED, actor=actor)
        return await self._to_response(invoice)

    async def record_payment(
        self, payload: RecordPaymentRequestSchema, *, actor: ActorRef, idempotency_key: str | None
    ) -> ApPaymentResponseSchema:
        if idempotency_key:
            existing = await self.repository.get_payment_by_idempotency_key(idempotency_key)
            if existing is not None:
                return self._to_payment_response(existing)

        if not payload.allocations:
            raise APValidationError("At least one allocation is required.")

        invoice_ids = sorted({alloc.invoice_id for alloc in payload.allocations})
        invoices: dict[str, SupplierInvoice] = {}
        for invoice_id in invoice_ids:
            invoice = await self.repository.get_invoice_by_id(invoice_id)
            if invoice is None:
                raise APValidationError(f"Invoice '{invoice_id}' was not found.")
            invoices[invoice_id] = invoice

        if payload.amount_minor < 0:
            if not payload.reference or not payload.notes:
                raise APValidationError("Negative (reversal) payments require both reference and notes (chốt #9).")
        else:
            for invoice_id, invoice in invoices.items():
                if invoice.status != "approved":
                    raise APValidationError(f"Invoice '{invoice_id}' must be 'approved' before recording a payment.")
            balances = await self.repository.get_balances_for_invoices(invoice_ids)
            invoice_balance_minor = {
                invoice_id: invoices[invoice_id].gross_total_minor - balances.get(invoice_id, 0) for invoice_id in invoice_ids
            }
            gate = validate_payment_allocations(
                payment_amount_minor=payload.amount_minor,
                allocations=[AllocationInput(invoice_id=a.invoice_id, amount_minor=a.amount_minor) for a in payload.allocations],
                invoice_balance_minor=invoice_balance_minor,
            )
            if not gate.passed:
                raise APValidationError("; ".join(issue.message for issue in gate.issues))

        payment_code = await self._next_payment_code()
        payment_values: dict[str, Any] = {
            "supplier_id": payload.supplier_id,
            "payment_code": payment_code,
            "paid_at": payload.paid_at,
            "currency": validate_currency(payload.currency),
            "amount_minor": payload.amount_minor,
            "fx_rate_ppm": payload.fx_rate_ppm,
            "method": payload.method,
            "reference": payload.reference,
            "idempotency_key": idempotency_key,
            "notes": payload.notes,
            "created_by": actor.serialize(),
        }
        allocation_values = [{"invoice_id": a.invoice_id, "amount_minor": a.amount_minor} for a in payload.allocations]
        try:
            payment = await self.repository.insert_payment_with_allocations(
                payment_id=generate_id(PAYMENT_ID_PREFIX), payment_values=payment_values, allocations=allocation_values
            )
        except ApPaymentDuplicateError as err:
            if idempotency_key:
                existing = await self.repository.get_payment_by_idempotency_key(idempotency_key)
                if existing is not None:
                    return self._to_payment_response(existing)
            raise APConflictError("A concurrent payment write raced this one — reload and retry.", current_revision=0) from err

        if payload.amount_minor >= 0:
            for invoice_id, invoice in invoices.items():
                new_balances = await self.repository.get_balances_for_invoices([invoice_id])
                if new_balances.get(invoice_id, 0) >= invoice.gross_total_minor and invoice.status == "approved":
                    await self.repository.update_header(
                        invoice, values={"status": "paid", "updated_by": actor.serialize()}, expected_revision=invoice.invoice_revision
                    )

        await self._emit_payment(payment, actor=actor)
        return self._to_payment_response(payment)

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _find_line(invoice: SupplierInvoice, line_id: int) -> SupplierInvoiceLine | None:
        return next((line for line in invoice.lines if line.id == line_id), None)

    @staticmethod
    def _check_revision(invoice: SupplierInvoice, base_invoice_revision: int) -> None:
        if base_invoice_revision != invoice.invoice_revision:
            raise APConflictError(
                f"Supplier invoice '{invoice.id}' has moved on: expected revision {base_invoice_revision}, "
                f"current is {invoice.invoice_revision}.",
                current_revision=invoice.invoice_revision,
            )

    async def _conflict_from_race(self, invoice_id: str) -> APConflictError:
        current = await self.repository.get_invoice_revision(invoice_id)
        return APConflictError(
            f"Supplier invoice '{invoice_id}' was modified by a concurrent write. Reload and retry.",
            current_revision=current if current is not None else 0,
        )

    async def _sheet_currency_for_booking_line(self, booking_line: BookingLine) -> str | None:
        booking = await self.booking_repository.get_booking_by_id(booking_line.booking_id)
        if booking is None:
            return None
        sheet = await self.costing_repository.get_sheet_by_id(booking.sheet_id)
        return sheet.currency if sheet else None

    async def _derive_and_apply_status(self, invoice: SupplierInvoice, *, actor: ActorRef) -> None:
        if invoice.status not in _PRE_APPROVAL_STATUSES:
            return
        new_status = derive_invoice_status(
            current_status=invoice.status, line_match_statuses=[line.match_status for line in invoice.lines]
        )
        if new_status == invoice.status:
            return
        await self.repository.update_header(
            invoice, values={"status": new_status}, expected_revision=invoice.invoice_revision
        )
        if new_status == "matched":
            await self._emit(invoice, EventType.FINANCE_AP_INVOICE_MATCHED, actor=actor)
        elif new_status == "disputed":
            await self._emit(invoice, EventType.FINANCE_AP_INVOICE_DISPUTED, actor=actor)

    async def _next_payment_code(self) -> str:
        year = date.today().year
        seq = await self.repository.next_business_code_sequence(code_type="PV", year=year)
        return f"PV-{year}-{seq:04d}"

    async def _emit(self, invoice: SupplierInvoice, event_type: EventType, *, actor: ActorRef) -> None:
        outbox = OutboxService(self.session)
        await outbox.emit_event(
            event_type=event_type.value,
            aggregate_type="supplier_invoice",
            aggregate_id=invoice.id,
            actor_email=actor.actor_id,
            payload={
                "invoice_id": invoice.id,
                "supplier_id": invoice.supplier_id,
                "invoice_number": invoice.invoice_number,
                "currency": invoice.currency,
                "gross_total_minor": invoice.gross_total_minor,
                "status": invoice.status,
                "lines": [
                    {"voucher_ref": line.voucher_ref, "variance_minor": line.variance_minor} for line in invoice.lines
                ],
                "actor": actor.serialize(),
            },
        )

    async def _emit_payment(self, payment: ApPayment, *, actor: ActorRef) -> None:
        outbox = OutboxService(self.session)
        await outbox.emit_event(
            event_type=EventType.FINANCE_AP_PAYMENT_RECORDED.value,
            aggregate_type="ap_payment",
            aggregate_id=payment.id,
            actor_email=actor.actor_id,
            payload={
                "payment_id": payment.id,
                "payment_code": payment.payment_code,
                "supplier_id": payment.supplier_id,
                "currency": payment.currency,
                "amount_minor": payment.amount_minor,
                "allocations": [
                    {"invoice_id": alloc.invoice_id, "amount_minor": alloc.amount_minor} for alloc in payment.allocations
                ],
                "actor": actor.serialize(),
            },
        )

    async def _to_response(self, invoice: SupplierInvoice) -> SupplierInvoiceResponseSchema:
        allocated_minor = sum(alloc.amount_minor for alloc in invoice.allocations)
        line_schemas: list[SupplierInvoiceLineResponseSchema] = []
        for line in invoice.lines:
            schema = SupplierInvoiceLineResponseSchema.model_validate(line)
            schema.variance_sheet_minor = await self._variance_sheet_minor(line)
            line_schemas.append(schema)
        response = SupplierInvoiceResponseSchema.model_validate(invoice)
        response.lines = line_schemas
        response.allocations = [ApPaymentAllocationResponseSchema.model_validate(a) for a in invoice.allocations]
        response.allocated_minor = allocated_minor
        response.balance_minor = invoice.gross_total_minor - allocated_minor
        return response

    async def _variance_sheet_minor(self, line: SupplierInvoiceLine) -> int | None:
        """Read-time conversion of the stored (invoice-currency) ``variance_minor`` to sheet currency."""
        if line.variance_minor is None:
            return None
        if line.line_type == "penalty":
            return line.variance_minor  # already sheet-currency when a value was ever stored (F2)
        if line.booking_line_id is None:
            return None
        booking_line = await self.booking_repository.get_line_by_id(line.booking_line_id)
        if booking_line is None:
            return None
        return to_sheet_minor(line.variance_minor, booking_line.fx_rate_ppm_snapshot)

    def _to_payment_response(self, payment: ApPayment) -> ApPaymentResponseSchema:
        response = ApPaymentResponseSchema.model_validate(payment)
        response.allocations = [ApPaymentAllocationResponseSchema.model_validate(a) for a in payment.allocations]
        return response
