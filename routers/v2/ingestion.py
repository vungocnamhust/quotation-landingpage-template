"""V2 Interactive Ingestion Co-Pilot routes (15.8 §1.7) — 7 operations.

Extract/Answer/Edit/Reject require ``require_editor``; Commit requires ``require_quote_admin``
(the person who bumps a batch into the real catalog is explicitly accountable, same gate as
other catalog-mutating actions). Uses ``api/dependencies.py`` DI like every other V2 router —
no top-level ``import main``.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Query, status

from api.dependencies import DbSessionDep, EditorPrincipalDep, QuoteAdminPrincipalDep
from core.kernel import ActorRef
from repositories.ingestion_repository import IngestionBatchRevisionConflictError, IngestionRepository
from schemas.catalog_ingest import (
    CatalogIngestPayload,
    IngestionBatchAnswersRequestSchema,
    IngestionBatchCommitRequestSchema,
    IngestionBatchCreateRequestSchema,
    IngestionBatchEditsRequestSchema,
    IngestionBatchListResponseSchema,
    IngestionBatchRejectRequestSchema,
    IngestionBatchResponseSchema,
    IngestionBatchStatus,
    IngestionBatchSummarySchema,
)
from services.ingestion.commit_service import CommitError, apply_edits_overlay, commit_batch
from services.ingestion.extraction_service import ExtractionError, create_batch, parse_payload
from services.ingestion.resolution_service import (
    BatchNotAnswerableError,
    ResolutionError,
    TooManyClarificationRoundsError,
    answer_clarifications,
    run_first_round,
)

router = APIRouter(prefix="/api/v2/ingestion-batches", tags=["ingestion"])

MAX_BATCHES_PER_ACTOR_PER_DAY = 50

# H6: a batch that already reached a terminal state must never accept further edits or a
# second rejection — editing a ``committed`` batch can flip it back to ``needs_clarification``
# (a committable state), opening the door to a duplicate commit replaying the whole resolution
# plan against the real catalog a second time.
_TERMINAL_BATCH_STATUSES = frozenset({"committed", "rejected", "archived"})


def _terminal_status_conflict(batch_id: str, current_status: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"Ingestion batch '{batch_id}' is '{current_status}' and can no longer be modified.",
    )


def _actor_from_principal(principal) -> ActorRef:
    return ActorRef(actor_id=principal.email or "unknown", actor_type="staff")


def _conflict_detail(batch_id: str, expected_revision: int) -> dict:
    return {
        "message": f"Ingestion batch '{batch_id}' moved past revision {expected_revision} while this write was in flight.",
        "currentRevision": expected_revision,
    }


def _to_response(batch) -> IngestionBatchResponseSchema:
    stored = batch.payload_json or {}
    return IngestionBatchResponseSchema(
        id=batch.id,
        status=batch.status,
        raw_text=batch.raw_text,
        source_channel=batch.source_channel,
        source_document_type=batch.source_document_type,
        payload=stored.get("payload", {}),
        parsed=stored.get("parsed", {}),
        resolution=batch.resolution_json,
        conversation=batch.conversation_json or [],
        operator_edits=batch.operator_edits_json or {},
        commit_result=batch.commit_result_json,
        error=batch.error_json,
        batch_revision=batch.batch_revision,
        created_at=batch.created_at,
        updated_at=batch.updated_at,
    )


def _to_summary(batch) -> IngestionBatchSummarySchema:
    stored = batch.payload_json or {}
    payload = stored.get("payload", {})
    return IngestionBatchSummarySchema(
        id=batch.id,
        status=batch.status,
        source_channel=batch.source_channel,
        source_document_type=batch.source_document_type,
        unresolved_count=len(payload.get("unresolved", [])),
        products_count=len(payload.get("products", [])),
        rate_groups_count=len(payload.get("rate_groups", [])),
        created_at=batch.created_at,
        updated_at=batch.updated_at,
    )


async def _get_batch_or_404(session: DbSessionDep, batch_id: str):
    batch = await IngestionRepository(session).get_by_id(batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingestion batch was not found.")
    return batch


@router.post("", response_model=IngestionBatchResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_ingestion_batch(
    payload: IngestionBatchCreateRequestSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> IngestionBatchResponseSchema:
    actor = _actor_from_principal(principal)

    since = datetime.now(timezone.utc) - timedelta(days=1)
    recent_count = await IngestionRepository(session).count_created_since(created_by=actor.serialize(), since=since)
    if recent_count >= MAX_BATCHES_PER_ACTOR_PER_DAY:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: at most {MAX_BATCHES_PER_ACTOR_PER_DAY} ingestion batches per user per day.",
        )

    try:
        batch, extracted, parsed, is_replay = await create_batch(
            session,
            raw_text=payload.raw_text,
            source_channel=payload.source_channel,
            source_document_type=payload.source_document_type,
            idempotency_key=idempotency_key,
            actor=actor,
        )
    except ExtractionError as err:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(err)) from err

    if not is_replay:
        try:
            batch = await run_first_round(session, batch=batch, payload=extracted, parsed=parsed, actor=actor)
        except ResolutionError as err:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(err)) from err

    await session.commit()
    return _to_response(batch)


@router.get("", response_model=IngestionBatchListResponseSchema)
async def list_ingestion_batches(
    session: DbSessionDep,
    principal: EditorPrincipalDep,
    status_filter: Annotated[IngestionBatchStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> IngestionBatchListResponseSchema:
    items, total = await IngestionRepository(session).list(status=status_filter, limit=limit)
    return IngestionBatchListResponseSchema(items=[_to_summary(b) for b in items], total=total)


@router.get("/{batch_id}", response_model=IngestionBatchResponseSchema)
async def get_ingestion_batch(
    batch_id: str,
    session: DbSessionDep,
    principal: EditorPrincipalDep,
) -> IngestionBatchResponseSchema:
    batch = await _get_batch_or_404(session, batch_id)
    return _to_response(batch)


@router.post("/{batch_id}/answers", response_model=IngestionBatchResponseSchema)
async def answer_ingestion_batch_clarifications(
    batch_id: str,
    payload: IngestionBatchAnswersRequestSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep,
) -> IngestionBatchResponseSchema:
    batch = await _get_batch_or_404(session, batch_id)
    actor = _actor_from_principal(principal)
    try:
        updated = await answer_clarifications(
            session,
            batch=batch,
            answers=payload.answers,
            actor=actor,
            expected_revision=payload.base_batch_revision,
        )
    except TooManyClarificationRoundsError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)) from err
    except BatchNotAnswerableError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(err)) from err
    except IngestionBatchRevisionConflictError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_conflict_detail(batch_id, payload.base_batch_revision)) from None
    except ResolutionError as err:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(err)) from err

    await session.commit()
    return _to_response(updated)


@router.put("/{batch_id}/edits", response_model=IngestionBatchResponseSchema)
async def edit_ingestion_batch(
    batch_id: str,
    payload: IngestionBatchEditsRequestSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep,
) -> IngestionBatchResponseSchema:
    batch = await _get_batch_or_404(session, batch_id)
    if batch.status in _TERMINAL_BATCH_STATUSES:
        raise _terminal_status_conflict(batch_id, batch.status)
    actor = _actor_from_principal(principal)

    stored = batch.payload_json or {}
    merged_edits = {**(batch.operator_edits_json or {}), **payload.edits}
    merged_payload_dict = apply_edits_overlay(stored.get("payload", {}), {k: str(v) for k, v in merged_edits.items()})
    reparsed_payload, parsed = parse_payload(CatalogIngestPayload.model_validate(merged_payload_dict).model_copy(update={"unresolved": []}))

    repository = IngestionRepository(session)
    try:
        updated = await repository.update_guarded(
            batch,
            expected_revision=payload.base_batch_revision,
            values={
                "payload_json": {"payload": reparsed_payload.model_dump(mode="json"), "parsed": parsed},
                "operator_edits_json": merged_edits,
                "status": "needs_clarification" if reparsed_payload.unresolved else batch.status,
                "updated_by": actor.serialize(),
            },
        )
    except IngestionBatchRevisionConflictError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_conflict_detail(batch_id, payload.base_batch_revision)) from None

    await session.commit()
    return _to_response(updated)


@router.post("/{batch_id}/commit", response_model=IngestionBatchResponseSchema)
async def commit_ingestion_batch(
    batch_id: str,
    payload: IngestionBatchCommitRequestSchema,
    session: DbSessionDep,
    principal: QuoteAdminPrincipalDep,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> IngestionBatchResponseSchema:
    batch = await _get_batch_or_404(session, batch_id)
    actor = _actor_from_principal(principal)
    try:
        committed = await commit_batch(
            session,
            batch=batch,
            actor=actor,
            expected_revision=payload.base_batch_revision,
            idempotency_key=idempotency_key,
            acknowledge_unresolved=payload.acknowledge_unresolved,
        )
    except CommitError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)) from err
    except IngestionBatchRevisionConflictError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_conflict_detail(batch_id, payload.base_batch_revision)) from None

    await session.commit()
    return _to_response(committed)


@router.post("/{batch_id}/reject", response_model=IngestionBatchResponseSchema)
async def reject_ingestion_batch(
    batch_id: str,
    payload: IngestionBatchRejectRequestSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep,
) -> IngestionBatchResponseSchema:
    batch = await _get_batch_or_404(session, batch_id)
    if batch.status in _TERMINAL_BATCH_STATUSES:
        raise _terminal_status_conflict(batch_id, batch.status)
    actor = _actor_from_principal(principal)
    repository = IngestionRepository(session)
    try:
        updated = await repository.update_guarded(
            batch,
            expected_revision=payload.base_batch_revision,
            values={
                "status": "rejected",
                "error_json": {"reason": payload.reason} if payload.reason else batch.error_json,
                "updated_by": actor.serialize(),
            },
        )
    except IngestionBatchRevisionConflictError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_conflict_detail(batch_id, payload.base_batch_revision)) from None

    await session.commit()
    return _to_response(updated)
