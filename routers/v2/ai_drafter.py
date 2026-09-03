"""V2 AI Service Drafter routes (15.7 §1.6) — 3 operations on top of a costing sheet.

Auth mirrors ``routers/v2/costing.py``: a sheet not yet attached to a quotation has no owner
(any authenticated editor may work it); once attached, ownership is enforced via
``require_owned_v2_quotation``. No top-level ``import main`` — DI only through
``api/dependencies.py``, like every other V2 router.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, status

from api.dependencies import DbSessionDep, EditorPrincipalDep, require_owned_v2_quotation
from core.kernel import ActorRef
from repositories.costing_repository import CostingRepository
from schemas.trip_profile import TripProfile
from schemas.v2.ai_drafter import (
    AiRunListResponseSchema,
    AiRunSummarySchema,
    AnalyzeRequestSchema,
    AnalyzeResponseSchema,
    DraftRequestSchema,
    DraftResponseSchema,
)
from services.ai_drafter.draft_run_service import (
    DraftConflictError,
    DraftValidationError,
    find_existing_run,
    list_runs,
    run_draft,
)
from services.ai_drafter.trip_analyst import analyze_trip

router = APIRouter(prefix="/api/v2/costing-sheets", tags=["ai-drafter"])

ANCHOR_TYPE = "costing_sheet"


def _actor_from_principal(principal: EditorPrincipalDep) -> ActorRef:
    return ActorRef(actor_id=principal.email or "unknown", actor_type="staff")


async def _get_sheet_or_404(sheet_id: str, session, principal: EditorPrincipalDep):
    sheet = await CostingRepository(session).get_sheet_by_id(sheet_id)
    if sheet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Costing sheet '{sheet_id}' was not found.")
    if sheet.quotation_id:
        await require_owned_v2_quotation(sheet.quotation_id, principal)
    return sheet


@router.post("/{sheet_id}/ai/analyze", response_model=AnalyzeResponseSchema)
async def analyze_trip_route(
    sheet_id: str,
    payload: AnalyzeRequestSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep,
    # H9: ai_runs.idempotency_key is String(128) — an oversized header would otherwise crash
    # the eventual insert with an opaque DataError deep inside a run instead of a clean 422.
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
) -> AnalyzeResponseSchema:
    sheet = await _get_sheet_or_404(sheet_id, session, principal)
    actor = _actor_from_principal(principal)

    existing = await find_existing_run(session, anchor_id=sheet.id, idempotency_key=idempotency_key, agent_name="trip_analyst")
    if existing is not None:
        stored = existing.output_json.get("trip_profile")
        if stored:
            profile = TripProfile.model_validate(stored)
            return AnalyzeResponseSchema(
                run_id=existing.id,
                trip_profile=profile,
                fallback_used=bool(existing.output_json.get("fallback_used")),
                confidence_notes=profile.confidence_notes,
            )

    # H3: the DB unique constraint on ``ai_runs`` is agent-agnostic — a key already used by a
    # different agent (e.g. Draft) on this sheet must not fall through to a real LLM call and
    # an eventual opaque IntegrityError; reject it up front instead.
    other_agent_run = await find_existing_run(session, anchor_id=sheet.id, idempotency_key=idempotency_key)
    if other_agent_run is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Idempotency-Key '{idempotency_key}' was already used by a different operation "
                f"('{other_agent_run.agent_name}') on this sheet — use a new key."
            ),
        )

    profile, fallback_used = await analyze_trip(
        session,
        raw_text=payload.raw_text,
        anchor_type=ANCHOR_TYPE,
        anchor_id=sheet.id,
        idempotency_key=idempotency_key,
        actor=actor,
    )
    await session.commit()

    run = await find_existing_run(session, anchor_id=sheet.id, idempotency_key=idempotency_key, agent_name="trip_analyst")
    return AnalyzeResponseSchema(
        run_id=run.id if run else idempotency_key,
        trip_profile=profile,
        fallback_used=fallback_used,
        confidence_notes=profile.confidence_notes,
    )


@router.post("/{sheet_id}/ai/draft", response_model=DraftResponseSchema)
async def draft_services_route(
    sheet_id: str,
    payload: DraftRequestSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep,
    # H9: ai_runs.idempotency_key is String(128) — an oversized header would otherwise crash
    # the eventual insert with an opaque DataError deep inside a run instead of a clean 422.
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
) -> DraftResponseSchema:
    sheet = await _get_sheet_or_404(sheet_id, session, principal)
    actor = _actor_from_principal(principal)

    try:
        response = await run_draft(
            session,
            sheet=sheet,
            trip_profile=payload.trip_profile,
            days=payload.days,
            day_numbers_filter=payload.day_numbers,
            base_costing_revision=payload.base_costing_revision,
            actor=actor,
            idempotency_key=idempotency_key,
        )
        await session.commit()
        return response
    except DraftValidationError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)) from err
    except DraftConflictError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": str(err), "currentRevision": err.current_revision},
        ) from err


@router.get("/{sheet_id}/ai/runs", response_model=AiRunListResponseSchema)
async def list_ai_runs_route(
    sheet_id: str,
    session: DbSessionDep,
    principal: EditorPrincipalDep,
) -> AiRunListResponseSchema:
    await _get_sheet_or_404(sheet_id, session, principal)
    runs = await list_runs(session, sheet_id=sheet_id)
    return AiRunListResponseSchema(
        runs=[
            AiRunSummarySchema(
                id=run.id,
                agent_name=run.agent_name,
                status=run.status,
                idempotency_key=run.idempotency_key,
                stats=run.stats_json,
                created_at=run.created_at.isoformat(),
            )
            for run in runs
        ]
    )
