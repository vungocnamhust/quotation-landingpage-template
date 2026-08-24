"""Typed HTTP boundary for Actionable Content Plan execution.

The router deliberately has no document, draft, or outbox orchestration.  The
application service owns the transaction and therefore preserves atomicity for
both the review-draft and bypass-apply modes.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException
from api.dependencies import DbSessionDep, EditorPrincipalDep, OwnedV2QuotationDep
from repositories.errors import DocumentRevisionConflictError
from routers.v2.schemas.content_actions import (
    AcceptContentActionPlanRequest,
    BypassContentActionsRequest,
    ContentActionExecutionResponse,
    ContentActionPlanResponse,
    ContentActionResponse,
    ExecuteContentActionsRequest,
)
from services.content_action_application_service import (
    ContentActionApplicationService,
    ContentActionNotFoundError,
    ContentActionPolicyError,
)
from services.section_content_generator import ContentGenerationError


router = APIRouter(prefix="/api/v2/quotations", tags=["content-actions"])
CorrelationIdHeader = Annotated[str, Header(alias="X-Correlation-ID", min_length=1)]
IdempotencyKeyHeader = Annotated[str, Header(alias="Idempotency-Key", min_length=1)]


def _serialize_action(action: Any) -> ContentActionResponse:
    return ContentActionResponse(
        id=action.id,
        scope=action.scope,
        entityKey=action.entity_key,
        reasonCode=action.reason_code,
        automationPolicy=action.automation_policy,
        state=action.state,
        inheritedReferenceStatus=action.inherited_reference_status,
        draftId=action.draft_id,
        appliedDocumentRevision=action.applied_document_revision,
        metadata=action.action_metadata_json or {},
    )


def _serialize_plan(plan: Any, actions: list[Any]) -> ContentActionPlanResponse:
    return ContentActionPlanResponse(
        id=plan.id,
        quotationId=plan.quotation_id,
        predecessorQuotationId=plan.predecessor_quotation_id,
        factsHash=plan.facts_hash,
        status=plan.status,
        acceptanceNote=plan.acceptance_note,
        actions=[_serialize_action(action) for action in actions],
    )


def _raise_domain_error(error: Exception) -> None:
    if isinstance(error, ContentActionNotFoundError):
        raise HTTPException(status_code=404, detail={"code": "content_action_not_found", "message": str(error)}) from error
    if isinstance(error, ContentActionPolicyError):
        raise HTTPException(status_code=409, detail={"code": "content_action_policy_conflict", "message": str(error)}) from error
    if isinstance(error, DocumentRevisionConflictError):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "document_revision_conflict",
                "expectedRevision": error.expected_revision,
                "currentRevision": error.current_revision,
            },
        ) from error
    if isinstance(error, ContentGenerationError):
        raise HTTPException(status_code=503, detail={"code": "content_generation_unavailable", "message": str(error), "retryable": True}) from error
    if isinstance(error, ValueError):
        raise HTTPException(status_code=422, detail={"code": "content_action_validation", "message": str(error)}) from error
    raise error


@router.get("/{quotation_id}/content-actions", response_model=ContentActionPlanResponse)
async def get_content_action_plan(
    quotation_id: str,
    _owned: OwnedV2QuotationDep,
    session: DbSessionDep,
) -> ContentActionPlanResponse:
    try:
        plan, actions = await ContentActionApplicationService(session).list(quotation_id)
        return _serialize_plan(plan, actions)
    except Exception as error:
        _raise_domain_error(error)


@router.post("/{quotation_id}/content-actions/accept", response_model=ContentActionPlanResponse)
async def accept_content_action_plan(
    quotation_id: str,
    payload: AcceptContentActionPlanRequest,
    principal: EditorPrincipalDep,
    _owned: OwnedV2QuotationDep,
    session: DbSessionDep,
    correlation_id: CorrelationIdHeader,
) -> ContentActionPlanResponse:
    try:
        plan, actions = await ContentActionApplicationService(session).accept(
            quotation_id=quotation_id,
            note=payload.note,
            profile_id=principal.person_id,
            correlation_id=correlation_id,
        )
        return _serialize_plan(plan, actions)
    except Exception as error:
        _raise_domain_error(error)


@router.post("/{quotation_id}/content-actions/generate-drafts", response_model=ContentActionExecutionResponse)
async def generate_content_action_drafts(
    quotation_id: str,
    payload: ExecuteContentActionsRequest,
    principal: EditorPrincipalDep,
    _owned: OwnedV2QuotationDep,
    session: DbSessionDep,
    correlation_id: CorrelationIdHeader,
) -> ContentActionExecutionResponse:
    try:
        drafts, revision = await ContentActionApplicationService(session).generate_drafts(
            quotation_id=quotation_id,
            plan_id=payload.planId,
            action_ids=payload.actionIds,
            writing_style=payload.writingStyle,
            profile_id=principal.person_id,
            correlation_id=correlation_id,
        )
        return ContentActionExecutionResponse(planId=payload.planId, actionIds=payload.actionIds, draftIds=[draft.id for draft in drafts], documentRevision=revision, mode="auto")
    except Exception as error:
        _raise_domain_error(error)


@router.post("/{quotation_id}/content-actions/generate-and-apply", response_model=ContentActionExecutionResponse)
async def generate_and_apply_content_actions(
    quotation_id: str,
    payload: BypassContentActionsRequest,
    principal: EditorPrincipalDep,
    _owned: OwnedV2QuotationDep,
    session: DbSessionDep,
    idempotency_key: IdempotencyKeyHeader,
    correlation_id: CorrelationIdHeader,
) -> ContentActionExecutionResponse:
    try:
        drafts, revision = await ContentActionApplicationService(session).generate_and_apply(
            quotation_id=quotation_id,
            plan_id=payload.planId,
            action_ids=payload.actionIds,
            expected_revision=payload.expectedRevision,
            writing_style=payload.writingStyle,
            profile_id=principal.person_id,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
        )
        return ContentActionExecutionResponse(planId=payload.planId, actionIds=payload.actionIds, draftIds=[draft.id for draft in drafts], documentRevision=revision, mode="bypass")
    except Exception as error:
        _raise_domain_error(error)
