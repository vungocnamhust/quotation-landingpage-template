from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models.costing import CostingSheet, ServiceLine

DEFAULT_TENANT_ID = "capella"


class CostingSheetSlotTakenError(Exception):
    """Raised when the partial-unique slot for a request/quotation is already occupied."""


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

    async def update_settings(self, sheet: CostingSheet, *, values: dict[str, Any]) -> CostingSheet:
        for field, value in values.items():
            setattr(sheet, field, value)
        sheet.costing_revision += 1
        sheet.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return sheet

    async def attach_to_quotation(self, sheet: CostingSheet, *, quotation_id: str, idempotency_key: str) -> CostingSheet:
        sheet.quotation_id = quotation_id
        sheet.attach_idempotency_key = idempotency_key
        sheet.costing_revision += 1
        sheet.updated_at = datetime.now(timezone.utc)
        try:
            await self.session.flush()
        except IntegrityError as err:
            await self.session.rollback()
            raise CostingSheetSlotTakenError(str(err)) from err
        return sheet

    async def insert_line(
        self, sheet: CostingSheet, *, line_id: str, tenant_id: str = DEFAULT_TENANT_ID, values: dict[str, Any]
    ) -> ServiceLine:
        now = datetime.now(timezone.utc)
        line = ServiceLine(id=line_id, sheet_id=sheet.id, tenant_id=tenant_id, created_at=now, updated_at=now, **values)
        self.session.add(line)
        sheet.lines.append(line)
        sheet.costing_revision += 1
        sheet.updated_at = now
        await self.session.flush()
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

    async def update_line(self, sheet: CostingSheet, line: ServiceLine, *, values: dict[str, Any]) -> ServiceLine:
        for field, value in values.items():
            setattr(line, field, value)
        line.updated_at = datetime.now(timezone.utc)
        sheet.costing_revision += 1
        sheet.updated_at = line.updated_at
        await self.session.flush()
        return line

    async def delete_line(self, sheet: CostingSheet, line: ServiceLine) -> None:
        if line in sheet.lines:
            sheet.lines.remove(line)
        await self.session.delete(line)
        sheet.costing_revision += 1
        sheet.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
