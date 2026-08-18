from __future__ import annotations

import asyncio
import logging
import os
import httpx

from db.session import get_session_factory
from repositories.outbox_repository import OutboxRepository

log = logging.getLogger("quotation.outbox_relay")

NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8116").rstrip("/")
SERVICE_TOKEN = os.getenv("QUOTE_SERVICE_TOKEN", "default-dev-service-token")


async def publish_outbox_events_batch(batch_size: int = 30) -> int:
    session_factory = get_session_factory()
    async with session_factory() as session:
        repo = OutboxRepository(session)
        events = await repo.claim_pending_events(limit=batch_size)
        if not events:
            return 0

        async with httpx.AsyncClient(timeout=5.0) as client:
            for ev in events:
                payload = {
                    "event_id": ev.id,
                    "source_service": "quotation-app",
                    "event_type": ev.event_type,
                    "event_version": 1,
                    "occurred_at": ev.created_at.isoformat() if ev.created_at else None,
                    "aggregate_type": ev.aggregate_type,
                    "aggregate_id": ev.aggregate_id,
                    "brand_id": ev.brand_id,
                    "actor_email": ev.actor_email,
                    "correlation_id": ev.correlation_id,
                    "payload": ev.payload_json,
                }
                headers = {
                    "X-Quote-Service-Token": SERVICE_TOKEN,
                    "Content-Type": "application/json",
                }
                try:
                    resp = await client.post(
                        f"{NOTIFICATION_SERVICE_URL}/api/v2/events",
                        json=payload,
                        headers=headers,
                    )
                    if resp.status_code in (200, 201):
                        await repo.mark_published(ev.id)
                    else:
                        await repo.mark_failed(ev.id, f"HTTP {resp.status_code}: {resp.text[:500]}")
                except Exception as exc:
                    log.warning("Failed to forward outbox event %s: %s", ev.id, exc)
                    await repo.mark_failed(ev.id, str(exc))

        await session.commit()
        return len(events)


async def run_outbox_relay_loop(interval: float = 2.0):
    log.info("Starting Quotation Outbox Relay loop forwarding to %s...", NOTIFICATION_SERVICE_URL)
    while True:
        try:
            processed = await publish_outbox_events_batch()
            if processed == 0:
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            log.info("Outbox relay stopped.")
            break
        except Exception as exc:
            log.error("Unexpected error in outbox relay: %s", exc)
            await asyncio.sleep(interval)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    asyncio.run(run_outbox_relay_loop())
