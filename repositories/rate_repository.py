from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models.rate import Rate, RatePriceLine, RateSource

DEFAULT_TENANT_ID = "capella"


class RateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, rate_id: str, *, tenant_id: str = DEFAULT_TENANT_ID) -> Rate | None:
        result = await self.session.execute(
            select(Rate).where(Rate.id == rate_id, Rate.tenant_id == tenant_id).options(selectinload(Rate.lines))
        )
        return result.scalar_one_or_none()

    async def list_by_product(
        self,
        product_id: str,
        *,
        tenant_id: str = DEFAULT_TENANT_ID,
        lifecycle: str | None = "active",
        on_date: date | None = None,
        limit: int = 100,
    ) -> tuple[list[Rate], int]:
        stmt = (
            select(Rate)
            .where(Rate.product_id == product_id, Rate.tenant_id == tenant_id)
            .options(selectinload(Rate.lines))
            .order_by(Rate.valid_from.desc(), Rate.version.desc())
        )
        if lifecycle:
            stmt = stmt.where(Rate.lifecycle_status == lifecycle)
        if on_date is not None:
            stmt = stmt.where(Rate.valid_from <= on_date, Rate.valid_to >= on_date)
        stmt = stmt.limit(max(1, min(limit, 200)))
        result = await self.session.scalars(stmt)
        items = list(result.all())
        return items, len(items)

    async def list_active_for_product(
        self, product_id: str, *, tenant_id: str = DEFAULT_TENANT_ID, exclude_rate_id: str | None = None
    ) -> list[Rate]:
        stmt = select(Rate).where(
            Rate.product_id == product_id,
            Rate.tenant_id == tenant_id,
            Rate.lifecycle_status == "active",
        )
        if exclude_rate_id:
            stmt = stmt.where(Rate.id != exclude_rate_id)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def insert_rate(self, *, rate_id: str, tenant_id: str = DEFAULT_TENANT_ID, values: dict[str, Any]) -> Rate:
        now = datetime.now(timezone.utc)
        rate = Rate(id=rate_id, tenant_id=tenant_id, created_at=now, updated_at=now, **values)
        self.session.add(rate)
        await self.session.flush()
        return rate

    async def replace_lines(self, rate_id: str, *, tenant_id: str = DEFAULT_TENANT_ID, lines: list[dict[str, Any]]) -> list[RatePriceLine]:
        await self.session.execute(delete(RatePriceLine).where(RatePriceLine.rate_id == rate_id))
        created: list[RatePriceLine] = []
        for line_values in lines:
            line = RatePriceLine(rate_id=rate_id, tenant_id=tenant_id, **line_values)
            self.session.add(line)
            created.append(line)
        await self.session.flush()
        return created

    async def update_header(self, rate: Rate, *, values: dict[str, Any]) -> Rate:
        for field, value in values.items():
            setattr(rate, field, value)
        rate.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return rate

    async def set_lifecycle_status(self, rate: Rate, *, lifecycle_status: str, validation_flags: list[str] | None = None) -> Rate:
        rate.lifecycle_status = lifecycle_status
        if validation_flags is not None:
            rate.validation_flags_json = validation_flags
        rate.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return rate

    async def delete_draft(self, rate: Rate) -> None:
        # ORM cascade="all, delete-orphan" on Rate.lines handles child price lines.
        await self.session.delete(rate)
        await self.session.flush()

    async def get_source(self, source_id: str, *, tenant_id: str = DEFAULT_TENANT_ID) -> RateSource | None:
        source = await self.session.get(RateSource, source_id)
        if source is None or source.tenant_id != tenant_id:
            return None
        return source

    async def insert_source(self, *, source_id: str, tenant_id: str = DEFAULT_TENANT_ID, values: dict[str, Any]) -> RateSource:
        now = datetime.now(timezone.utc)
        source = RateSource(id=source_id, tenant_id=tenant_id, created_at=now, updated_at=now, **values)
        self.session.add(source)
        await self.session.flush()
        return source
