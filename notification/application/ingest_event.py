from __future__ import annotations

import logging
from sqlalchemy.ext.asyncio import AsyncSession

from notification.domain.events import IntegrationEvent
from notification.domain.policy import NotificationPolicy
from notification.domain.templates import NotificationTemplateEngine
from notification.infrastructure.broadcaster import get_sse_broadcaster
from notification.infrastructure.db.models import Notification
from notification.infrastructure.db.repository import NotificationRepository

log = logging.getLogger(__name__)


class IngestEventUseCase:
    """Orchestrates event ingestion, policy application, storage, and immediate in-app broadcast."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = NotificationRepository(session)
        self.broadcaster = get_sse_broadcaster()

    async def execute(self, event: IntegrationEvent) -> list[Notification]:
        # 1. Resolve recipients according to policy
        recipients = NotificationPolicy.resolve_recipients(event)
        severity = NotificationPolicy.resolve_severity(event)
        action_url = NotificationPolicy.resolve_action_url(event)
        channels = [c.value for c in NotificationPolicy.resolve_channels(event)]
        title, body = NotificationTemplateEngine.render(event)

        created_notifications: list[Notification] = []

        for r in recipients:
            recipient_email = r["email"]
            if not recipient_email:
                continue
            recipient_profile_id = r.get("profile_id")

            # 2. Persist notification and delivery records
            notif = await self.repo.create_notification(
                source_service=event.source_service,
                source_event_id=event.event_id,
                notification_type=event.event_type,
                recipient_email=recipient_email,
                recipient_profile_id=recipient_profile_id,
                brand_id=event.brand_id,
                title=title,
                body=body,
                severity=severity.value,
                action_url=action_url,
                aggregate_type=event.aggregate_type,
                aggregate_id=event.aggregate_id,
                metadata_json=event.payload,
                channels=channels,
            )
            created_notifications.append(notif)

        # Commit to save records
        await self.session.commit()

        # 3. Trigger immediate SSE in-app broadcast
        for notif in created_notifications:
            payload_data = {
                "id": notif.id,
                "source_service": notif.source_service,
                "source_event_id": notif.source_event_id,
                "notification_type": notif.notification_type,
                "title": notif.title,
                "body": notif.body,
                "severity": notif.severity,
                "action_url": notif.action_url,
                "aggregate_type": notif.aggregate_type,
                "aggregate_id": notif.aggregate_id,
                "is_read": notif.is_read,
                "created_at": notif.created_at.isoformat() if notif.created_at else None,
                "metadata": notif.metadata_json,
            }
            await self.broadcaster.publish(notif.recipient_email, {
                "event": "notification",
                "data": payload_data,
            })

        return created_notifications
