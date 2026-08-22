"""Quotation V2 facts endpoints."""
from __future__ import annotations

import copy
from datetime import datetime
from typing import Annotated, Any, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import V2_RENDERER_NAME
from core.auth import Principal, require_editor
from quote_document import CreateQuoteRequestV1
from repositories import (
    ContentDraftRepository,
    QuotationDocumentRepository,
    QuotationRepository,
)
from repositories.travel_designer_repository import TravelDesignerRepository
from repositories.errors import DocumentRevisionConflictError
from schemas.brand_contract import _require_active_v2_brand
from services.skeleton_builder import SkeletonBuilder


router = APIRouter(prefix="/api/v2/quotations", tags=["quotation-facts"])


class FactsMediaRequest(BaseModel):
    baseRevision: int
    slots: list[dict[str, Any]] = Field(default_factory=list)


class FactsDesignerRequest(BaseModel):
    baseRevision: int
    designerProfileId: str


class PresentationMediaDefaultsRequest(BaseModel):
    baseRevision: int
    dryRun: bool = True


def _get_helpers():
    import main
    return main


@router.get("/{quotation_id}/facts")
async def get_quotation_facts_v2(
    quotation_id: str,
    principal: Principal = Depends(require_editor),
):
    h = _get_helpers()
    await h.require_owned_quotation(quotation_id, principal)
    async with h._get_db_session_factory()() as session:
        quotes, documents = QuotationRepository(session), QuotationDocumentRepository(session)
        quotation = await quotes.get_quotation_by_id(quotation_id)
        request = await quotes.get_latest_quotation_request(quotation_id)
        version_facts = await quotes.get_version_facts(quotation_id)
        if quotation is None or (request is None and version_facts is None):
            raise HTTPException(status_code=404, detail="Quotation facts were not found.")
        document = await documents.get_current_document(quotation_id, quotation.baseline_lang)
        snapshot = version_facts.canonical_facts_json if version_facts is not None else request.request_json
        payload = CreateQuoteRequestV1.model_validate(h.normalize_legacy_facts_snapshot(snapshot))
        canonical = payload
        resolved = version_facts.resolved_facts_json if version_facts is not None else (await h._resolve_v2_facts(payload))[1]
        if canonical.presentation_options.travel_designer_id is None and quotation.designer_profile_id:
            canonical.presentation_options.travel_designer_id = quotation.designer_profile_id

        request_payload = None
        if quotation.opportunity_id:
            from repositories.quote_request_repository import QuoteRequestRepository
            quote_req = await QuoteRequestRepository(session).get_by_id(quotation.opportunity_id)
            if quote_req and quote_req.payload_json:
                request_payload = quote_req.payload_json
        if not request_payload and request and request.request_json:
            request_payload = request.request_json
        from services.content_draft_service import extract_request_brief
        request_brief = extract_request_brief(request_payload)

        res = h._facts_response(
            quotation=quotation,
            request_json=canonical.model_dump(mode="json"),
            document=(document.document_json if document else {}),
            resolved_facts=resolved,
        )
        if request_brief:
            res["requestBrief"] = request_brief
        if quotation.quotation_family_id:
            res["businessVersion"] = {
                "familyId": quotation.quotation_family_id,
                "number": quotation.business_version,
                "parentQuotationId": quotation.parent_quotation_id,
                "sourceRequestId": quotation.source_request_id,
                "sourceRequestRevision": quotation.source_request_revision,
                "immutable": True,
            }
        return res


