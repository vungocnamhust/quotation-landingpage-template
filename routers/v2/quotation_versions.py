"""Immutable business-version and Impact Analysis endpoints for V2 quotations."""
from __future__ import annotations

import copy
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import DbSessionDep, OwnedV2QuotationDep, V2_RENDERER_NAME
from core.auth import Principal, require_editor
from quote_document import CreateQuoteRequestV1
from repositories import BrandRepository, ContentDraftRepository, QuotationDocumentRepository, QuotationRepository, QuotationVersionImpactRepository
from services.outbox_service import OutboxService
from services.content_draft_service import ContentDraftService, ContentGenerationError
from services.quotation_impact_analysis import ImpactAnalysisService
from services.skeleton_builder import SkeletonBuilder
from services.quotation_version_application_service import (
    LegacyQuotationVersionError,
    QuotationVersionApplicationService,
    TemplateChangeUnsupportedError,
)


router = APIRouter(prefix="/api/v2/quotations", tags=["quotation-versions"])
EditorPrincipalDep = Annotated[Principal, Depends(require_editor)]


class CreateQuotationVersionRequest(BaseModel):
    facts: CreateQuoteRequestV1
    baseRevision: int = Field(ge=1)


class ResolveImpactRequest(BaseModel):
    resolutionNote: str = Field(min_length=1, max_length=1000)


class AcceptImpactCenterRequest(BaseModel):
    selectedTargetIds: list[int] = Field(default_factory=list)
    resolutionNote: str = Field(default="Accepted in Impact Center.", min_length=1, max_length=1000)


class ImpactTargetResponse(BaseModel):
    id: int
    scope: str
    targetPath: str
    treatment: str
    affectedFields: list[dict[str, Any]]
    generationEligible: bool
    generationSelected: bool
    executionStatus: str
    deepLink: dict[str, Any]


class ContentImpactResponse(BaseModel):
    id: int
    entityKey: str
    operation: str
    sourcePath: str
    explanation: str
    status: str
    oldValue: dict[str, Any] | None = None
    newValue: dict[str, Any] | None = None
    targets: list[ImpactTargetResponse] = Field(default_factory=list)


class ContentImpactPlanResponse(BaseModel):
    items: list[ContentImpactResponse]


class AcceptImpactCenterResponse(BaseModel):
    items: list[ContentImpactResponse]
    factsUrl: str
    contentUrl: str


def _copy_successor_owned_values(previous: dict[str, Any], rebuilt: dict[str, Any]) -> None:
    """Carry user-owned values only when the immutable Fact day identity matches."""
    old_days = ((previous.get("itinerary") or {}).get("days") or [])
    new_days = ((rebuilt.get("itinerary") or {}).get("days") or [])
    old_by_fact_id = {str(day.get("sourceFactId")): day for day in old_days if day.get("sourceFactId")}
    for day in new_days:
        old = old_by_fact_id.get(str(day.get("sourceFactId")))
        if old is None:
            continue
        # A fact identity can remain while the destination changes. Never carry
        # editorial/media ownership across that semantic boundary.
        if any(old.get(key) != day.get(key) for key in ("destinationRef", "segmentCity", "overnight", "dayDate")):
            continue
        for key in ("title", "description", "activities", "labelHighlights", "labelNotes"):
            day[key] = copy.deepcopy(old.get(key, day[key]))
    presentation = copy.deepcopy(previous.get("presentation") or {})
    old_overrides = presentation.get("mediaOverrides") or {}
    old_index_by_fact = {str(day.get("sourceFactId")): index for index, day in enumerate(old_days) if day.get("sourceFactId")}
    new_overrides: dict[str, Any] = {}
    for new_index, day in enumerate(new_days):
        old_index = old_index_by_fact.get(str(day.get("sourceFactId")))
        if old_index is None:
            continue
        old = old_days[old_index]
        if any(old.get(key) != day.get(key) for key in ("destinationRef", "segmentCity", "overnight", "dayDate")):
            continue
        prefix = f"itinerary.days.{old_index}."
        for key, value in old_overrides.items():
            if key.startswith(prefix):
                new_overrides[f"itinerary.days.{new_index}.{key[len(prefix):]}"] = copy.deepcopy(value)
    if new_overrides:
        presentation["mediaOverrides"] = new_overrides
    else:
        presentation.pop("mediaOverrides", None)
    rebuilt["presentation"] = {**rebuilt.get("presentation", {}), **presentation}


def _helpers() -> Any:
    # Transitional adapter for established V2 canonicalization.
    import main
    return main


