from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from notification.infrastructure.broadcaster import get_sse_broadcaster
from notification.infrastructure.db.models import Notification
from notification.infrastructure.db.repository import NotificationRepository


class QueryInboxUseCase:
    def __init__(self, session: AsyncSession):
        self.repo = NotificationRepository(session)

    async def list_notifications(
        self,
        recipient_email: str,
        is_read: bool | None = None,
        severity: str | None = None,
        limit: int = 30,
        offset: int = 0,
    ) -> tuple[list[Notification], int, int]:
        items, total = await self.repo.list_for_recipient(
            recipient_email=recipient_email,
            is_read=is_read,
            severity=severity,
            limit=limit,
            offset=offset,
        )
        unread_count = await self.repo.count_unread_for_recipient(recipient_email)
        return items, total, unread_count

    async def get_unread_count(self, recipient_email: str) -> int:
        return await self.repo.count_unread_for_recipient(recipient_email)


class MarkReadUseCase:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = NotificationRepository(session)
        self.broadcaster = get_sse_broadcaster()

    async def mark_read(self, notification_id: str, recipient_email: str) -> Notification | None:
        notif = await self.repo.mark_read(notification_id, recipient_email)
        if notif:
            await self.session.commit()
            unread_count = await self.repo.count_unread_for_recipient(recipient_email)
            await self.broadcaster.publish(recipient_email, {
                "event": "unread_count_updated",
                "data": {"unread_count": unread_count, "notification_id": notification_id, "is_read": True},
            })
        return notif

    async def mark_all_read(self, recipient_email: str) -> tuple[int, int]:
        count = await self.repo.mark_all_read(recipient_email)
        await self.session.commit()
        await self.broadcaster.publish(recipient_email, {
            "event": "unread_count_updated",
            "data": {"unread_count": 0, "marked_count": count, "all_read": True},
        })
        return count, 0
