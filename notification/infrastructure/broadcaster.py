from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator

log = logging.getLogger(__name__)


class SSEBroadcaster:
    """In-memory Pub/Sub registry for Server-Sent Events (SSE) subscribers."""

    def __init__(self):
        # Maps email -> set of asyncio.Queue
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, recipient_email: str) -> asyncio.Queue[dict[str, Any]]:
        norm_email = recipient_email.strip().lower()
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        async with self._lock:
            if norm_email not in self._subscribers:
                self._subscribers[norm_email] = set()
            self._subscribers[norm_email].add(queue)
        log.info("Client subscribed to SSE notifications for %s", norm_email)
        return queue

    async def unsubscribe(self, recipient_email: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        norm_email = recipient_email.strip().lower()
        async with self._lock:
            if norm_email in self._subscribers:
                self._subscribers[norm_email].discard(queue)
                if not self._subscribers[norm_email]:
                    del self._subscribers[norm_email]
        log.info("Client unsubscribed from SSE notifications for %s", norm_email)

    async def publish(self, recipient_email: str, event_data: dict[str, Any]) -> int:
        norm_email = recipient_email.strip().lower()
        count = 0
        async with self._lock:
            target_queues = set(self._subscribers.get(norm_email, set()))
            # Also notify broadcast listeners
            if norm_email != "all@workspace.internal":
                target_queues.update(self._subscribers.get("all@workspace.internal", set()))

            for queue in target_queues:
                try:
                    queue.put_nowait(event_data)
                    count += 1
                except Exception as exc:
                    log.warning("Failed to enqueue SSE event: %s", exc)

        return count


# Singleton instance for the process
_global_broadcaster = SSEBroadcaster()


def get_sse_broadcaster() -> SSEBroadcaster:
    return _global_broadcaster
