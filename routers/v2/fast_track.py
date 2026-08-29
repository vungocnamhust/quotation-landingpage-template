"""HTTP boundary for server-owned Fast Track assembly."""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterable
from typing import Annotated, Literal

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel, Field

from api.dependencies import DbSessionDep, EditorPrincipalDep, OwnedV2QuotationDep
from repositories.errors import DocumentRevisionConflictError
from services.content_action_application_service import (
    ContentActionNotFoundError,
    ContentActionPolicyError,
)
from services.fast_track_assembly_service import (
    FastTrackAssemblyService,
    FastTrackNotFoundError,
    FastTrackReviewBlockedError,
)
from services.fast_track_progress import ProgressEmitter, get_fast_track_progress_broadcaster
from services.section_content_generator import ContentGenerationError

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/quotations", tags=["fast-track"])
IdempotencyKeyHeader = Annotated[str, Header(alias="Idempotency-Key", min_length=1)]
CorrelationIdHeader = Annotated[str, Header(alias="X-Correlation-ID", min_length=1)]


class FastTrackAssembleRequest(BaseModel):
    baseRevision: int = Field(ge=1)
    writingStyle: Literal["storytelling", "detailed"] = "storytelling"


class FastTrackAssembleResponse(BaseModel):
    status: Literal["complete"]
    quotationId: str
    currentRevision: int
    review: dict


@router.post("/{quotation_id}/fast-track/assemble", response_model=FastTrackAssembleResponse)
async def assemble_fast_track(
    quotation_id: str,
    payload: FastTrackAssembleRequest,
    principal: EditorPrincipalDep,
    _owned: OwnedV2QuotationDep,
    session: DbSessionDep,
    idempotency_key: IdempotencyKeyHeader,
    correlation_id: CorrelationIdHeader,
    lang: str | None = None,
) -> FastTrackAssembleResponse:
    import main

    quotation, effective_lang = await main._resolve_v2_locale(quotation_id, lang)
    service = FastTrackAssemblyService(session)
    # Bound to the client's own X-Correlation-ID (16.3 F-21): the GET stream
    # endpoint below subscribes to the same channel, so the client only needs
    # one id to correlate its progress feed with this POST's work.
    progress = ProgressEmitter(correlation_id=correlation_id)

    async def apply_media(document: dict) -> dict:
        return await main._apply_missing_media_defaults(session, document, quotation_id, effective_lang)

    def normalize(document: dict, revision: int) -> dict:
        return main._normalize_quote_document_structure_or_422(
            main._hydrate_canonical_quote_document(document, quotation, lang=effective_lang, revision=revision)
        )

    try:
        result = await service.assemble(
            quotation_id=quotation_id, lang=effective_lang, base_revision=payload.baseRevision,
            writing_style=payload.writingStyle, profile_id=principal.person_id,
            correlation_id=correlation_id, idempotency_key=idempotency_key,
            apply_media_defaults=apply_media, normalize_document=normalize,
            review_status=lambda: main._canonical_review_status(quotation_id, effective_lang),
            progress=progress,
        )
        return FastTrackAssembleResponse(**result)
    except FastTrackReviewBlockedError as error:
        await progress.error(message=str(error))
        raise HTTPException(status_code=422, detail={"message": str(error), "review": error.review}) from error
    except DocumentRevisionConflictError as error:
        await progress.error(message="Document revision conflict.")
        raise HTTPException(status_code=409, detail={"message": "Document revision conflict.", "currentRevision": error.current_revision}) from error
    except (FastTrackNotFoundError, ContentActionNotFoundError) as error:
        await progress.error(message=str(error))
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ContentGenerationError as error:
        # Upstream LLM failure/timeout — retryable dependency error, not a 500 (16.3 F-08).
        await progress.error(message=str(error))
        raise HTTPException(status_code=503, detail={"message": str(error)}) from error
    except (ContentActionPolicyError, ValueError) as error:
        await progress.error(message=str(error))
        raise HTTPException(status_code=422, detail={"message": str(error)}) from error


@router.get("/{quotation_id}/fast-track/stream", response_class=EventSourceResponse)
async def stream_fast_track_progress(
    quotation_id: str,
    _principal: EditorPrincipalDep,
    _owned: OwnedV2QuotationDep,
    request: Request,
    correlation_id: Annotated[str, Query(alias="correlationId", min_length=1)],
) -> AsyncIterable[ServerSentEvent]:
    """Observational channel only — the POST above does the actual work and is
    the single source of truth for the outcome. Open this before the POST,
    with the same X-Correlation-ID, and close it on "complete"/"error"
    (16.3 F-21: replaces the client's fabricated progress percentages)."""
    broadcaster = get_fast_track_progress_broadcaster()
    queue = await broadcaster.subscribe(correlation_id)
    yield ServerSentEvent(data=json.dumps({"status": "connected"}), event="connected")
    try:
        while True:
            if await request.is_disconnected():
                break
            try:
                item = await asyncio.wait_for(queue.get(), timeout=20.0)
                event_name = item.get("event", "progress")
                yield ServerSentEvent(data=json.dumps(item.get("data", {})), event=event_name)
                if event_name in {"complete", "error"}:
                    break
            except asyncio.TimeoutError:
                yield ServerSentEvent(comment="ping")
    except (asyncio.CancelledError, GeneratorExit):
        log.info("Fast Track progress client disconnected: quotation=%s correlation=%s", quotation_id, correlation_id)
    finally:
        await broadcaster.unsubscribe(correlation_id, queue)
