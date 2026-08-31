from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, inspect, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models.booking import Booking, BookingLine, BusinessCodeCounter

DEFAULT_TENANT_ID = "capella"


class BookingSlotTakenError(Exception):
    """Raised when a partial-unique slot (active booking per quotation, active line
    per source service_line, or an idempotency key) is already occupied."""


class BookingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------ reads

    async def get_booking_by_id(self, booking_id: str, *, tenant_id: str = DEFAULT_TENANT_ID) -> Booking | None:
        result = await self.session.execute(
            select(Booking)
            .where(Booking.id == booking_id, Booking.tenant_id == tenant_id)
            .options(selectinload(Booking.lines))
        )
        return result.scalar_one_or_none()

    async def get_active_booking_by_quotation(
        self, quotation_id: str, *, tenant_id: str = DEFAULT_TENANT_ID
    ) -> Booking | None:
        result = await self.session.execute(
            select(Booking)
            .where(Booking.quotation_id == quotation_id, Booking.status != "cancelled", Booking.tenant_id == tenant_id)
            .options(selectinload(Booking.lines))
        )
        return result.scalar_one_or_none()

    async def get_booking_by_idempotency_key(
        self, idempotency_key: str, *, tenant_id: str = DEFAULT_TENANT_ID
    ) -> Booking | None:
        result = await self.session.execute(
            select(Booking)
            .where(Booking.idempotency_key == idempotency_key, Booking.tenant_id == tenant_id)
            .options(selectinload(Booking.lines))
        )
        return result.scalar_one_or_none()

    async def get_line_by_id(self, line_id: str, *, tenant_id: str = DEFAULT_TENANT_ID) -> BookingLine | None:
        line = await self.session.get(BookingLine, line_id)
        if line is None or line.tenant_id != tenant_id:
            return None
        return line

    async def get_active_line_by_source_service_line(
        self, source_service_line_id: str, *, tenant_id: str = DEFAULT_TENANT_ID
    ) -> BookingLine | None:
        result = await self.session.execute(
            select(BookingLine).where(
                BookingLine.source_service_line_id == source_service_line_id,
                BookingLine.status != "cancelled",
                BookingLine.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_board_lines(
        self,
        *,
        tenant_id: str = DEFAULT_TENANT_ID,
        status: str | None = None,
        assignee_email: str | None = None,
        quotation_id: str | None = None,
        due_within_days: int | None = None,
        overdue_only: bool = False,
        today: date | None = None,
    ) -> list[tuple[BookingLine, Booking]]:
        conditions = [BookingLine.tenant_id == tenant_id]
        if status:
            conditions.append(BookingLine.status == status)
        if assignee_email:
            conditions.append(BookingLine.assignee_email == assignee_email)
        if quotation_id:
            conditions.append(Booking.quotation_id == quotation_id)
        if overdue_only:
            if today is None:
                raise ValueError("today is required when overdue_only=True")
            conditions.append(BookingLine.request_by_date < today)
            conditions.append(BookingLine.status.notin_(("delivered", "cancelled")))
        elif due_within_days is not None:
            if today is None:
                raise ValueError("today is required when due_within_days is set")
            conditions.append(BookingLine.request_by_date <= today + timedelta(days=due_within_days))
            conditions.append(BookingLine.status.notin_(("delivered", "cancelled")))

        result = await self.session.execute(
            select(BookingLine, Booking)
            .join(Booking, BookingLine.booking_id == Booking.id)
            .where(and_(*conditions))
            .order_by(BookingLine.request_by_date.is_(None), BookingLine.request_by_date.asc(), BookingLine.sort_order.asc())
        )
        return [(line, booking) for line, booking in result.all()]

    # ----------------------------------------------------------------- writes

    async def insert_booking(self, *, booking_id: str, tenant_id: str = DEFAULT_TENANT_ID, values: dict[str, Any]) -> Booking:
        now = datetime.now(timezone.utc)
        booking = Booking(id=booking_id, tenant_id=tenant_id, created_at=now, updated_at=now, **values)
        self.session.add(booking)
        try:
            await self.session.flush()
        except IntegrityError as err:
            await self.session.rollback()
            raise BookingSlotTakenError(str(err)) from err
        return booking

    async def insert_line(
        self, booking: Booking, *, line_id: str, tenant_id: str = DEFAULT_TENANT_ID, values: dict[str, Any]
    ) -> BookingLine:
        now = datetime.now(timezone.utc)
        line = BookingLine(id=line_id, booking_id=booking.id, tenant_id=tenant_id, created_at=now, updated_at=now, **values)
        self.session.add(line)
        # Only touch the in-memory collection if it's already loaded: appending to
        # an unloaded collection on a just-flushed object triggers an
        # async-incompatible lazy load. When it *is* loaded, appending keeps it in
        # sync — a later get_booking_by_id() on the same identity-mapped object
        # would otherwise skip re-populating an already-loaded relationship.
        if "lines" in inspect(booking).dict:
            booking.lines.append(line)
        booking.booking_revision += 1
        booking.updated_at = now
        try:
            await self.session.flush()
        except IntegrityError as err:
            await self.session.rollback()
            raise BookingSlotTakenError(str(err)) from err
        return line

    async def update_header(self, booking: Booking, *, values: dict[str, Any]) -> Booking:
        for field, value in values.items():
            setattr(booking, field, value)
        booking.booking_revision += 1
        booking.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return booking

    async def update_line(self, booking: Booking, line: BookingLine, *, values: dict[str, Any]) -> BookingLine:
        for field, value in values.items():
            setattr(line, field, value)
        line.updated_at = datetime.now(timezone.utc)
        booking.booking_revision += 1
        booking.updated_at = line.updated_at
        try:
            await self.session.flush()
        except IntegrityError as err:
            await self.session.rollback()
            raise BookingSlotTakenError(str(err)) from err
        return line

    async def cancel_all_open_lines(
        self, booking: Booking, *, reason: str, actor: str, on_date: date, penalties: dict[str, int] | None = None
    ) -> None:
        now = datetime.now(timezone.utc)
        for line in booking.lines:
            # "delivered" is terminal too — a consumed service cannot be un-delivered by a bulk cancel.
            if line.status in ("cancelled", "delivered"):
                continue
            line.status = "cancelled"
            line.cancelled_at = now
            line.cancel_reason = reason
            if penalties is not None and line.id in penalties:
                line.cancel_penalty_minor = penalties[line.id]
            line.updated_by = actor
            line.updated_at = now
        booking.booking_revision += 1
        booking.updated_at = now
        await self.session.flush()

    # ------------------------------------------------------------- sequences

    async def next_business_code_sequence(self, *, code_type: str, year: int, tenant_id: str = DEFAULT_TENANT_ID) -> int:
        """Atomic, portable (PG + SQLite) increment for ``BK-``/``VC-`` codes."""
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
