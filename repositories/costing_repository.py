from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models.costing import CostingSheet, ServiceLine

DEFAULT_TENANT_ID = "capella"


class CostingSheetSlotTakenError(Exception):
    """Raised when the partial-unique slot for a request/quotation is already occupied."""


class CostingRevisionRaceError(Exception):
    """Version-guarded revision bump matched no row — a concurrent writer won the race."""

    def __init__(self, sheet_id: str, expected_revision: int) -> None:
        super().__init__(
            f"Costing sheet '{sheet_id}' moved past revision {expected_revision} while this write was in flight."
        )
        self.sheet_id = sheet_id
        self.expected_revision = expected_revision


class CostingSheetAlreadyAttachedError(Exception):
    """Attach guard (quotation_id IS NULL) matched no row — the sheet was attached concurrently."""


class CostingLineDuplicateError(Exception):
    """The (sheet_id, idempotency_key) unique index fired — a concurrent duplicate create."""


class CostingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------ reads

    async def get_sheet_by_id(self, sheet_id: str, *, tenant_id: str = DEFAULT_TENANT_ID) -> CostingSheet | None:
        result = await self.session.execute(
            select(CostingSheet)
            .where(CostingSheet.id == sheet_id, CostingSheet.tenant_id == tenant_id)
            .options(selectinload(CostingSheet.lines))
        )
        return result.scalar_one_or_none()

    async def get_active_sheet_by_request(
        self, request_id: str, *, tenant_id: str = DEFAULT_TENANT_ID
    ) -> CostingSheet | None:
        """The unattached sheet currently open for this request (chốt #1 slot)."""
        result = await self.session.execute(
            select(CostingSheet)
            .where(
                CostingSheet.quote_request_id == request_id,
                CostingSheet.quotation_id.is_(None),
                CostingSheet.tenant_id == tenant_id,
            )
            .options(selectinload(CostingSheet.lines))
            .order_by(CostingSheet.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_sheet_by_quotation(
        self, quotation_id: str, *, tenant_id: str = DEFAULT_TENANT_ID
    ) -> CostingSheet | None:
        result = await self.session.execute(
            select(CostingSheet)
            .where(CostingSheet.quotation_id == quotation_id, CostingSheet.tenant_id == tenant_id)
            .options(selectinload(CostingSheet.lines))
        )
        return result.scalar_one_or_none()

    async def get_line_by_id(self, line_id: str, *, tenant_id: str = DEFAULT_TENANT_ID) -> ServiceLine | None:
        line = await self.session.get(ServiceLine, line_id)
        if line is None or line.tenant_id != tenant_id:
            return None
        return line

    # ----------------------------------------------------------------- writes

    async def insert_sheet(self, *, sheet_id: str, tenant_id: str = DEFAULT_TENANT_ID, values: dict[str, Any]) -> CostingSheet:
        now = datetime.now(timezone.utc)
        sheet = CostingSheet(id=sheet_id, tenant_id=tenant_id, created_at=now, updated_at=now, **values)
        self.session.add(sheet)
        try:
            await self.session.flush()
        except IntegrityError as err:
            await self.session.rollback()
            raise CostingSheetSlotTakenError(str(err)) from err
        return sheet

    async def _bump_revision_guarded(self, sheet: CostingSheet, *, expected_revision: int, extra_values: dict[str, Any] | None = None) -> None:
        """CAS enforced in SQL (Plan 16.3 F-01/D1): the bump only lands if nobody moved the revision.

        The Python-level ``_check_revision`` in the service is a fast pre-check only;
        this guarded UPDATE is the authority, so two concurrent writers can never
        both win between the check and the flush.
        """
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            update(CostingSheet)
            .where(CostingSheet.id == sheet.id, CostingSheet.costing_revision == expected_revision)
            .values(costing_revision=expected_revision + 1, updated_at=now, **(extra_values or {}))
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            raise CostingRevisionRaceError(sheet.id, expected_revision)
        # We now hold the row lock until commit, so mirroring the new state onto the
        # in-session object cannot be clobbered by another writer.
        sheet.costing_revision = expected_revision + 1
        sheet.updated_at = now
        for field, value in (extra_values or {}).items():
            setattr(sheet, field, value)

    async def get_sheet_revision(self, sheet_id: str, *, tenant_id: str = DEFAULT_TENANT_ID) -> int | None:
        """Current revision straight from the DB, bypassing the identity map (post-race re-read)."""
        result = await self.session.execute(
            select(CostingSheet.costing_revision).where(
                CostingSheet.id == sheet_id, CostingSheet.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def update_settings(
        self, sheet: CostingSheet, *, values: dict[str, Any], expected_revision: int
    ) -> CostingSheet:
        await self._bump_revision_guarded(sheet, expected_revision=expected_revision, extra_values=values)
        await self.session.flush()
        return sheet

    async def attach_to_quotation(self, sheet: CostingSheet, *, quotation_id: str, idempotency_key: str, updated_by: dict[str, Any] | None = None) -> CostingSheet:
        now = datetime.now(timezone.utc)
        values: dict[str, Any] = {
            "quotation_id": quotation_id,
            "attach_idempotency_key": idempotency_key,
            "costing_revision": CostingSheet.costing_revision + 1,
            "updated_at": now,
        }
        if updated_by is not None:
            values["updated_by"] = updated_by
        try:
            result = await self.session.execute(
                update(CostingSheet)
                .where(CostingSheet.id == sheet.id, CostingSheet.quotation_id.is_(None))
                .values(**values)
                .execution_options(synchronize_session=False)
            )
        except IntegrityError as err:
            await self.session.rollback()
            raise CostingSheetSlotTakenError(str(err)) from err
        if result.rowcount != 1:
            raise CostingSheetAlreadyAttachedError(
                f"Costing sheet '{sheet.id}' was attached to a quotation by a concurrent writer."
            )
        await self.session.refresh(sheet)
        return sheet

    async def insert_line(
        self,
        sheet: CostingSheet,
        *,
        line_id: str,
        tenant_id: str = DEFAULT_TENANT_ID,
        values: dict[str, Any],
        expected_revision: int,
    ) -> ServiceLine:
        now = datetime.now(timezone.utc)
        line = ServiceLine(id=line_id, sheet_id=sheet.id, tenant_id=tenant_id, created_at=now, updated_at=now, **values)
        self.session.add(line)
        sheet.lines.append(line)
        try:
            await self._bump_revision_guarded(sheet, expected_revision=expected_revision)
            await self.session.flush()
        except IntegrityError as err:
            # Concurrent duplicate with the same Idempotency-Key: the loser replays
            # gracefully instead of surfacing a 500 (16.3 F-18).
            await self.session.rollback()
            raise CostingLineDuplicateError(str(err)) from err
        return line

    async def get_line_by_idempotency_key(
        self, sheet_id: str, *, idempotency_key: str, tenant_id: str = DEFAULT_TENANT_ID
    ) -> ServiceLine | None:
        result = await self.session.execute(
            select(ServiceLine).where(
                ServiceLine.sheet_id == sheet_id,
                ServiceLine.idempotency_key == idempotency_key,
                ServiceLine.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_line(
        self, sheet: CostingSheet, line: ServiceLine, *, values: dict[str, Any], expected_revision: int
    ) -> ServiceLine:
        for field, value in values.items():
            setattr(line, field, value)
        line.updated_at = datetime.now(timezone.utc)
        await self._bump_revision_guarded(sheet, expected_revision=expected_revision)
        await self.session.flush()
        return line

    async def delete_line(self, sheet: CostingSheet, line: ServiceLine, *, expected_revision: int) -> None:
        if line in sheet.lines:
            sheet.lines.remove(line)
        await self.session.delete(line)
        await self._bump_revision_guarded(sheet, expected_revision=expected_revision)
        await self.session.flush()
