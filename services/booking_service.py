"""Booking aggregate service — 15.6 §1. Copy-on-confirm-deposit, frozen forever (T3/R3).

Never touches facts/content/media/publication; only read-only lookups into
costing (sheet + lines), supplier/rate (policy resolution) and quotation
(ownership + facts snapshot for the board header) — chốt #7 in
docs/plans/refactor-tech-stack/15.6-booking-operations.md.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.kernel import ActorRef, generate_id
from core.rules.booking_rules import CashFlowLine, cancellation_penalty_minor, cash_flow_check, compute_deadlines, default_request_by, validate_transition
from core.rules.costing_rules import ServiceLineInput, line_cost_minor, line_sell_minor
from db.models.booking import Booking, BookingLine
from repositories.booking_repository import BookingRepository, BookingSlotTakenError
from repositories.costing_repository import CostingRepository
from repositories.quotation_repository import QuotationRepository
from repositories.rate_repository import RateRepository
from repositories.supplier_repository import SupplierRepository
from schemas.v2.booking import (
    BookingAddLineSchema,
    BookingBoardItemSchema,
    BookingBoardResponseSchema,
    BookingCancelSchema,
    BookingCreateSchema,
    BookingDetailResponseSchema,
    BookingHeaderUpdateSchema,
    BookingLineOpsUpdateSchema,
    BookingLineResponseSchema,
    BookingLineTransitionSchema,
    BookingResponseSchema,
)
from services.outbox_service import OutboxService

BOOKING_ID_PREFIX = "bkg"
LINE_ID_PREFIX = "bkl"

DUE_SOON_WINDOW_DAYS = 7
_TERMINAL_LINE_STATUSES = ("delivered", "cancelled")


class BookingValidationError(ValueError):
    """Business-rule violation (maps to 422)."""


class BookingConflictError(ValueError):
    """CAS mismatch or lifecycle conflict (maps to 409)."""

    def __init__(self, message: str, *, current_revision: int) -> None:
        super().__init__(message)
        self.current_revision = current_revision


class BookingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = BookingRepository(session)
        self.costing_repository = CostingRepository(session)
        self.quotation_repository = QuotationRepository(session)
        self.supplier_repository = SupplierRepository(session)
        self.rate_repository = RateRepository(session)

    # ------------------------------------------------------------------ reads

    async def get_detail(self, booking_id: str, *, today: date) -> BookingDetailResponseSchema | None:
        booking = await self.repository.get_booking_by_id(booking_id)
        if booking is None:
            return None
        return self._to_detail(booking, today=today)

    async def get_line_by_voucher_ref(self, voucher_ref: str) -> BookingLine | None:
        """Read-only — no flush/commit. Sole exception carved for AP voucher matching (15.9 §9)."""
        return await self.repository.get_line_by_voucher_ref(voucher_ref)

    async def list_board(
        self,
        *,
        today: date,
        status: str | None = None,
        assignee_email: str | None = None,
        quotation_id: str | None = None,
        due_within_days: int | None = None,
        overdue_only: bool = False,
    ) -> BookingBoardResponseSchema:
        rows = await self.repository.list_board_lines(
            status=status,
            assignee_email=assignee_email,
            quotation_id=quotation_id,
            due_within_days=due_within_days,
            overdue_only=overdue_only,
            today=today,
        )
        items = [
            BookingBoardItemSchema(
                line=self._line_response(line, today=today),
                booking_id=booking.id,
                booking_code=booking.booking_code,
                booking_revision=booking.booking_revision,
                quotation_id=booking.quotation_id,
                party_label_snapshot=booking.party_label_snapshot,
                travel_start_date=booking.travel_start_date,
                travel_end_date=booking.travel_end_date,
                customer_balance_due_date=booking.customer_balance_due_date,
                cash_flow_warning=bool(
                    cash_flow_check(
                        booking.customer_balance_due_date,
                        [CashFlowLine(line_id=line.id, balance_due_date=line.balance_due_date)],
                    )
                ),
            )
            for line, booking in rows
        ]
        return BookingBoardResponseSchema(items=items)

    # --------------------------------------------------------------- writes

    async def create_booking(
        self, payload: BookingCreateSchema, *, actor: ActorRef, idempotency_key: str, today: date
    ) -> BookingDetailResponseSchema:
        existing = await self.repository.get_booking_by_idempotency_key(idempotency_key)
        if existing is not None and existing.quotation_id == payload.quotation_id:
            return self._to_detail(existing, today=today)

        already_open = await self.repository.get_active_booking_by_quotation(payload.quotation_id)
        if already_open is not None:
            raise BookingConflictError(
                f"quotation '{payload.quotation_id}' already has an active booking '{already_open.id}'.",
                current_revision=already_open.booking_revision,
            )

        sheet = await self.costing_repository.get_sheet_by_quotation(payload.quotation_id)
        if sheet is None or not sheet.lines:
            raise BookingValidationError(
                f"quotation '{payload.quotation_id}' has no costing sheet with service lines to book."
            )

        quotation = await self.quotation_repository.get_quotation_by_id(payload.quotation_id)
        if quotation is None:
            raise BookingValidationError(f"quotation '{payload.quotation_id}' was not found.")

        party_label, travel_start_date, travel_end_date = await self._snapshot_quotation_facts(payload.quotation_id)

        header_values: dict[str, Any] = {
            "quotation_id": payload.quotation_id,
            "sheet_id": sheet.id,
            "booking_code": await self._next_code("BK", today.year),
            "deposit_received_at": payload.deposit_received_at,
            "customer_balance_due_date": payload.customer_balance_due_date,
            "party_label_snapshot": party_label,
            "travel_start_date": travel_start_date,
            "travel_end_date": travel_end_date,
            "idempotency_key": idempotency_key,
            "created_by": actor.serialize(),
            "updated_by": actor.serialize(),
        }
        try:
            booking = await self.repository.insert_booking(booking_id=generate_id(BOOKING_ID_PREFIX), values=header_values)
        except BookingSlotTakenError as err:
            raise BookingConflictError(
                f"quotation '{payload.quotation_id}' already has an active booking.", current_revision=0
            ) from err

        for line in sorted(sheet.lines, key=lambda item: (item.day_number is None, item.day_number or 0, item.sort_order)):
            values = await self._snapshot_line(line, sheet=sheet)
            await self.repository.insert_line(booking, line_id=generate_id(LINE_ID_PREFIX), values=values)
            await self.costing_repository.update_line_booking_status(line, booking_status="to_request")

        await self.session.flush()

        outbox = OutboxService(self.session)
        await outbox.emit_event(
            event_type="booking.created",
            aggregate_type="booking",
            aggregate_id=booking.id,
            actor_email=actor.actor_id,
            payload={"booking_code": booking.booking_code, "quotation_id": booking.quotation_id, "line_count": len(sheet.lines)},
        )

        booking = await self.repository.get_booking_by_id(booking.id)
        return self._to_detail(booking, today=today)

    async def update_header(
        self, booking_id: str, payload: BookingHeaderUpdateSchema, *, actor: ActorRef, today: date
    ) -> BookingDetailResponseSchema | None:
        booking = await self.repository.get_booking_by_id(booking_id)
        if booking is None:
            return None
        self._check_revision(booking, payload.base_booking_revision)

        values: dict[str, Any] = {"updated_by": actor.serialize()}
        if payload.customer_balance_due_date is not None:
            values["customer_balance_due_date"] = payload.customer_balance_due_date
        if payload.status is not None:
            values["status"] = payload.status
        if payload.notes is not None:
            values["notes"] = payload.notes

        booking = await self.repository.update_header(booking, values=values)
        return self._to_detail(booking, today=today)

    async def transition_line(
        self,
        booking_id: str,
        line_id: str,
        payload: BookingLineTransitionSchema,
        *,
        actor: ActorRef,
        idempotency_key: str,
        today: date,
    ) -> BookingDetailResponseSchema | None:
        booking = await self.repository.get_booking_by_id(booking_id)
        if booking is None:
            return None
        line = self._find_line(booking, line_id)
        if line is None:
            return None

        if line.transition_idempotency_key == idempotency_key and line.status == payload.to:
            return self._to_detail(booking, today=today)

        self._check_revision(booking, payload.base_booking_revision)

        confirmed_at = today if payload.to == "confirmed" else None
        gate = validate_transition(line.status, payload.to, confirmed_at=confirmed_at, cancel_reason=payload.cancel_reason)
        if not gate.passed:
            raise BookingValidationError({"message": "Invalid booking-line transition.", "issues": [issue.message for issue in gate.errors]})

        values: dict[str, Any] = {
            "status": payload.to,
            "transition_idempotency_key": idempotency_key,
            "updated_by": actor.serialize(),
        }
        if payload.supplier_ref:
            values["supplier_ref"] = payload.supplier_ref

        if payload.to == "confirmed":
            now = datetime.now(timezone.utc)
            values["confirmed_at"] = now
            values["voucher_ref"] = await self._next_code("VC", today.year)
            deadlines = compute_deadlines(
                cancellation_policy=line.cancellation_policy_snapshot_json,
                payment_terms=line.payment_terms_snapshot_json,
                service_date=line.service_date or today,
                confirmed_at=today,
            )
            values["deposit_due_date"] = deadlines.deposit_due_date
        elif payload.to == "cancelled":
            now = datetime.now(timezone.utc)
            values["cancelled_at"] = now
            values["cancel_reason"] = payload.cancel_reason
            values["cancel_penalty_minor"] = cancellation_penalty_minor(
                line.cancellation_policy_snapshot_json, line.sell_minor_snapshot, line.service_date or today, today
            )

        await self.repository.update_line(booking, line, values=values)
        await self._mirror_service_line_status(line.source_service_line_id, payload.to)

        outbox = OutboxService(self.session)
        if payload.to == "confirmed":
            await outbox.emit_event(
                event_type="booking.line.confirmed",
                aggregate_type="booking_line",
                aggregate_id=line.id,
                actor_email=actor.actor_id,
                payload={
                    **self._finance_line_payload(booking, line),
                    "voucher_ref": values["voucher_ref"],
                    "supplier_ref": payload.supplier_ref,
                    "deposit_due_date": values["deposit_due_date"].isoformat() if values.get("deposit_due_date") else None,
                },
            )
        elif payload.to == "cancelled":
            await outbox.emit_event(
                event_type="booking.line.cancelled",
                aggregate_type="booking_line",
                aggregate_id=line.id,
                actor_email=actor.actor_id,
                payload={
                    **self._finance_line_payload(booking, line),
                    "penalty_minor": values["cancel_penalty_minor"],
                    "penalty_currency": await self._sheet_currency(booking.sheet_id),
                    "reason": payload.cancel_reason,
                },
            )
        elif payload.to == "delivered":
            # Accrual moment for Finance (M7): the service was consumed, the payable is final.
            await outbox.emit_event(
                event_type="booking.line.delivered",
                aggregate_type="booking_line",
                aggregate_id=line.id,
                actor_email=actor.actor_id,
                payload=self._finance_line_payload(booking, line),
            )

        booking = await self.repository.get_booking_by_id(booking.id)
        return self._to_detail(booking, today=today)

    async def update_line_ops(
        self, booking_id: str, line_id: str, payload: BookingLineOpsUpdateSchema, *, actor: ActorRef, today: date
    ) -> BookingDetailResponseSchema | None:
        booking = await self.repository.get_booking_by_id(booking_id)
        if booking is None:
            return None
        line = self._find_line(booking, line_id)
        if line is None:
            return None
        self._check_revision(booking, payload.base_booking_revision)

        values: dict[str, Any] = {"updated_by": actor.serialize()}
        if payload.request_by_date is not None:
            values["request_by_date"] = payload.request_by_date
        if payload.assignee_email is not None:
            values["assignee_email"] = payload.assignee_email
        if payload.notes is not None:
            values["notes"] = payload.notes
        if payload.supplier_ref is not None:
            if line.status == "confirmed":
                raise BookingValidationError("supplier_ref can only be edited before a line is confirmed.")
            values["supplier_ref"] = payload.supplier_ref

        await self.repository.update_line(booking, line, values=values)
        booking = await self.repository.get_booking_by_id(booking.id)
        return self._to_detail(booking, today=today)

    async def add_line(
        self, booking_id: str, payload: BookingAddLineSchema, *, actor: ActorRef, today: date
    ) -> BookingDetailResponseSchema | None:
        booking = await self.repository.get_booking_by_id(booking_id)
        if booking is None:
            return None
        self._check_revision(booking, payload.base_booking_revision)

        service_line = await self.costing_repository.get_line_by_id(payload.service_line_id)
        if service_line is None or service_line.sheet_id != booking.sheet_id:
            raise BookingValidationError(
                f"service_line '{payload.service_line_id}' was not found on booking's costing sheet."
            )
        existing = await self.repository.get_active_line_by_source_service_line(payload.service_line_id)
        if existing is not None:
            raise BookingConflictError(
                f"service_line '{payload.service_line_id}' already has an active booking_line '{existing.id}'.",
                current_revision=booking.booking_revision,
            )

        sheet = await self.costing_repository.get_sheet_by_id(booking.sheet_id)
        values = await self._snapshot_line(service_line, sheet=sheet)
        values["created_by"] = actor.serialize()
        values["updated_by"] = actor.serialize()
        await self.repository.insert_line(booking, line_id=generate_id(LINE_ID_PREFIX), values=values)
        await self.costing_repository.update_line_booking_status(service_line, booking_status="to_request")

        booking = await self.repository.get_booking_by_id(booking.id)
        return self._to_detail(booking, today=today)

    async def cancel_booking(
        self, booking_id: str, payload: BookingCancelSchema, *, actor: ActorRef, today: date
    ) -> BookingDetailResponseSchema | None:
        booking = await self.repository.get_booking_by_id(booking_id)
        if booking is None:
            return None
        self._check_revision(booking, payload.base_booking_revision)

        # Penalties are documentary evidence (Finance readiness): compute per open line from the
        # FROZEN cancellation policy before flipping status — same math as the per-line transition.
        penalties: dict[str, int] = {
            line.id: cancellation_penalty_minor(
                line.cancellation_policy_snapshot_json, line.sell_minor_snapshot, line.service_date or today, today
            )
            for line in booking.lines
            if line.status not in _TERMINAL_LINE_STATUSES
        }
        cancelled_lines = [line for line in booking.lines if line.id in penalties]
        await self.repository.cancel_all_open_lines(
            booking, reason=payload.reason, actor=actor.serialize(), on_date=today, penalties=penalties
        )
        for line in cancelled_lines:
            await self._mirror_service_line_status(line.source_service_line_id, "cancelled")
        booking = await self.repository.update_header(booking, values={"status": "cancelled", "updated_by": actor.serialize()})

        outbox = OutboxService(self.session)
        await outbox.emit_event(
            event_type="booking.cancelled",
            aggregate_type="booking",
            aggregate_id=booking.id,
            actor_email=actor.actor_id,
            payload={
                "booking_code": booking.booking_code,
                "quotation_id": booking.quotation_id,
                "reason": payload.reason,
                "penalty_currency": await self._sheet_currency(booking.sheet_id),
                "lines": [
                    {"line_id": line.id, "voucher_ref": line.voucher_ref, "penalty_minor": penalties[line.id]}
                    for line in cancelled_lines
                ],
                "penalty_total_minor": sum(penalties.values()),
            },
        )
        return self._to_detail(booking, today=today)

    # ------------------------------------------------------------- helpers

    @staticmethod
    def _check_revision(booking: Booking, base_booking_revision: int) -> None:
        if base_booking_revision != booking.booking_revision:
            raise BookingConflictError(
                f"Booking '{booking.id}' has moved on: expected revision {base_booking_revision}, "
                f"current is {booking.booking_revision}.",
                current_revision=booking.booking_revision,
            )

    @staticmethod
    def _find_line(booking: Booking, line_id: str) -> BookingLine | None:
        return next((line for line in booking.lines if line.id == line_id), None)

    @staticmethod
    def _finance_line_payload(booking: Booking, line: BookingLine) -> dict[str, Any]:
        """Self-standing documentary payload (Finance readiness — mốc A).

        A future Finance consumer must be able to originate a payable from this payload
        alone, without joining back into booking/costing tables.
        """
        return {
            "booking_id": booking.id,
            "booking_code": booking.booking_code,
            "quotation_id": booking.quotation_id,
            "source_service_line_id": line.source_service_line_id,
            "supplier_id": line.supplier_id_snapshot,
            "supplier_name": line.supplier_name_snapshot,
            "category": line.category,
            "title": line.title_snapshot,
            "service_date": line.service_date.isoformat() if line.service_date else None,
            "cost_total_minor": line.unit_cost_minor_snapshot * line.qty_unit * line.qty_time,
            "cost_currency": line.cost_currency_snapshot,
            "sell_minor": line.sell_minor_snapshot,
            "voucher_ref": line.voucher_ref,
            "balance_due_date": line.balance_due_date.isoformat() if line.balance_due_date else None,
        }

    async def _sheet_currency(self, sheet_id: str) -> str | None:
        sheet = await self.costing_repository.get_sheet_by_id(sheet_id)
        return sheet.currency if sheet is not None else None

    async def _mirror_service_line_status(self, source_service_line_id: str, status: str) -> None:
        service_line = await self.costing_repository.get_line_by_id(source_service_line_id)
        if service_line is not None:
            await self.costing_repository.update_line_booking_status(service_line, booking_status=status)

    async def _next_code(self, code_type: str, year: int) -> str:
        seq = await self.repository.next_business_code_sequence(code_type=code_type, year=year)
        return f"{code_type}-{year}-{seq:04d}"

    async def _resolve_policies(self, service_line) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        """Resolve inherit rate→supplier for payment/cancellation policy (Phụ lục A)."""
        payment_terms: dict[str, Any] | None = None
        cancellation_policy: dict[str, Any] | None = None
        if service_line.tariff_id:
            rate = await self.rate_repository.get_by_id(service_line.tariff_id)
            if rate is not None:
                payment_terms = rate.payment_terms_json
                cancellation_policy = rate.cancellation_policy_json
        if (payment_terms is None or cancellation_policy is None) and service_line.supplier_id:
            supplier = await self.supplier_repository.get_by_id(service_line.supplier_id)
            if supplier is not None:
                payment_terms = payment_terms or supplier.payment_terms_json
                cancellation_policy = cancellation_policy or supplier.cancellation_policy_json
        return payment_terms, cancellation_policy

    async def _snapshot_line(self, service_line, *, sheet) -> dict[str, Any]:
        payment_terms, cancellation_policy = await self._resolve_policies(service_line)

        supplier_name = None
        supplier_contact = None
        if service_line.supplier_id:
            supplier = await self.supplier_repository.get_by_id(service_line.supplier_id)
            if supplier is not None:
                supplier_name = supplier.name
                supplier_contact = supplier.contact_json

        line_input = ServiceLineInput(
            line_id=service_line.id,
            day_number=service_line.day_number,
            category=service_line.category,
            unit_cost_minor=service_line.unit_cost_minor,
            qty_unit=service_line.qty_unit,
            qty_time=service_line.qty_time,
            fx_rate_ppm=service_line.fx_rate_ppm,
            sell_override_minor=service_line.sell_override_minor,
        )
        cost_minor = line_cost_minor(line_input)
        sell_minor = line_sell_minor(
            line_input,
            cost_minor=cost_minor,
            markup_rate_bps=sheet.markup_rate_bps,
            rounding_increment_minor=sheet.rounding_increment_minor,
        )

        service_date = service_line.service_date
        deadlines = compute_deadlines(
            cancellation_policy=cancellation_policy,
            payment_terms=payment_terms,
            service_date=service_date,
        ) if service_date is not None else None
        request_by = default_request_by(deadlines.penalty_free_until, service_date) if (deadlines and service_date) else None

        return {
            "source_service_line_id": service_line.id,
            "supplier_id_snapshot": service_line.supplier_id,
            "supplier_name_snapshot": supplier_name,
            "supplier_contact_snapshot_json": supplier_contact,
            "title_snapshot": service_line.title,
            "category": service_line.category,
            "service_date": service_date,
            "unit": service_line.unit,
            "time_basis": service_line.time_basis,
            "qty_unit": service_line.qty_unit,
            "qty_time": service_line.qty_time,
            "unit_cost_minor_snapshot": service_line.unit_cost_minor,
            "cost_currency_snapshot": service_line.cost_currency,
            "fx_rate_ppm_snapshot": service_line.fx_rate_ppm,
            "sell_minor_snapshot": sell_minor,
            "payment_terms_snapshot_json": payment_terms,
            "cancellation_policy_snapshot_json": cancellation_policy,
            "penalty_free_until": deadlines.penalty_free_until if deadlines else None,
            "balance_due_date": deadlines.balance_due_date if deadlines else None,
            "request_by_date": request_by,
            "sort_order": service_line.sort_order,
        }

    async def _snapshot_quotation_facts(self, quotation_id: str) -> tuple[str | None, date | None, date | None]:
        facts = await self.quotation_repository.get_version_facts(quotation_id)
        if facts is None:
            return None, None, None
        resolved = facts.resolved_facts_json or {}
        canonical = facts.canonical_facts_json or {}
        trip = canonical.get("trip_facts") or {}
        party_label = resolved.get("partyLabel")
        start_date = self._parse_date(trip.get("start_date"))
        end_date = self._parse_date(trip.get("end_date"))
        return party_label, start_date, end_date

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None

    def _line_response(self, line: BookingLine, *, today: date) -> BookingLineResponseSchema:
        item = BookingLineResponseSchema.model_validate(line)
        return item.model_copy(update={"urgency": self._urgency(line, today=today)})

    @staticmethod
    def _urgency(line: BookingLine, *, today: date) -> str | None:
        if line.status in _TERMINAL_LINE_STATUSES or line.request_by_date is None:
            return None
        if line.request_by_date < today:
            return "overdue"
        if line.request_by_date <= today + timedelta(days=DUE_SOON_WINDOW_DAYS):
            return "due_soon"
        return "ok"

    def _to_detail(self, booking: Booking, *, today: date) -> BookingDetailResponseSchema:
        lines = sorted(booking.lines, key=lambda line: line.sort_order)
        cash_flow_inputs = [CashFlowLine(line_id=line.id, balance_due_date=line.balance_due_date) for line in lines]
        warnings = cash_flow_check(booking.customer_balance_due_date, cash_flow_inputs)
        return BookingDetailResponseSchema(
            booking=BookingResponseSchema.model_validate(booking),
            lines=[self._line_response(line, today=today) for line in lines],
            cash_flow_warnings=warnings,
        )