@router.put("/{quotation_id}/facts")
async def put_quotation_facts_v2(
    quotation_id: str,
    payload: CreateQuoteRequestV1,
    baseRevision: int,
    principal: Principal = Depends(require_editor),
):
    h = _get_helpers()
    await h.require_owned_quotation(quotation_id, principal)
    canonical, resolved = await h._resolve_v2_facts(payload)
    if resolved["missingInputs"]:
        raise HTTPException(
            status_code=422,
            detail={"message": "Required quotation facts are missing.", "missingInputs": resolved["missingInputs"]},
        )
    async with h._get_db_session_factory()() as session:
        quotes, documents, drafts, designers = (
            QuotationRepository(session),
            QuotationDocumentRepository(session),
            ContentDraftRepository(session),
            TravelDesignerRepository(session),
        )
        quotation = await quotes.get_quotation_by_id(quotation_id)
        if quotation is None:
            raise HTTPException(status_code=404, detail="Quotation was not found.")
        if quotation.quotation_family_id:
            raise HTTPException(status_code=409, detail={"message": "Facts are immutable for a business quotation version. Create an Edit Quotation version.", "code": "immutable_facts", "editQuotationId": quotation_id})
        if quotation.source_kind != "manual":
            raise HTTPException(status_code=403, detail="Facts are read-only for this quotation source.")
        if canonical.brand_id != quotation.brand_id:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "A quotation brand is immutable. Create a publication target to render another brand.",
                    "missingInputs": ["brand_id"],
                },
            )
        current = await documents.get_current_document(quotation_id, quotation.baseline_lang)
        if current is None:
            raise HTTPException(status_code=404, detail="Canonical document was not found.")
        rebuilt = SkeletonBuilder().build(
            quotation_id=quotation_id,
            payload=canonical,
            resolved_facts=resolved,
            template=quotation.template_name,
        )
        h._preserve_content_owned_values(current.document_json, rebuilt)
        if canonical.presentation_options.travel_designer_id:
            profile = await designers.get_profile(canonical.presentation_options.travel_designer_id)
            if profile is None or not profile.is_active:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "message": "Travel Designer is unavailable.",
                        "missingInputs": ["presentation_options.travel_designer_id"],
                    },
                )
            quotation.designer_profile_id = profile.id
            h._apply_travel_designer_snapshot(rebuilt, h._serialize_travel_designer(profile))
        rebuilt["presentation"] = copy.deepcopy((current.document_json.get("presentation") or {}))
        if "viewOverrides" in current.document_json:
            rebuilt["viewOverrides"] = copy.deepcopy(current.document_json["viewOverrides"])
        h._copy_fact_media_slots(current.document_json, rebuilt)
        await h._apply_missing_media_defaults(session, rebuilt, quotation_id, quotation.baseline_lang)
        validated = h._normalize_quote_document_structure_or_422(
            h._hydrate_canonical_quote_document(rebuilt, quotation, lang=quotation.baseline_lang, revision=baseRevision)
        )
        try:
            saved = await documents.save_current_document(
                quotation_id=quotation_id,
                lang=quotation.baseline_lang,
                document_json=validated,
                expected_revision=baseRevision,
            )
        except DocumentRevisionConflictError as exc:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Facts revision conflict.",
                    "currentRevision": exc.current_revision,
                    "currentDocument": exc.current_document,
                },
            ) from exc
        canonical_doc = h._hydrate_canonical_quote_document(saved.document_json, quotation, lang=quotation.baseline_lang, revision=saved.revision)
        await documents.append_document_revision(
            quotation_id=quotation_id,
            lang=quotation.baseline_lang,
            revision=saved.revision,
            document_json=canonical_doc,
            change_source="update_facts",
        )
        await quotes.create_quotation_request(quotation_id=quotation_id, request_json=canonical.model_dump(mode="json"))
        await drafts.mark_stale(quotation_id)
        await session.commit()
        return h._facts_response(
            quotation=quotation,
            request_json=canonical.model_dump(mode="json"),
            document=canonical_doc,
            resolved_facts=resolved,
        )


