from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from notification.infrastructure.broadcaster import get_sse_broadcaster
from notification.infrastructure.db.base import get_notification_session_factory
from notification.infrastructure.db.models import Notification, NotificationDelivery

log = logging.getLogger("notification.delivery_worker")


async def process_batch(session: AsyncSession, batch_size: int = 20) -> int:
    now = datetime.now(timezone.utc)

    # 1. Claim pending/retrying deliveries safely with FOR UPDATE SKIP LOCKED
    stmt = (
        select(NotificationDelivery)
        .where(
            NotificationDelivery.status.in_(["PENDING", "RETRYING"]),
            NotificationDelivery.next_attempt_at <= now,
        )
        .order_by(NotificationDelivery.created_at)
        .with_for_update(skip_locked=True)
        .limit(batch_size)
    )

    result = await session.scalars(stmt)
    claimed_deliveries = list(result)
    if not claimed_deliveries:
        return 0

    for d in claimed_deliveries:
        d.status = "PROCESSING"
        d.attempts += 1

    # Commit state change to release row locks before doing external work
    await session.commit()

    # 2. Process each delivery outside the DB lock
    broadcaster = get_sse_broadcaster()

    for d in claimed_deliveries:
        try:
            notif = await session.get(Notification, d.notification_id)
            if not notif:
                d.status = "DEAD"
                d.last_error = "Notification record not found"
                continue

            if d.channel == "INAPP_SSE":
                # Push to in-app SSE subscribers
                await broadcaster.publish(notif.recipient_email, {
                    "event": "notification",
                    "data": {
                        "id": notif.id,
                        "title": notif.title,
                        "body": notif.body,
                        "severity": notif.severity,
                        "action_url": notif.action_url,
                        "created_at": notif.created_at.isoformat() if notif.created_at else None,
                    },
                })
            elif d.channel == "EMAIL":
                # External email adapter (placeholder/log for now)
                log.info("Simulating email send for notification %s to %s", notif.id, notif.recipient_email)

            d.status = "SENT"
            d.sent_at = datetime.now(timezone.utc)
            d.last_error = None
        except Exception as exc:
            log.warning("Delivery %s failed attempt %d: %s", d.id, d.attempts, exc)
            if d.attempts >= d.max_attempts:
                d.status = "DEAD"
                d.last_error = str(exc)[:1000]
            else:
                d.status = "RETRYING"
                # Exponential backoff with jitter
                delay = min(300, (2 ** d.attempts)) + random.uniform(0.5, 2.0)
                d.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
                d.last_error = str(exc)[:1000]

    await session.commit()
    return len(claimed_deliveries)


async def run_delivery_worker_loop(poll_interval: float = 3.0):
    log.info("Starting Notification Delivery Worker loop...")
    session_factory = get_notification_session_factory()
    while True:
        try:
            async with session_factory() as session:
                processed = await process_batch(session)
                if processed == 0:
                    await asyncio.sleep(poll_interval)
        except asyncio.CancelledError:
            log.info("Delivery worker stopped.")
            break
        except Exception as exc:
            log.error("Unexpected error in delivery worker: %s", exc)
            await asyncio.sleep(poll_interval)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    asyncio.run(run_delivery_worker_loop())
