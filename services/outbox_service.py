from __future__ import annotations

import os
import uuid
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.outbox_repository import OutboxRepository


class OutboxService:
    """Helper service for business services to emit domain events atomically."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = OutboxRepository(session)

    async def emit_event(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict[str, Any],
        brand_id: str | None = None,
        actor_email: str | None = None,
        correlation_id: str | None = None,
        event_id: str | None = None,
    ):
        """Records an outbox event in the current database transaction."""
        eid = event_id or f"evt_{uuid.uuid4().hex}"
        return await self.repo.record_event(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            brand_id=brand_id,
            actor_email=actor_email,
            correlation_id=correlation_id,
            event_id=eid,
        )
