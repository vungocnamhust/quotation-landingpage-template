from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from notification.infrastructure.db.models import (
    Notification,
    NotificationDelivery,
    NotificationPreference,
)


class NotificationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_notification(
        self,
        source_service: str,
        source_event_id: str,
        notification_type: str,
        recipient_email: str,
        title: str,
        body: str,
        severity: str,
        recipient_profile_id: str | None = None,
        brand_id: str | None = None,
        action_url: str | None = None,
        aggregate_type: str | None = None,
        aggregate_id: str | None = None,
        metadata_json: dict[str, Any] | None = None,
        channels: list[str] | None = None,
    ) -> Notification:
        # Check deduplication
        existing = await self.get_by_dedupe(
            source_service=source_service,
            source_event_id=source_event_id,
            notification_type=notification_type,
            recipient_email=recipient_email,
        )
        if existing:
            return existing

        notif_id = f"notif_{uuid.uuid4().hex}"
        notif = Notification(
            id=notif_id,
            source_service=source_service,
            source_event_id=source_event_id,
            notification_type=notification_type,
            recipient_profile_id=recipient_profile_id,
            recipient_email=recipient_email,
            brand_id=brand_id,
            title=title,
            body=body,
            severity=severity,
            action_url=action_url,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            metadata_json=metadata_json or {},
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(notif)

        # Create deliveries for each channel
        for ch in (channels or ["INAPP_SSE"]):
            delivery = NotificationDelivery(
                id=f"del_{uuid.uuid4().hex}",
                notification_id=notif_id,
                channel=ch,
                status="PENDING",
                attempts=0,
                max_attempts=5,
                next_attempt_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
            )
            self.session.add(delivery)

        return notif

    async def get_by_dedupe(
        self,
        source_service: str,
        source_event_id: str,
        notification_type: str,
        recipient_email: str,
    ) -> Notification | None:
        stmt = select(Notification).where(
            Notification.source_service == source_service,
            Notification.source_event_id == source_event_id,
            Notification.notification_type == notification_type,
            Notification.recipient_email == recipient_email,
        )
        return await self.session.scalar(stmt)

    async def get_by_id(self, notification_id: str) -> Notification | None:
        return await self.session.get(Notification, notification_id)

    async def list_for_recipient(
        self,
        recipient_email: str,
        is_read: bool | None = None,
        severity: str | None = None,
        limit: int = 30,
        offset: int = 0,
    ) -> tuple[list[Notification], int]:
        stmt = select(Notification).where(
            (Notification.recipient_email == recipient_email) | (Notification.recipient_email == "all@workspace.internal")
        )
        if is_read is not None:
            stmt = stmt.where(Notification.is_read.is_(is_read))
        if severity is not None:
            stmt = stmt.where(Notification.severity == severity)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.scalar(count_stmt)) or 0

        # Query items
        stmt = stmt.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
        items = list(await self.session.scalars(stmt))
        return items, total

    async def count_unread_for_recipient(self, recipient_email: str) -> int:
        stmt = select(func.count(Notification.id)).where(
            ((Notification.recipient_email == recipient_email) | (Notification.recipient_email == "all@workspace.internal")),
            Notification.is_read.is_(False),
        )
        return (await self.session.scalar(stmt)) or 0

    async def mark_read(self, notification_id: str, recipient_email: str) -> Notification | None:
        notif = await self.get_by_id(notification_id)
        if notif and (notif.recipient_email == recipient_email or notif.recipient_email == "all@workspace.internal"):
            notif.is_read = True
            notif.read_at = datetime.now(timezone.utc)
            return notif
        return None

    async def mark_all_read(self, recipient_email: str) -> int:
        now = datetime.now(timezone.utc)
        stmt = (
            update(Notification)
            .where(
                ((Notification.recipient_email == recipient_email) | (Notification.recipient_email == "all@workspace.internal")),
                Notification.is_read.is_(False),
            )
            .values(is_read=True, read_at=now)
        )
        result = await self.session.execute(stmt)
        return int(result.rowcount or 0)