def _ensure_itinerary_fact_ids(facts: CreateQuoteRequestV1) -> None:
    """Canonicalize old V2 payloads before their immutable successor snapshot."""
    for index, day in enumerate(facts.trip_facts.itinerary, 1):
        if not day.id:
            day.id = f"day_{uuid.uuid5(uuid.NAMESPACE_URL, f'{facts.opportunity_id}:{index}:{day.display_date}:{day.destination_ref or day.destination}').hex}"


def _serialize_impact(item: Any, targets: list[Any] | None = None) -> dict[str, Any]:
    return {"id": item.id, "entityKey": item.entity_key, "operation": item.operation, "sourcePath": item.source_path, "explanation": item.explanation, "status": item.status, "oldValue": item.old_value_json, "newValue": item.new_value_json, "targets": [{"id": target.id, "scope": target.scope, "targetPath": target.target_path, "treatment": target.treatment, "affectedFields": target.affected_fields_json, "generationEligible": target.generation_eligible, "generationSelected": target.generation_selected, "executionStatus": target.execution_status, "deepLink": target.deep_link_json} for target in (targets or [])]}


def _clear_incompatible_day_carry_forward(
    *,
    previous_facts: dict[str, Any],
    current_facts: dict[str, Any],
    document: dict[str, Any],
) -> None:
    old_days = {str(day.get("day_number") or index + 1): day for index, day in enumerate((previous_facts.get("trip_facts") or {}).get("itinerary") or []) if isinstance(day, dict)}
    new_days = {str(day.get("day_number") or index + 1): day for index, day in enumerate((current_facts.get("trip_facts") or {}).get("itinerary") or []) if isinstance(day, dict)}
    changed = {
        number for number, new_day in new_days.items()
        if number not in old_days or tuple(old_days[number].get(key) for key in ("destination_ref", "destination", "overnight", "display_date")) != tuple(new_day.get(key) for key in ("destination_ref", "destination", "overnight", "display_date"))
    }
    for day in ((document.get("itinerary") or {}).get("days") or []):
        if str(day.get("dayNumber")) not in changed:
            continue
        for key in ("title", "description", "activities", "labelHighlights", "labelNotes"):
            day[key] = [] if key in {"description", "activities"} else ""
    presentation = document.get("presentation") or {}
    overrides = presentation.get("mediaOverrides") or {}
    for number in changed:
        prefix = f"itinerary.days.{int(number) - 1}."
        for key in list(overrides):
            if key.startswith(prefix):
                overrides.pop(key)
    presentation["mediaOverrides"] = overrides
    document["presentation"] = presentation


@router.post("/{quotation_id}/versions")
async def create_quotation_business_version(
    quotation_id: str,
    payload: CreateQuotationVersionRequest,
    principal: EditorPrincipalDep,
    _owned: OwnedV2QuotationDep,
    session: DbSessionDep,
) -> dict[str, Any]:
    try:
        successor, actions = await QuotationVersionApplicationService(session).create_successor(
            predecessor_id=quotation_id,
            facts=payload.facts,
            base_revision=payload.baseRevision,
            profile_id=principal.person_id,
            correlation_id=f"quotation-family:{quotation_id}:{uuid.uuid4().hex}",
        )
    except LegacyQuotationVersionError as error:
        raise HTTPException(status_code=409, detail={"message": str(error), "code": "legacy_quotation"}) from error
    except TemplateChangeUnsupportedError as error:
        raise HTTPException(status_code=422, detail={"message": str(error), "code": "template_change_unsupported"}) from error
    except DocumentRevisionConflictError as error:
        raise HTTPException(status_code=409, detail={"message": "Document revision conflict.", "currentRevision": error.current_revision}) from error
    except LookupError as error:
        raise HTTPException(status_code=404, detail={"message": str(error)}) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"message": str(error)}) from error
    return {
        "quotationId": successor.id,
        "businessVersion": successor.business_version,
        "redirectUrl": f"/workspace/quotations/{successor.id}/edit?stage=impact&lang={successor.baseline_lang}",
        "contentActionIds": [action.id for action in actions],
    }


@router.get("/{quotation_id}/impacts", response_model=ContentImpactPlanResponse)
async def list_quotation_impacts(quotation_id: str, principal: EditorPrincipalDep) -> ContentImpactPlanResponse:
    h = _helpers()
    await h.require_owned_quotation(quotation_id, principal)
    async with h._get_db_session_factory()() as session:
        impacts = QuotationVersionImpactRepository(session)
        items = await impacts.list(quotation_id)
        targets_by_impact: dict[int, list[Any]] = {}
        for target in await impacts.list_targets(quotation_id):
            targets_by_impact.setdefault(target.impact_id, []).append(target)
    return ContentImpactPlanResponse(items=[ContentImpactResponse.model_validate(_serialize_impact(item, targets_by_impact.get(item.id))) for item in items])


