"""Immutable business-version and Impact Analysis endpoints for V2 quotations."""
from __future__ import annotations

import copy
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import V2_RENDERER_NAME
from core.auth import Principal, require_editor
from quote_document import CreateQuoteRequestV1
from repositories import BrandRepository, ContentDraftRepository, QuotationDocumentRepository, QuotationRepository, QuotationVersionImpactRepository
from services.outbox_service import OutboxService
from services.content_draft_service import ContentDraftService, ContentGenerationError
from services.quotation_impact_analysis import ImpactAnalysisService
from services.skeleton_builder import SkeletonBuilder


router = APIRouter(prefix="/api/v2/quotations", tags=["quotation-versions"])
EditorPrincipalDep = Annotated[Principal, Depends(require_editor)]


class CreateQuotationVersionRequest(BaseModel):
    facts: dict[str, Any]
    baseRevision: int = Field(ge=1)


class ResolveImpactRequest(BaseModel):
    resolutionNote: str = Field(min_length=1, max_length=1000)


class AcceptImpactCenterRequest(BaseModel):
    selectedImpactIds: list[int] = Field(default_factory=list)
    resolutionNote: str = Field(default="Accepted in Impact Center.", min_length=1, max_length=1000)


class GenerateSelectedImpactsRequest(BaseModel):
    generationMode: str = Field(default="storytelling", pattern="^(storytelling|detailed)$")
    instruction: str = Field(default="", max_length=2000)


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
    return {"id": item.id, "stage": item.stage, "scope": item.scope, "action": item.action, "sourcePath": item.source_path, "targetPath": item.target_path, "explanation": item.explanation, "status": item.status, "entityKey": item.entity_key, "operation": item.operation, "oldValue": item.old_value_json, "newValue": item.new_value_json, "generationEligible": item.generation_eligible, "generationSelected": item.generation_selected, "generationStatus": item.generation_status, "resolutionNote": item.resolution_note, "resolvedAt": item.resolved_at.isoformat() if item.resolved_at else None, "targets": [{"id": target.id, "stage": target.stage, "scope": target.scope, "targetPath": target.target_path, "treatment": target.treatment, "affectedFields": target.affected_fields_json, "generationEligible": target.generation_eligible, "generationSelected": target.generation_selected, "executionStatus": target.execution_status} for target in (targets or [])]}


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
async def create_quotation_business_version(quotation_id: str, payload: CreateQuotationVersionRequest, principal: EditorPrincipalDep) -> dict[str, Any]:
    h = _helpers()
    await h.require_owned_quotation(quotation_id, principal)
    canonical, resolved = await h._resolve_v2_facts(CreateQuoteRequestV1.model_validate(h.normalize_legacy_facts_snapshot(payload.facts)))
    _ensure_itinerary_fact_ids(canonical)
    if resolved["missingInputs"]:
        raise HTTPException(status_code=422, detail={"message": "Required quotation facts are missing.", "missingInputs": resolved["missingInputs"]})
    async with h._get_db_session_factory()() as session:
        quotes, documents = QuotationRepository(session), QuotationDocumentRepository(session)
        predecessor = await quotes.get_quotation_by_id(quotation_id)
        if predecessor is None or predecessor.template_name != V2_RENDERER_NAME:
            raise HTTPException(status_code=404, detail="Quotation was not found.")
        if predecessor.quotation_family_id is None:
            raise HTTPException(status_code=409, detail={"message": "Legacy quotations cannot create business versions.", "code": "legacy_quotation"})
        current, previous_facts = await documents.get_current_document(quotation_id, predecessor.baseline_lang), await quotes.get_version_facts(quotation_id)
        if current is None or previous_facts is None:
            raise HTTPException(status_code=409, detail={"message": "The immutable predecessor snapshot is unavailable."})
        if current.revision != payload.baseRevision:
            raise HTTPException(status_code=409, detail={"message": "Document revision conflict.", "currentRevision": current.revision})
        next_id = f"quo_{uuid.uuid4().hex[:12]}"
        next_business_version = await quotes.next_business_version(predecessor.quotation_family_id)
        predecessor_template_id = str((current.document_json.get("presentation") or {}).get("templateId") or "")
        requested_template_id = canonical.presentation_options.template_id or predecessor_template_id
        if requested_template_id != predecessor_template_id:
            raise HTTPException(status_code=422, detail={"message": "Template cannot be changed until a V2 template registry is available.", "code": "template_change_unsupported"})
        successor_brand_id = canonical.brand_id or predecessor.brand_id
        successor_lang = canonical.lang or predecessor.baseline_lang
        rebuilt = SkeletonBuilder().build(quotation_id=next_id, payload=canonical, resolved_facts=resolved, template=predecessor.template_name)
        _copy_successor_owned_values(current.document_json, rebuilt)
        rebuilt["presentation"]["templateId"] = canonical.presentation_options.template_id or ""
        if "viewOverrides" in current.document_json:
            rebuilt["viewOverrides"] = copy.deepcopy(current.document_json["viewOverrides"])
        await h._apply_missing_media_defaults(
            session,
            rebuilt,
            next_id,
            successor_lang,
            successor_brand_id,
        )
        successor = await quotes.create_quotation(quotation_id=next_id, opportunity_id=predecessor.opportunity_id, brand_id=successor_brand_id, template_name=predecessor.template_name, baseline_lang=successor_lang, customer_name=canonical.customer_facts.customer_name, title=rebuilt.get("trip", {}).get("title") or predecessor.title, status="draft", source_kind=predecessor.source_kind, source_snapshot_at=predecessor.source_snapshot_at, designer_profile_id=predecessor.designer_profile_id, created_by_profile_id=predecessor.created_by_profile_id, quotation_family_id=predecessor.quotation_family_id, business_version=next_business_version, parent_quotation_id=predecessor.id, source_request_id=predecessor.source_request_id, source_request_revision=predecessor.source_request_revision)
        await quotes.create_quotation_request(quotation_id=next_id, request_json=canonical.model_dump(mode="json"))
        await quotes.create_version_facts(quotation_id=next_id, canonical_facts_json=canonical.model_dump(mode="json"), resolved_facts_json=resolved, facts_hash=resolved["factsHash"], source_request_id=predecessor.source_request_id, source_request_revision=predecessor.source_request_revision)
        validated = h._normalize_quote_document_structure_or_422(h._hydrate_canonical_quote_document(rebuilt, successor, lang=successor.baseline_lang, revision=1))
        saved = await documents.save_current_document(quotation_id=next_id, lang=successor.baseline_lang, document_json=validated, expected_revision=0)
        canonical_document = h._hydrate_canonical_quote_document(saved.document_json, successor, lang=successor.baseline_lang, revision=saved.revision)
        await documents.append_document_revision(quotation_id=next_id, lang=successor.baseline_lang, revision=saved.revision, document_json=canonical_document, change_source="create_business_version")
        impacts = ImpactAnalysisService.analyze(previous_facts.canonical_facts_json, canonical.model_dump(mode="json"))
        impact_rows = await QuotationVersionImpactRepository(session).create_many(next_id, impacts)
        outbox = OutboxService(session)
        correlation_id = f"quotation-family:{successor.quotation_family_id}"
        await outbox.emit_event(event_type="quotation.version.created", aggregate_type="quotation", aggregate_id=next_id, brand_id=successor.brand_id, correlation_id=correlation_id, payload={"quotation_family_id": successor.quotation_family_id, "business_version": successor.business_version, "parent_quotation_id": predecessor.id, "source_request_id": successor.source_request_id, "source_request_revision": successor.source_request_revision})
        if impact_rows:
            await outbox.emit_event(event_type="quotation.impact.created", aggregate_type="quotation", aggregate_id=next_id, brand_id=successor.brand_id, correlation_id=correlation_id, payload={"quotation_family_id": successor.quotation_family_id, "business_version": successor.business_version, "content_count": sum(row.stage == "content" for row in impact_rows), "design_count": sum(row.stage == "design" for row in impact_rows)})
        await session.commit()
    return {"quotationId": next_id, "businessVersion": next_business_version, "redirectUrl": f"/workspace/quotations/{next_id}/edit?stage=impact&lang={successor.baseline_lang}", "impacts": [_serialize_impact(row) for row in impact_rows]}


