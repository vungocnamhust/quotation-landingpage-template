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
from repositories import QuotationDocumentRepository, QuotationRepository, QuotationVersionImpactRepository
from services.outbox_service import OutboxService
from services.quotation_impact_analysis import ImpactAnalysisService
from services.skeleton_builder import SkeletonBuilder


router = APIRouter(prefix="/api/v2/quotations", tags=["quotation-versions"])
EditorPrincipalDep = Annotated[Principal, Depends(require_editor)]


class CreateQuotationVersionRequest(BaseModel):
    facts: dict[str, Any]
    baseRevision: int = Field(ge=1)


class ResolveImpactRequest(BaseModel):
    resolutionNote: str = Field(min_length=1, max_length=1000)


def _helpers() -> Any:
    # Transitional adapter for established V2 canonicalization.
    import main
    return main


def _serialize_impact(item: Any) -> dict[str, Any]:
    return {"id": item.id, "stage": item.stage, "scope": item.scope, "action": item.action, "sourcePath": item.source_path, "targetPath": item.target_path, "explanation": item.explanation, "status": item.status, "resolutionNote": item.resolution_note, "resolvedAt": item.resolved_at.isoformat() if item.resolved_at else None}


@router.post("/{quotation_id}/versions")
async def create_quotation_business_version(quotation_id: str, payload: CreateQuotationVersionRequest, principal: EditorPrincipalDep) -> dict[str, Any]:
    h = _helpers()
    await h.require_owned_quotation(quotation_id, principal)
    canonical, resolved = await h._resolve_v2_facts(CreateQuoteRequestV1.model_validate(h.normalize_legacy_facts_snapshot(payload.facts)))
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
        rebuilt = SkeletonBuilder().build(quotation_id=next_id, payload=canonical, resolved_facts=resolved, template=predecessor.template_name)
        h._preserve_content_owned_values(current.document_json, rebuilt)
        rebuilt["presentation"] = copy.deepcopy(current.document_json.get("presentation") or {})
        if "viewOverrides" in current.document_json:
            rebuilt["viewOverrides"] = copy.deepcopy(current.document_json["viewOverrides"])
        await h._apply_missing_media_defaults(
            session,
            rebuilt,
            next_id,
            predecessor.baseline_lang,
            predecessor.brand_id,
        )
        successor = await quotes.create_quotation(quotation_id=next_id, opportunity_id=predecessor.opportunity_id, brand_id=predecessor.brand_id, template_name=predecessor.template_name, baseline_lang=predecessor.baseline_lang, customer_name=canonical.customer_facts.customer_name, title=rebuilt.get("trip", {}).get("title") or predecessor.title, status="draft", source_kind=predecessor.source_kind, source_snapshot_at=predecessor.source_snapshot_at, designer_profile_id=predecessor.designer_profile_id, created_by_profile_id=predecessor.created_by_profile_id, quotation_family_id=predecessor.quotation_family_id, business_version=next_business_version, parent_quotation_id=predecessor.id, source_request_id=predecessor.source_request_id, source_request_revision=predecessor.source_request_revision)
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
    return {"quotationId": next_id, "businessVersion": next_business_version, "redirectUrl": f"/workspace/quotations/{next_id}/edit?stage=content&lang={successor.baseline_lang}", "impacts": [_serialize_impact(row) for row in impact_rows]}


@router.get("/{quotation_id}/impacts")
async def list_quotation_impacts(quotation_id: str, principal: EditorPrincipalDep) -> dict[str, Any]:
    h = _helpers()
    await h.require_owned_quotation(quotation_id, principal)
    async with h._get_db_session_factory()() as session:
        items = await QuotationVersionImpactRepository(session).list(quotation_id)
    return {"items": [_serialize_impact(item) for item in items]}


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
