from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.ingestion import IngestionBatch

DEFAULT_TENANT_ID = "capella"


class IngestionBatchRevisionConflictError(Exception):
    """CAS mismatch on ``batch_revision`` — maps to 409 REVISION_CONFLICT (pattern: costing)."""

    def __init__(self, batch_id: str, expected_revision: int) -> None:
        super().__init__(
            f"Ingestion batch '{batch_id}' moved past revision {expected_revision} while this write was in flight."
        )
        self.batch_id = batch_id
        self.expected_revision = expected_revision


class IngestionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, batch_id: str, *, tenant_id: str = DEFAULT_TENANT_ID) -> IngestionBatch | None:
        batch = await self.session.get(IngestionBatch, batch_id)
        if batch is None or batch.tenant_id != tenant_id:
            return None
        return batch

    async def get_by_idempotency_key(
        self, idempotency_key: str, *, tenant_id: str = DEFAULT_TENANT_ID
    ) -> IngestionBatch | None:
        stmt = select(IngestionBatch).where(
            IngestionBatch.tenant_id == tenant_id, IngestionBatch.idempotency_key == idempotency_key
        )
        return await self.session.scalar(stmt)

    async def list(
        self,
        *,
        tenant_id: str = DEFAULT_TENANT_ID,
        status: str | None = None,
        limit: int = 50,
    ) -> tuple[list[IngestionBatch], int]:
        stmt = (
            select(IngestionBatch)
            .where(IngestionBatch.tenant_id == tenant_id)
            .order_by(IngestionBatch.created_at.desc())
        )
        if status:
            stmt = stmt.where(IngestionBatch.status == status)
        stmt = stmt.limit(max(1, min(limit, 200)))
        result = await self.session.scalars(stmt)
        items = list(result.all())
        return items, len(items)

    async def insert(
        self, *, batch_id: str, tenant_id: str = DEFAULT_TENANT_ID, values: dict[str, Any]
    ) -> IngestionBatch:
        now = datetime.now(timezone.utc)
        batch = IngestionBatch(id=batch_id, tenant_id=tenant_id, created_at=now, updated_at=now, **values)
        self.session.add(batch)
        await self.session.flush()
        return batch

    async def update_guarded(
        self, batch: IngestionBatch, *, expected_revision: int, values: dict[str, Any]
    ) -> IngestionBatch:
        """CAS enforced in SQL: the write only lands if ``batch_revision`` hasn't moved."""
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            update(IngestionBatch)
            .where(IngestionBatch.id == batch.id, IngestionBatch.batch_revision == expected_revision)
            .values(batch_revision=expected_revision + 1, updated_at=now, **values)
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            raise IngestionBatchRevisionConflictError(batch.id, expected_revision)
        batch.batch_revision = expected_revision + 1
        batch.updated_at = now
        for field, value in values.items():
            setattr(batch, field, value)
        return batch

    async def get_revision(self, batch_id: str, *, tenant_id: str = DEFAULT_TENANT_ID) -> int | None:
        stmt = select(IngestionBatch.batch_revision).where(
            IngestionBatch.id == batch_id, IngestionBatch.tenant_id == tenant_id
        )
        return await self.session.scalar(stmt)

    async def count_created_since(
        self, *, created_by: str, since: datetime, tenant_id: str = DEFAULT_TENANT_ID
    ) -> int:
        """Rate-limit counter (15.8 §1.7, pattern: booking's atomic sequence, read-side)."""
        stmt = select(func.count()).select_from(IngestionBatch).where(
            IngestionBatch.tenant_id == tenant_id,
            IngestionBatch.created_by == created_by,
            IngestionBatch.created_at >= since,
        )
        return int(await self.session.scalar(stmt) or 0)
