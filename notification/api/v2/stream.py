from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterable

from fastapi import APIRouter, Request
from fastapi.sse import EventSourceResponse, ServerSentEvent

from notification.api.dependencies import EditorPrincipalDep
from notification.infrastructure.broadcaster import get_sse_broadcaster

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/notifications", tags=["notifications-stream"])


@router.get("/stream", response_class=EventSourceResponse)
async def stream_notifications(
    request: Request,
    principal: EditorPrincipalDep,
) -> AsyncIterable[ServerSentEvent]:
    """Streams real-time Server-Sent Events (SSE) for the authenticated user."""
    email = (principal.email or "all@workspace.internal").strip().lower()
    broadcaster = get_sse_broadcaster()
    queue = await broadcaster.subscribe(email)

    yield ServerSentEvent(
        data=json.dumps({"status": "connected", "recipient_email": email}),
        event="connected",
    )
    try:
        while True:
            if await request.is_disconnected():
                break

            try:
                item = await asyncio.wait_for(queue.get(), timeout=20.0)
                event_name = item.get("event", "notification")
                data_payload = item.get("data", {})
                data_str = json.dumps(data_payload) if isinstance(data_payload, (dict, list)) else str(data_payload)
                yield ServerSentEvent(
                    data=data_str,
                    event=event_name,
                )
            except asyncio.TimeoutError:
                yield ServerSentEvent(comment="ping")
    except (asyncio.CancelledError, GeneratorExit):
        log.info("SSE client disconnected: %s", email)
    finally:
        await broadcaster.unsubscribe(email, queue)