@router.put("/{quotation_id}/facts/media")
async def put_quotation_fact_media_v2(
    quotation_id: str,
    payload: FactsMediaRequest,
    lang: str | None = None,
    principal: Principal = Depends(require_editor),
):
    h = _get_helpers()
    await h.require_owned_quotation(quotation_id, principal)
    fields = h._validate_v2_fact_media_slots(payload.slots)
    async with h._get_db_session_factory()() as session:
        quotes, documents = QuotationRepository(session), QuotationDocumentRepository(session)
        quotation = await quotes.get_quotation_by_id(quotation_id)
        if quotation is None or quotation.template_name != V2_RENDERER_NAME:
            raise HTTPException(status_code=404, detail="Quotation was not found.")
        if quotation.quotation_family_id:
            raise HTTPException(status_code=409, detail={"message": "Fact media is immutable for a business quotation version. Update it in Design.", "code": "immutable_facts"})
        effective_lang = lang or quotation.baseline_lang
        current = await documents.get_current_document(quotation_id, effective_lang)
        if current is None:
            raise HTTPException(status_code=404, detail="Canonical document was not found.")
        await h._require_active_media_overrides(
            session, {key: value for key, value in fields.items() if value is not None}
        )
        next_document = copy.deepcopy(current.document_json)
        for field_id, value in fields.items():
            h._set_fact_media_field(next_document, field_id, value)
        try:
            validated = h._normalize_quote_document_structure_or_422(
                h._hydrate_canonical_quote_document(next_document, quotation, lang=effective_lang, revision=payload.baseRevision)
            )
            saved = await documents.save_current_document(
                quotation_id=quotation_id,
                lang=effective_lang,
                document_json=validated,
                expected_revision=payload.baseRevision,
            )
        except DocumentRevisionConflictError as exc:
            raise HTTPException(
                status_code=409,
                detail={"message": "Fact media revision conflict.", "currentRevision": exc.current_revision},
            ) from exc
        canonical = h._hydrate_canonical_quote_document(saved.document_json, quotation, lang=effective_lang, revision=saved.revision)
        await documents.append_document_revision(
            quotation_id=quotation_id,
            lang=effective_lang,
            revision=saved.revision,
            document_json=canonical,
            change_source="update_fact_media",
        )
        await session.commit()
    return {"ok": True, "document": canonical, "currentRevision": saved.revision}


@router.put("/{quotation_id}/facts/designer")
async def put_quotation_fact_designer_v2(
    quotation_id: str,
    payload: FactsDesignerRequest,
    lang: str | None = None,
    principal: Principal = Depends(require_editor),
):
    h = _get_helpers()
    await h.require_owned_quotation(quotation_id, principal)
    async with h._get_db_session_factory()() as session:
        quotes, documents, designers = (
            QuotationRepository(session),
            QuotationDocumentRepository(session),
            TravelDesignerRepository(session),
        )
        quotation = await quotes.get_quotation_by_id(quotation_id)
        profile = await designers.get_profile(payload.designerProfileId)
        if quotation is None or quotation.template_name != V2_RENDERER_NAME:
            raise HTTPException(status_code=404, detail="Quotation was not found.")
        if quotation.quotation_family_id:
            raise HTTPException(status_code=409, detail={"message": "Designer Facts are immutable for a business quotation version. Update Design instead.", "code": "immutable_facts"})
        if profile is None or not profile.is_active:
            raise HTTPException(
                status_code=422,
                detail={"message": "Travel Designer is unavailable.", "missingInputs": ["designerProfileId"]},
            )
        effective_lang = lang or quotation.baseline_lang
        current = await documents.get_current_document(quotation_id, effective_lang)
        if current is None:
            raise HTTPException(status_code=404, detail="Canonical document was not found.")
        if current.revision != payload.baseRevision:
            raise HTTPException(
                status_code=409,
                detail={"message": "Designer selection revision conflict.", "currentRevision": current.revision},
            )
        quotation.designer_profile_id = profile.id
        request_snapshot = await quotes.get_latest_quotation_request(quotation_id)
        if request_snapshot is not None:
            next_request = copy.deepcopy(request_snapshot.request_json)
            next_request.setdefault("presentation_options", {})["travel_designer_id"] = profile.id
            await quotes.create_quotation_request(quotation_id=quotation_id, request_json=next_request)
        saved_target = None
        for stored in await documents.list_current_documents(quotation_id):
            next_document = copy.deepcopy(stored.document_json)
            h._apply_travel_designer_snapshot(next_document, h._serialize_travel_designer(profile))
            validated = h._normalize_quote_document_structure_or_422(
                h._hydrate_canonical_quote_document(next_document, quotation, lang=stored.lang, revision=stored.revision)
            )
            saved = await documents.save_current_document(
                quotation_id=quotation_id,
                lang=stored.lang,
                document_json=validated,
                expected_revision=stored.revision,
            )
            canonical = h._hydrate_canonical_quote_document(saved.document_json, quotation, lang=stored.lang, revision=saved.revision)
            await documents.append_document_revision(
                quotation_id=quotation_id,
                lang=stored.lang,
                revision=saved.revision,
                document_json=canonical,
                change_source="update_fact_designer",
            )
            if stored.lang == effective_lang:
                saved_target = (canonical, saved.revision)
        await session.commit()
    assert saved_target is not None
    return {"ok": True, "document": saved_target[0], "currentRevision": saved_target[1]}


