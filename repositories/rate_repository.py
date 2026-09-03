from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models.rate import Rate, RatePriceLine, RateSource

DEFAULT_TENANT_ID = "capella"


class RateLifecycleRaceError(Exception):
    """A conditional lifecycle transition lost to another writer."""


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
        # Blackouts are JSON and therefore evaluated by the shared pure
        # selection adapter in the service. Keeping all product rates here
        # makes ``total`` agree with the returned blackout-filtered set.
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

    async def replace_lines(self, rate: Rate, *, tenant_id: str = DEFAULT_TENANT_ID, lines: list[dict[str, Any]]) -> list[RatePriceLine]:
        # Async ORM relationships must be loaded explicitly before collection
        # mutation; otherwise ``clear`` attempts a forbidden implicit lazy load.
        await self.session.refresh(rate, attribute_names=["lines"])
        rate.lines.clear()
        # Flush orphan deletes before adding equal unique keys. SQLAlchemy's
        # unit-of-work otherwise batches inserts before deletes on SQLite/PG.
        await self.session.flush()
        created: list[RatePriceLine] = []
        for line_values in lines:
            line = RatePriceLine(tenant_id=tenant_id, **line_values)
            rate.lines.append(line)
            created.append(line)
        await self.session.flush()
        return created

    async def update_header(self, rate: Rate, *, values: dict[str, Any]) -> Rate:
        for field, value in values.items():
            setattr(rate, field, value)
        rate.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return rate

    async def set_lifecycle_status(
        self,
        rate: Rate,
        *,
        expected_status: str,
        lifecycle_status: str,
        validation_flags: list[str] | None = None,
    ) -> Rate:
        now = datetime.now(timezone.utc)
        values: dict[str, Any] = {"lifecycle_status": lifecycle_status, "updated_at": now}
        if validation_flags is not None:
            values["validation_flags_json"] = validation_flags
        result = await self.session.execute(
            update(Rate)
            .where(Rate.id == rate.id, Rate.tenant_id == rate.tenant_id, Rate.lifecycle_status == expected_status)
            .values(**values)
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            raise RateLifecycleRaceError(rate.id, expected_status)
        rate.lifecycle_status = lifecycle_status
        rate.updated_at = now
        if validation_flags is not None:
            rate.validation_flags_json = validation_flags
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

    async def get_sources_by_ids(self, source_ids: set[str], *, tenant_id: str = DEFAULT_TENANT_ID) -> dict[str, RateSource]:
        if not source_ids:
            return {}
        result = await self.session.scalars(
            select(RateSource).where(RateSource.id.in_(source_ids), RateSource.tenant_id == tenant_id)
        )
        return {source.id: source for source in result}

    async def insert_source(self, *, source_id: str, tenant_id: str = DEFAULT_TENANT_ID, values: dict[str, Any]) -> RateSource:
        now = datetime.now(timezone.utc)
        source = RateSource(id=source_id, tenant_id=tenant_id, created_at=now, updated_at=now, **values)
        self.session.add(source)
        await self.session.flush()
        return source