@router.post("/{quotation_id}/impacts/{impact_id}/resolve")
async def resolve_quotation_impact(quotation_id: str, impact_id: int, payload: ResolveImpactRequest, principal: EditorPrincipalDep) -> dict[str, Any]:
    h = _helpers()
    await h.require_owned_quotation(quotation_id, principal)
    async with h._get_db_session_factory()() as session:
        item = await QuotationVersionImpactRepository(session).resolve(quotation_id, impact_id, note=payload.resolutionNote, profile_id=None)
        if item is None:
            raise HTTPException(status_code=404, detail="Impact was not found.")
        await session.commit()
    return {"item": _serialize_impact(item)}


@router.post("/{quotation_id}/impacts/accept", response_model=AcceptImpactCenterResponse)
async def accept_quotation_impact_center(quotation_id: str, payload: AcceptImpactCenterRequest, principal: EditorPrincipalDep, idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None, correlation_id: Annotated[str | None, Header(alias="X-Correlation-ID")] = None) -> AcceptImpactCenterResponse:
    h = _helpers()
    await h.require_owned_quotation(quotation_id, principal)
    async with h._get_db_session_factory()() as session:
        quotation = await QuotationRepository(session).get_quotation_by_id(quotation_id)
        if quotation is None or quotation.quotation_family_id is None:
            raise HTTPException(status_code=409, detail={"message": "Impact Center is available only for new-model quotation versions."})
        impacts = QuotationVersionImpactRepository(session)
        pending = await impacts.list(quotation_id, pending_only=True)
        targets = await impacts.list_targets(quotation_id)
        valid_ids = {item.id for item in targets if item.generation_eligible and item.impact_id in {row.id for row in pending}}
        selected_ids = set(payload.selectedTargetIds)
        if not selected_ids.issubset(valid_ids):
            raise HTTPException(status_code=422, detail={"message": "Only pending generation candidates can be selected."})
        profile_id = getattr(principal, "profile_id", None)
        idempotency_key = idempotency_key or f"impact-accept:{quotation_id}:{uuid.uuid4().hex}"
        correlation_id = correlation_id or f"impact-center:{quotation_id}:v{quotation.business_version or 0}"
        previous_acceptance = await impacts.get_acceptance(quotation_id, idempotency_key)
        if previous_acceptance is not None and (
            set(previous_acceptance.selected_target_ids_json) != selected_ids
            or previous_acceptance.resolution_note != payload.resolutionNote
        ):
            raise HTTPException(status_code=409, detail={"message": "Idempotency key was already used with a different Impact Center acceptance.", "code": "impact_acceptance_idempotency_conflict"})
        try:
            accepted = await impacts.accept_all(quotation_id, selected_target_ids=selected_ids, note=payload.resolutionNote, profile_id=profile_id, idempotency_key=idempotency_key, correlation_id=correlation_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail={"message": str(exc), "code": "impact_acceptance_idempotency_conflict"}) from exc
        if previous_acceptance is None:
            await OutboxService(session).emit_event(
                event_type="quotation.impact.accepted",
                aggregate_type="quotation",
                aggregate_id=quotation_id,
                brand_id=quotation.brand_id,
                correlation_id=correlation_id,
                payload={"quotation_family_id": quotation.quotation_family_id, "business_version": quotation.business_version, "selected_target_ids": sorted(selected_ids), "actor_profile_id": profile_id, "idempotency_key": idempotency_key},
            )
        await session.commit()
        targets_by_impact = {}
        for target in await impacts.list_targets(quotation_id):
            targets_by_impact.setdefault(target.impact_id, []).append(target)
    base = f"/workspace/quotations/{quotation_id}/edit?lang={quotation.baseline_lang}"
    return AcceptImpactCenterResponse(items=[ContentImpactResponse.model_validate(_serialize_impact(item, targets_by_impact.get(item.id))) for item in accepted], factsUrl=f"{base}&stage=facts", contentUrl=f"{base}&stage=content")


@router.post("/{quotation_id}/impacts/generate-selected")
async def generate_selected_quotation_impacts(quotation_id: str, principal: EditorPrincipalDep) -> None:
    """Compatibility endpoint: Impact Center never executes content automatically."""
    h = _helpers()
    await h.require_owned_quotation(quotation_id, principal)
    raise HTTPException(status_code=409, detail={"message": "Impact execution was retired. Generate reviewed drafts in Content Studio.", "code": "impact_execution_retired"})