@router.get("/{quotation_id}/impacts")
async def list_quotation_impacts(quotation_id: str, principal: EditorPrincipalDep) -> dict[str, Any]:
    h = _helpers()
    await h.require_owned_quotation(quotation_id, principal)
    async with h._get_db_session_factory()() as session:
        impacts = QuotationVersionImpactRepository(session)
        items = await impacts.list(quotation_id)
        targets_by_impact: dict[int, list[Any]] = {}
        for target in await impacts.list_targets(quotation_id):
            targets_by_impact.setdefault(target.impact_id, []).append(target)
    return {"items": [_serialize_impact(item, targets_by_impact.get(item.id)) for item in items]}


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


@router.post("/{quotation_id}/impacts/accept")
async def accept_quotation_impact_center(quotation_id: str, payload: AcceptImpactCenterRequest, principal: EditorPrincipalDep) -> dict[str, Any]:
    h = _helpers()
    await h.require_owned_quotation(quotation_id, principal)
    async with h._get_db_session_factory()() as session:
        quotation = await QuotationRepository(session).get_quotation_by_id(quotation_id)
        if quotation is None or quotation.quotation_family_id is None:
            raise HTTPException(status_code=409, detail={"message": "Impact Center is available only for new-model quotation versions."})
        impacts = QuotationVersionImpactRepository(session)
        pending = await impacts.list(quotation_id, pending_only=True)
        valid_ids = {item.id for item in pending if item.generation_eligible}
        selected_ids = set(payload.selectedImpactIds)
        if not selected_ids.issubset(valid_ids):
            raise HTTPException(status_code=422, detail={"message": "Only pending generation candidates can be selected."})
        profile_id = getattr(principal, "profile_id", None)
        accepted = await impacts.accept_all(quotation_id, selected_impact_ids=selected_ids, note=payload.resolutionNote, profile_id=profile_id)
        correlation_id = f"impact-center:{quotation_id}:v{quotation.business_version or 0}"
        await OutboxService(session).emit_event(
            event_type="quotation.impact.accepted",
            aggregate_type="quotation",
            aggregate_id=quotation_id,
            brand_id=quotation.brand_id,
            correlation_id=correlation_id,
            payload={"quotation_family_id": quotation.quotation_family_id, "business_version": quotation.business_version, "selected_impact_ids": sorted(selected_ids), "actor_profile_id": profile_id},
        )
        await session.commit()
    base = f"/workspace/quotations/{quotation_id}/edit?lang={quotation.baseline_lang}"
    return {"items": [_serialize_impact(item) for item in accepted], "factsUrl": f"{base}&stage=facts", "designUrl": f"{base}&stage=design"}


