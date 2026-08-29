"""In-memory Server-Sent Events pub/sub for real Fast Track assembly progress.

Mirrors the pattern in notification/infrastructure/broadcaster.py, but keyed
by the client-supplied ``X-Correlation-ID`` of a single assemble call rather
than by recipient email — there is no persistence, no cross-database access,
and no coupling to the notification subsystem (Plan 16.3 F-21: replace the
fabricated client-side progress with events the server actually publishes as
it works).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

log = logging.getLogger(__name__)


class FastTrackProgressBroadcaster:
    """Per-correlation-id Pub/Sub registry, process-local."""

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, correlation_id: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        async with self._lock:
            self._subscribers.setdefault(correlation_id, set()).add(queue)
        return queue

    async def unsubscribe(self, correlation_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        async with self._lock:
            queues = self._subscribers.get(correlation_id)
            if queues is None:
                return
            queues.discard(queue)
            if not queues:
                del self._subscribers[correlation_id]

    async def publish(self, correlation_id: str, event: dict[str, Any]) -> None:
        async with self._lock:
            queues = set(self._subscribers.get(correlation_id, set()))
        for queue in queues:
            try:
                queue.put_nowait(event)
            except Exception as exc:  # pragma: no cover - unbounded queue, defensive only
                log.warning("Failed to enqueue Fast Track progress event: %s", exc)


_global_broadcaster = FastTrackProgressBroadcaster()


def get_fast_track_progress_broadcaster() -> FastTrackProgressBroadcaster:
    return _global_broadcaster


class ProgressEmitter:
    """Bound to one correlation id — the only thing services see (no broadcaster coupling)."""

    def __init__(self, *, correlation_id: str, broadcaster: FastTrackProgressBroadcaster | None = None) -> None:
        self._correlation_id = correlation_id
        self._broadcaster = broadcaster or get_fast_track_progress_broadcaster()

    async def emit(
        self,
        *,
        stage: str,
        message: str,
        current: int | None = None,
        total: int | None = None,
    ) -> None:
        payload: dict[str, Any] = {"stage": stage, "message": message}
        if current is not None:
            payload["current"] = current
        if total is not None:
            payload["total"] = total
        await self._broadcaster.publish(self._correlation_id, {"event": "progress", "data": payload})

    async def complete(self, *, current_revision: int) -> None:
        await self._broadcaster.publish(
            self._correlation_id,
            {"event": "complete", "data": {"stage": "complete", "currentRevision": current_revision}},
        )

    async def error(self, *, message: str) -> None:
        await self._broadcaster.publish(
            self._correlation_id, {"event": "error", "data": {"message": message}}
        )
