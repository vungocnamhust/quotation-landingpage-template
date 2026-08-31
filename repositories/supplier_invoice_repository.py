from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models.booking import BusinessCodeCounter
from db.models.supplier_invoice import ApPayment, ApPaymentAllocation, SupplierInvoice, SupplierInvoiceLine

DEFAULT_TENANT_ID = "capella"


class SupplierInvoiceSlotTakenError(Exception):
    """A partial-unique slot (supplier+invoice_number, or idempotency key) is already occupied."""


class SupplierInvoiceRevisionRaceError(Exception):
    """Version-guarded revision bump matched no row — a concurrent writer won the race."""

    def __init__(self, invoice_id: str, expected_revision: int) -> None:
        super().__init__(
            f"Supplier invoice '{invoice_id}' moved past revision {expected_revision} while this write was in flight."
        )
        self.invoice_id = invoice_id
        self.expected_revision = expected_revision


class SupplierInvoiceLineMatchTakenError(Exception):
    """The partial-unique (booking_line_id, match_status IN active) index fired — double-billing guard (chốt #3)."""


class ApPaymentDuplicateError(Exception):
    """The (tenant_id, idempotency_key) unique index on ap_payments fired — a concurrent duplicate create (F3)."""


class SupplierInvoiceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------ reads

    async def get_invoice_by_id(self, invoice_id: str, *, tenant_id: str = DEFAULT_TENANT_ID) -> SupplierInvoice | None:
        result = await self.session.execute(
            select(SupplierInvoice)
            .where(SupplierInvoice.id == invoice_id, SupplierInvoice.tenant_id == tenant_id)
            .options(selectinload(SupplierInvoice.lines), selectinload(SupplierInvoice.allocations))
        )
        return result.scalar_one_or_none()

    async def get_invoice_by_idempotency_key(
        self, idempotency_key: str, *, tenant_id: str = DEFAULT_TENANT_ID
    ) -> SupplierInvoice | None:
        result = await self.session.execute(
            select(SupplierInvoice)
            .where(SupplierInvoice.idempotency_key == idempotency_key, SupplierInvoice.tenant_id == tenant_id)
            .options(selectinload(SupplierInvoice.lines), selectinload(SupplierInvoice.allocations))
        )
        return result.scalar_one_or_none()

    async def list_invoices(
        self,
        *,
        supplier_id: str | None = None,
        status: str | None = None,
        due_within_days: int | None = None,
        overdue_only: bool = False,
        search: str | None = None,
        today: date,
        tenant_id: str = DEFAULT_TENANT_ID,
    ) -> list[SupplierInvoice]:
        stmt = (
            select(SupplierInvoice)
            .where(SupplierInvoice.tenant_id == tenant_id)
            .options(selectinload(SupplierInvoice.lines))
            .order_by(SupplierInvoice.due_date.asc().nulls_last(), SupplierInvoice.invoice_date.desc())
        )
        if supplier_id:
            stmt = stmt.where(SupplierInvoice.supplier_id == supplier_id)
        if status:
            stmt = stmt.where(SupplierInvoice.status == status)
        if overdue_only:
            stmt = stmt.where(SupplierInvoice.due_date < today, SupplierInvoice.status.notin_(("paid", "void")))
        elif due_within_days is not None:
            horizon = today + timedelta(days=due_within_days)
            stmt = stmt.where(SupplierInvoice.due_date.is_not(None), SupplierInvoice.due_date <= horizon)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(or_(SupplierInvoice.invoice_number.ilike(like), SupplierInvoice.notes.ilike(like)))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_balances_for_invoices(
        self, invoice_ids: list[str], *, tenant_id: str = DEFAULT_TENANT_ID
    ) -> dict[str, int]:
        if not invoice_ids:
            return {}
        result = await self.session.execute(
            select(ApPaymentAllocation.invoice_id, func.sum(ApPaymentAllocation.amount_minor))
            .where(ApPaymentAllocation.invoice_id.in_(invoice_ids), ApPaymentAllocation.tenant_id == tenant_id)
            .group_by(ApPaymentAllocation.invoice_id)
        )
        return {invoice_id: int(total or 0) for invoice_id, total in result.all()}

    async def get_payment_by_idempotency_key(
        self, idempotency_key: str, *, tenant_id: str = DEFAULT_TENANT_ID
    ) -> ApPayment | None:
        result = await self.session.execute(
            select(ApPayment)
            .where(ApPayment.idempotency_key == idempotency_key, ApPayment.tenant_id == tenant_id)
            .options(selectinload(ApPayment.allocations))
        )
        return result.scalar_one_or_none()

    async def next_business_code_sequence(self, *, code_type: str, year: int, tenant_id: str = DEFAULT_TENANT_ID) -> int:
        """Shared portable sequence table (booking's ``BusinessCodeCounter`` — generic by design)."""
        stmt = (
            update(BusinessCodeCounter)
            .where(
                BusinessCodeCounter.tenant_id == tenant_id,
                BusinessCodeCounter.code_type == code_type,
                BusinessCodeCounter.year == year,
            )
            .values(last_value=BusinessCodeCounter.last_value + 1)
            .returning(BusinessCodeCounter.last_value)
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is not None:
            await self.session.flush()
            return int(row)
        self.session.add(BusinessCodeCounter(tenant_id=tenant_id, code_type=code_type, year=year, last_value=1))
        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            return await self.next_business_code_sequence(code_type=code_type, year=year, tenant_id=tenant_id)
        return 1

    # ----------------------------------------------------------------- writes

    async def insert_invoice(
        self, *, invoice_id: str, tenant_id: str = DEFAULT_TENANT_ID, values: dict[str, Any]
    ) -> SupplierInvoice:
        now = datetime.now(timezone.utc)
        invoice = SupplierInvoice(id=invoice_id, tenant_id=tenant_id, created_at=now, updated_at=now, **values)
        self.session.add(invoice)
        try:
            await self.session.flush()
        except IntegrityError as err:
            await self.session.rollback()
            raise SupplierInvoiceSlotTakenError(str(err)) from err
        return invoice

    async def _bump_revision_guarded(
        self, invoice: SupplierInvoice, *, expected_revision: int, extra_values: dict[str, Any] | None = None
    ) -> None:
        """CAS enforced in SQL — mirrors ``CostingRepository._bump_revision_guarded``."""
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            update(SupplierInvoice)
            .where(SupplierInvoice.id == invoice.id, SupplierInvoice.invoice_revision == expected_revision)
            .values(invoice_revision=expected_revision + 1, updated_at=now, **(extra_values or {}))
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            raise SupplierInvoiceRevisionRaceError(invoice.id, expected_revision)
        invoice.invoice_revision = expected_revision + 1
        invoice.updated_at = now
        for field, value in (extra_values or {}).items():
            setattr(invoice, field, value)

    async def get_invoice_revision(self, invoice_id: str, *, tenant_id: str = DEFAULT_TENANT_ID) -> int | None:
        result = await self.session.execute(
            select(SupplierInvoice.invoice_revision).where(
                SupplierInvoice.id == invoice_id, SupplierInvoice.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def update_header(
        self, invoice: SupplierInvoice, *, values: dict[str, Any], expected_revision: int
    ) -> SupplierInvoice:
        try:
            await self._bump_revision_guarded(invoice, expected_revision=expected_revision, extra_values=values)
        except IntegrityError as err:
            await self.session.rollback()
            raise SupplierInvoiceSlotTakenError(str(err)) from err
        await self.session.flush()
        return invoice

    async def replace_lines(
        self, invoice: SupplierInvoice, *, line_values: list[dict[str, Any]], expected_revision: int
    ) -> list[SupplierInvoiceLine]:
        """Full replace-set (KISS, like costing's rate-draft convention) — only while draft/received."""
        now = datetime.now(timezone.utc)
        for existing in list(invoice.lines):
            invoice.lines.remove(existing)
            await self.session.delete(existing)
        new_lines: list[SupplierInvoiceLine] = []
        for values in line_values:
            line = SupplierInvoiceLine(invoice_id=invoice.id, tenant_id=invoice.tenant_id, created_at=now, updated_at=now, **values)
            self.session.add(line)
            invoice.lines.append(line)
            new_lines.append(line)
        await self._bump_revision_guarded(invoice, expected_revision=expected_revision)
        await self.session.flush()
        return new_lines

    async def update_line(
        self, invoice: SupplierInvoice, line: SupplierInvoiceLine, *, values: dict[str, Any], expected_revision: int
    ) -> SupplierInvoiceLine:
        for field, value in values.items():
            setattr(line, field, value)
        line.updated_at = datetime.now(timezone.utc)
        try:
            # Flush the line change explicitly first — surfaces the partial-unique
            # IntegrityError here rather than as an implicit autoflush nested inside
            # the raw ``UPDATE`` below, which is harder to reason about under asyncio.
            await self.session.flush()
            await self._bump_revision_guarded(invoice, expected_revision=expected_revision)
            await self.session.flush()
        except IntegrityError as err:
            await self.session.rollback()
            raise SupplierInvoiceLineMatchTakenError(str(err)) from err
        return line

    async def insert_payment_with_allocations(
        self,
        *,
        payment_id: str,
        tenant_id: str = DEFAULT_TENANT_ID,
        payment_values: dict[str, Any],
        allocations: list[dict[str, Any]],
    ) -> ApPayment:
        now = datetime.now(timezone.utc)
        payment = ApPayment(id=payment_id, tenant_id=tenant_id, created_at=now, **payment_values)
        self.session.add(payment)
        for alloc_values in allocations:
            allocation = ApPaymentAllocation(
                payment_id=payment_id, tenant_id=tenant_id, created_at=now, **alloc_values
            )
            self.session.add(allocation)
            payment.allocations.append(allocation)
        try:
            await self.session.flush()
        except IntegrityError as err:
            await self.session.rollback()
            raise ApPaymentDuplicateError(str(err)) from err
        return payment