@router.post("/{quotation_id}/impacts/generate-selected")
async def generate_selected_quotation_impacts(quotation_id: str, payload: GenerateSelectedImpactsRequest, principal: EditorPrincipalDep) -> dict[str, Any]:
    h = _helpers()
    await h.require_owned_quotation(quotation_id, principal)
    async with h._get_db_session_factory()() as session:
        quotes, documents, impacts_repo = QuotationRepository(session), QuotationDocumentRepository(session), QuotationVersionImpactRepository(session)
        quotation = await quotes.get_quotation_by_id(quotation_id)
        facts_snapshot = await quotes.get_version_facts(quotation_id)
        document = await documents.get_current_document(quotation_id, quotation.baseline_lang) if quotation else None
        if quotation is None or quotation.quotation_family_id is None or facts_snapshot is None or document is None:
            raise HTTPException(status_code=409, detail={"message": "The immutable version context is unavailable."})
        selected = await impacts_repo.selected_for_generation(quotation_id)
        content_impacts = [item for item in selected if item.stage == "content"]
        design_impacts = [item for item in selected if item.stage == "design"]
        if not selected:
            return {"drafts": [], "count": 0, "revision": document.revision, "appliedScopes": []}
        facts = CreateQuoteRequestV1.model_validate(facts_snapshot.canonical_facts_json)
        brand = await BrandRepository(session).get_active(quotation.brand_id)
        if brand is None:
            raise HTTPException(status_code=422, detail={"message": "Brand is unavailable for selected generation."})
        drafts = ContentDraftRepository(session)
        service = ContentDraftService(drafts, h._brand_generation_profile(brand))
        created: list[Any] = []
        try:
            generated_scopes: set[str] = set()
            for impact in content_impacts:
                if impact.scope in generated_scopes:
                    continue
                generated_scopes.add(impact.scope)
                created.extend(await service.create(quotation_id=quotation_id, payload=facts, facts_hash=facts_snapshot.facts_hash, document_revision=document.revision, lang=quotation.baseline_lang, scope=impact.scope, mode=payload.generationMode, instruction=payload.instruction))
            merged = copy.deepcopy(document.document_json)
            applied_scopes: list[str] = []
            # This endpoint is intentionally Design-only.  Facts never call it:
            # their Content drafts are user-triggered from Content Studio.
            for draft in created:
                if draft.missing_inputs:
                    raise ValueError(f"Selected scope {draft.scope} is missing required Facts.")
                merged = ContentDraftService.apply_candidate(merged, draft.scope, draft.candidate_json)
                draft.status = "applied"
                applied_scopes.append(draft.scope)
            if applied_scopes:
                validated = h._normalize_quote_document_structure_or_422(
                    h._hydrate_canonical_quote_document(merged, quotation, lang=quotation.baseline_lang, revision=document.revision + 1)
                )
                saved = await documents.save_current_document(
                    quotation_id=quotation_id,
                    lang=quotation.baseline_lang,
                    document_json=validated,
                    expected_revision=document.revision,
                )
                await documents.append_document_revision(
                    quotation_id=quotation_id,
                    lang=quotation.baseline_lang,
                    revision=saved.revision,
                    document_json=saved.document_json,
                    change_source="impact_center_design_apply",
                )
            else:
                saved = document
            await impacts_repo.mark_generation_status(content_impacts + design_impacts, status="auto_applied")
            await OutboxService(session).emit_event(
                event_type="quotation.impact.auto_applied",
                aggregate_type="quotation",
                aggregate_id=quotation_id,
                brand_id=quotation.brand_id,
                correlation_id=f"impact-center:{quotation_id}:design",
                payload={"quotation_family_id": quotation.quotation_family_id, "business_version": quotation.business_version, "selected_impact_ids": [item.id for item in selected], "applied_scopes": applied_scopes, "document_revision": saved.revision},
            )
            await session.commit()
        except ContentGenerationError as exc:
            await session.rollback()
            raise HTTPException(status_code=503, detail={"message": str(exc), "retryable": True}) from exc
        except ValueError as exc:
            await session.rollback()
            raise HTTPException(status_code=422, detail={"message": str(exc)}) from exc
    return {"drafts": [h._serialize_content_draft(item) for item in created], "count": len(created), "revision": saved.revision, "appliedScopes": applied_scopes}