@router.post("/{quotation_id}/facts/media-defaults")
async def apply_quotation_media_defaults_v2(
    quotation_id: str,
    payload: PresentationMediaDefaultsRequest,
    lang: str | None = None,
    principal: Principal = Depends(require_editor),
):
    h = _get_helpers()
    await h.require_owned_quotation(quotation_id, principal)
    async with h._get_db_session_factory()() as session:
        quotes, documents = QuotationRepository(session), QuotationDocumentRepository(session)
        quotation = await quotes.get_quotation_by_id(quotation_id)
        if quotation is None or quotation.template_name != V2_RENDERER_NAME:
            raise HTTPException(status_code=404, detail="Quotation was not found.")
        effective_lang = lang or quotation.baseline_lang
        current = await documents.get_current_document(quotation_id, effective_lang)
        if current is None:
            raise HTTPException(status_code=404, detail="Canonical document was not found.")
        if current.revision != payload.baseRevision:
            raise HTTPException(
                status_code=409,
                detail={"message": "Media defaults revision conflict.", "currentRevision": current.revision},
            )
        next_document = copy.deepcopy(current.document_json)
        result = await h._apply_missing_media_defaults(session, next_document, quotation_id, effective_lang)
        has_changes = result.get("hasChanges", False)
        applied_count = result.get("appliedCount", 0)

        if payload.dryRun or not has_changes:
            canonical = h._hydrate_canonical_quote_document(next_document, quotation, lang=effective_lang, revision=current.revision)
            return {
                "ok": True,
                "dryRun": payload.dryRun,
                "applied": False,
                "appliedCount": applied_count if payload.dryRun else 0,
                "hasChanges": has_changes,
                "document": canonical,
                "currentRevision": current.revision,
                "rationale": result["rationale"],
                "message": (
                    "No matching media found or all slots already assigned."
                    if not has_changes
                    else f"Previewed {applied_count} matching media defaults."
                ),
            }

        validated = h._normalize_quote_document_structure_or_422(
            h._hydrate_canonical_quote_document(next_document, quotation, lang=effective_lang, revision=payload.baseRevision)
        )
        saved = await documents.save_current_document(
            quotation_id=quotation_id,
            lang=effective_lang,
            document_json=validated,
            expected_revision=payload.baseRevision,
        )
        canonical = h._hydrate_canonical_quote_document(saved.document_json, quotation, lang=effective_lang, revision=saved.revision)
        await documents.append_document_revision(
            quotation_id=quotation_id,
            lang=effective_lang,
            revision=saved.revision,
            document_json=canonical,
            change_source="apply_media_defaults",
        )
        await session.commit()
    return {
        "ok": True,
        "dryRun": False,
        "applied": True,
        "appliedCount": applied_count,
        "hasChanges": True,
        "document": canonical,
        "currentRevision": saved.revision,
        "rationale": result["rationale"],
        "message": f"Successfully applied {applied_count} matching media defaults.",
    }
