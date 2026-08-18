from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.outbox import OutboxEvent


class OutboxRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_event(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict[str, Any],
        brand_id: str | None = None,
        actor_email: str | None = None,
        correlation_id: str | None = None,
        event_id: str | None = None,
    ) -> OutboxEvent:
        event = OutboxEvent(
            id=event_id or f"evt_{uuid.uuid4().hex}",
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            brand_id=brand_id,
            actor_email=actor_email,
            correlation_id=correlation_id,
            payload_json=payload,
            status="PENDING",
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(event)
        return event

    async def claim_pending_events(self, limit: int = 50) -> list[OutboxEvent]:
        query = (
            select(OutboxEvent)
            .where(OutboxEvent.status == "PENDING")
            .order_by(OutboxEvent.created_at)
            .limit(limit)
        )
        result = await self.session.scalars(query)
        return list(result)

    async def mark_published(self, event_id: str) -> None:
        event = await self.session.get(OutboxEvent, event_id)
        if event:
            event.status = "PUBLISHED"
            event.published_at = datetime.now(timezone.utc)

    async def mark_failed(self, event_id: str, error: str) -> None:
        event = await self.session.get(OutboxEvent, event_id)
        if event:
            event.attempts += 1
            event.last_error = error[:1000]
            if event.attempts >= event.max_attempts:
                event.status = "FAILED"
