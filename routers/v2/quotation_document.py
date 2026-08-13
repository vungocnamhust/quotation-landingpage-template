"""Quotation V2 document, presentation, and content drafts endpoints."""
from __future__ import annotations

import copy
from typing import Annotated, Any, Dict, Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from api.dependencies import V2_RENDERER_NAME
from core.auth import Principal, require_editor
from quote_document import CreateQuoteRequestV1
from repositories import (
    BrandRepository,
    ContentDraftRepository,
    QuotationDocumentRepository,
    QuotationRepository,
)
from repositories.errors import DocumentRevisionConflictError
from schemas.brand_contract import _require_active_v2_brand, _serialize_brand_render_profile
from services.content_draft_service import ContentDraftService, ContentGenerationError
from services.section_registry import SECTION_REGISTRY


router = APIRouter(prefix="/api/v2/quotations", tags=["quotation-document"])


class QuoteDocumentUpsertRequest(BaseModel):
    document: Dict[str, Any]
    baseRevision: int | None = None


class PresentationUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    baseRevision: int
    themeId: Literal["brochure"] = "brochure"
    layoutVersion: Literal[1] = 1


class PresentationCopyOverridesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    baseRevision: int
    overrides: dict[str, str]


class PresentationOverridesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    baseRevision: int
    copyOverrides: dict[str, str] = Field(default_factory=dict)
    identityOverrides: dict[str, Any] = Field(default_factory=dict)


class ContentDraftCreateRequest(BaseModel):
    scope: str = Field(min_length=1, max_length=128)
    generationMode: Literal["storytelling", "detailed"] = "storytelling"
    instruction: str = Field(default="", max_length=2000)


class ContentDraftPatchRequest(BaseModel):
    candidate: dict[str, Any]


class ContentDraftManualCreateRequest(BaseModel):
    scope: str = Field(min_length=1, max_length=128)
    candidate: dict[str, Any]
    baseRevision: int


class ContentDraftApplyRequest(BaseModel):
    baseRevision: int


def _get_helpers():
    import main
    return main


@router.get("/{quotation_id}/document")
async def get_quotation_document(
    quotation_id: str,
    request: Request,
    lang: str | None = None,
    language: str | None = None,
    principal: Principal = Depends(require_editor),
):
    h = _get_helpers()
    await h.require_owned_quotation(quotation_id, principal)
    target_lang = lang or language
    if target_lang not in ("en", "vi", "ar"):
        target_lang = None

    quotation, document, effective_lang = await h._load_canonical_quote_document_from_db(quotation_id, target_lang)
    if quotation is None:
        raise HTTPException(status_code=404, detail=f"Quotation '{quotation_id}' not found.")
    if quotation.template_name != V2_RENDERER_NAME:
        raise HTTPException(status_code=400, detail="Document is not a React V2 quotation.")
    if document is None:
        raise HTTPException(status_code=404, detail="No quote document available.")
    brand = await _require_active_v2_brand(quotation.brand_id)
    return {
        "document": h._hydrate_r2_asset_urls(document),
        "lang": effective_lang,
        "documentVersion": ((document.get("meta") or {}).get("version")) or 1,
        "currentRevision": ((document.get("meta") or {}).get("revision")) or 1,
        "sectionRegistry": {key: value.model_dump(mode="json") for key, value in SECTION_REGISTRY.items()},
        "contentRegistry": h.content_registry_for_document_payload(document),
        "contentEditorState": h.content_editor_state_payload(document),
        "editableContract": h.editable_contract_payload(),
        "brandProfile": _serialize_brand_render_profile(brand),
    }


@router.put("/{quotation_id}/document")
async def put_quotation_document(
    quotation_id: str,
    payload: QuoteDocumentUpsertRequest,
    request: Request,
    lang: str | None = None,
    language: str | None = None,
    principal: Principal = Depends(require_editor),
):
    h = _get_helpers()
    await h.require_owned_quotation(quotation_id, principal)
    target_lang = lang or language
    if target_lang not in ("en", "vi", "ar"):
        target_lang = None

    document = copy.deepcopy(payload.document or {})
    try:
        async with h._get_db_session_factory()() as session:
            quotation_repository = QuotationRepository(session)
            document_repository = QuotationDocumentRepository(session)

            quotation = await quotation_repository.get_quotation_by_id(quotation_id)
            if quotation is None:
                raise HTTPException(status_code=404, detail=f"Quotation '{quotation_id}' not found.")

            effective_lang = target_lang or quotation.baseline_lang
            if quotation.template_name != V2_RENDERER_NAME:
                raise HTTPException(status_code=400, detail="Document is not a React V2 quotation.")

            current_document = await document_repository.get_current_document(quotation_id, effective_lang)
            sanitized_document = h._sanitize_canonical_asset_state(
                document,
                current_document.document_json if current_document is not None else None,
            )
            sanitized_document["brand"] = {}
            sanitized_document = h._hydrate_r2_asset_urls(sanitized_document)
            document = h._hydrate_canonical_quote_document(
                sanitized_document,
                quotation,
                lang=effective_lang,
                revision=payload.baseRevision or int(((document.get("meta") or {}).get("revision")) or 1),
            )
            validated_document = h._validate_quote_document_or_422(document)
            saved_document = await document_repository.save_current_document(
                quotation_id=quotation_id,
                lang=effective_lang,
                document_json=validated_document,
                expected_revision=payload.baseRevision,
            )
            canonical_document = h._hydrate_canonical_quote_document(
                saved_document.document_json,
                quotation,
                lang=effective_lang,
                revision=saved_document.revision,
            )
            await document_repository.append_document_revision(
                quotation_id=quotation_id,
                lang=effective_lang,
                revision=saved_document.revision,
                document_json=canonical_document,
                change_source="autosave",
            )
            await session.commit()
    except DocumentRevisionConflictError as exc:
        quotation, _, effective_lang = await h._load_canonical_quote_document_from_db(quotation_id, target_lang)
        current_document = None
        if quotation is not None and exc.current_document is not None:
            current_document = h._hydrate_canonical_quote_document(
                exc.current_document,
                quotation,
                lang=effective_lang or target_lang or quotation.baseline_lang,
                revision=exc.current_revision or 0,
            )
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Document revision conflict.",
                "currentRevision": exc.current_revision,
                "currentDocument": current_document,
            },
        ) from exc

    return {
        "ok": True,
        "document": canonical_document,
        "documentVersion": ((canonical_document.get("meta") or {}).get("version")) or 1,
        "currentRevision": ((canonical_document.get("meta") or {}).get("revision")) or 1,
        "sectionRegistry": {key: value.model_dump(mode="json") for key, value in SECTION_REGISTRY.items()},
    }


@router.put("/{quotation_id}/presentation")
async def put_quotation_presentation_v2(
    quotation_id: str,
    payload: PresentationUpsertRequest,
    lang: str | None = None,
    principal: Principal = Depends(require_editor),
):
    h = _get_helpers()
    await h.require_owned_quotation(quotation_id, principal)
    async with h._get_db_session_factory()() as session:
        quotes, documents = QuotationRepository(session), QuotationDocumentRepository(session)
        quotation = await quotes.get_quotation_by_id(quotation_id)
        if quotation is None:
            raise HTTPException(status_code=404, detail="Quotation was not found.")
        if quotation.template_name != V2_RENDERER_NAME:
            raise HTTPException(status_code=400, detail="Presentation controls are only available for React V2 quotations.")
        effective_lang = lang or quotation.baseline_lang
        current = await documents.get_current_document(quotation_id, effective_lang)
        if current is None:
            raise HTTPException(status_code=404, detail="Canonical document was not found.")
        next_document = copy.deepcopy(current.document_json)
        current_presentation = next_document.get("presentation") or {}
        next_document["presentation"] = {
            "renderer": V2_RENDERER_NAME,
            "themeId": payload.themeId,
            "layoutVersion": payload.layoutVersion,
            "copyOverrides": current_presentation.get("copyOverrides") or {},
            "mediaOverrides": current_presentation.get("mediaOverrides") or {},
            "mediaDefaults": current_presentation.get("mediaDefaults") or {},
            "identityOverrides": current_presentation.get("identityOverrides") or {},
        }
        try:
            validated = h._validate_quote_document_or_422(
                h._hydrate_canonical_quote_document(next_document, quotation, lang=effective_lang, revision=payload.baseRevision)
            )
            saved = await documents.save_current_document(
                quotation_id=quotation_id,
                lang=effective_lang,
                document_json=validated,
                expected_revision=payload.baseRevision,
            )
        except DocumentRevisionConflictError as exc:
            raise HTTPException(status_code=409, detail={"message": "Presentation revision conflict.", "currentRevision": exc.current_revision}) from exc
        canonical = h._hydrate_canonical_quote_document(saved.document_json, quotation, lang=effective_lang, revision=saved.revision)
        await documents.append_document_revision(
            quotation_id=quotation_id,
            lang=effective_lang,
            revision=saved.revision,
            document_json=canonical,
            change_source="update_presentation",
        )
        await session.commit()
    return {"ok": True, "document": canonical, "currentRevision": saved.revision}


@router.put("/{quotation_id}/presentation/copy-overrides")
async def put_quotation_presentation_copy_overrides_v2(
    quotation_id: str,
    payload: PresentationCopyOverridesRequest,
    lang: str | None = None,
    principal: Principal = Depends(require_editor),
):
    h = _get_helpers()
    await h.require_owned_quotation(quotation_id, principal)
    overrides = h._validate_v2_copy_overrides(payload.overrides)
    async with h._get_db_session_factory()() as session:
        quotes, documents = QuotationRepository(session), QuotationDocumentRepository(session)
        quotation = await quotes.get_quotation_by_id(quotation_id)
        if quotation is None or quotation.template_name != V2_RENDERER_NAME:
            raise HTTPException(status_code=404, detail="Quotation was not found.")
        effective_lang = lang or quotation.baseline_lang
        current = await documents.get_current_document(quotation_id, effective_lang)
        if current is None:
            raise HTTPException(status_code=404, detail="Canonical document was not found.")
        next_document = copy.deepcopy(current.document_json)
        presentation = next_document.setdefault("presentation", {})
        current_overrides = presentation.get("copyOverrides") or {}
        if not isinstance(current_overrides, dict):
            current_overrides = {}
        presentation["copyOverrides"] = h._validate_v2_copy_overrides({**current_overrides, **overrides})
        try:
            validated = h._validate_quote_document_or_422(
                h._hydrate_canonical_quote_document(next_document, quotation, lang=effective_lang, revision=payload.baseRevision)
            )
            saved = await documents.save_current_document(
                quotation_id=quotation_id,
                lang=effective_lang,
                document_json=validated,
                expected_revision=payload.baseRevision,
            )
        except DocumentRevisionConflictError as exc:
            raise HTTPException(status_code=409, detail={"message": "Presentation copy revision conflict.", "currentRevision": exc.current_revision}) from exc
        canonical = h._hydrate_canonical_quote_document(saved.document_json, quotation, lang=effective_lang, revision=saved.revision)
        await documents.append_document_revision(
            quotation_id=quotation_id,
            lang=effective_lang,
            revision=saved.revision,
            document_json=canonical,
            change_source="update_presentation_copy",
        )
        await session.commit()
    return {"ok": True, "document": canonical, "currentRevision": saved.revision}


@router.put("/{quotation_id}/presentation/overrides")
async def put_quotation_presentation_overrides_v2(
    quotation_id: str,
    payload: PresentationOverridesRequest,
    lang: str | None = None,
    principal: Principal = Depends(require_editor),
):
    h = _get_helpers()
    await h.require_owned_quotation(quotation_id, principal)
    copy_overrides = h._validate_v2_copy_overrides(payload.copyOverrides)
    identity = h._validate_v2_identity_overrides(payload.identityOverrides)

    async with h._get_db_session_factory()() as session:
        quotes, documents = QuotationRepository(session), QuotationDocumentRepository(session)
        quotation = await quotes.get_quotation_by_id(quotation_id)
        if quotation is None or quotation.template_name != V2_RENDERER_NAME:
            raise HTTPException(status_code=404, detail="Quotation was not found.")
        effective_lang = lang or quotation.baseline_lang
        current = await documents.get_current_document(quotation_id, effective_lang)
        if current is None:
            raise HTTPException(status_code=404, detail="Canonical document was not found.")
        next_document = copy.deepcopy(current.document_json)
        presentation = next_document.setdefault("presentation", {})
        current_copy = presentation.get("copyOverrides") or {}
        current_identity = presentation.get("identityOverrides") or {}
        presentation["copyOverrides"] = h._validate_v2_copy_overrides({**current_copy, **copy_overrides})
        presentation["mediaOverrides"] = presentation.get("mediaOverrides") or {}
        presentation["identityOverrides"] = {**current_identity, **identity}
        try:
            validated = h._validate_quote_document_or_422(
                h._hydrate_canonical_quote_document(next_document, quotation, lang=effective_lang, revision=payload.baseRevision)
            )
            saved = await documents.save_current_document(
                quotation_id=quotation_id,
                lang=effective_lang,
                document_json=validated,
                expected_revision=payload.baseRevision,
            )
        except DocumentRevisionConflictError as exc:
            raise HTTPException(status_code=409, detail={"message": "Presentation override revision conflict.", "currentRevision": exc.current_revision}) from exc
        canonical = h._hydrate_canonical_quote_document(saved.document_json, quotation, lang=effective_lang, revision=saved.revision)
        await documents.append_document_revision(
            quotation_id=quotation_id,
            lang=effective_lang,
            revision=saved.revision,
            document_json=canonical,
            change_source="update_presentation_overrides",
        )
        await session.commit()
    return {"ok": True, "document": canonical, "currentRevision": saved.revision}


@router.get("/{quotation_id}/content-drafts")
async def list_content_drafts_v2(
    quotation_id: str,
    lang: str | None = None,
    principal: Principal = Depends(require_editor),
):
    h = _get_helpers()
    await h.require_owned_quotation(quotation_id, principal)
    _quotation, lang = await h._resolve_v2_locale(quotation_id, lang)
    async with h._get_db_session_factory()() as session:
        quotation = await QuotationRepository(session).get_quotation_by_id(quotation_id)
        if quotation is None:
            raise HTTPException(status_code=404, detail="Quotation was not found.")
        items = await ContentDraftRepository(session).list(quotation_id, lang)
        return {"drafts": [h._serialize_content_draft(item) for item in items]}


@router.post("/{quotation_id}/content-drafts")
async def create_content_drafts_v2(
    quotation_id: str,
    payload: ContentDraftCreateRequest,
    lang: str | None = None,
    principal: Principal = Depends(require_editor),
):
    h = _get_helpers()
    await h.require_owned_quotation(quotation_id, principal)
    _quotation, lang = await h._resolve_v2_locale(quotation_id, lang)
    async with h._get_db_session_factory()() as session:
        quotes, documents, drafts = QuotationRepository(session), QuotationDocumentRepository(session), ContentDraftRepository(session)
        quotation = await quotes.get_quotation_by_id(quotation_id)
        request = await quotes.get_latest_quotation_request(quotation_id) if quotation else None
        document = await documents.get_current_document(quotation_id, lang) if quotation else None
        if quotation is None or request is None or document is None:
            raise HTTPException(status_code=404, detail="Quotation content context was not found.")
        facts, resolved = await h._resolve_v2_facts(CreateQuoteRequestV1.model_validate(h.normalize_legacy_facts_snapshot(request.request_json)))
        try:
            brand = await BrandRepository(session).get_active(quotation.brand_id)
            if brand is None:
                raise HTTPException(status_code=422, detail={"message": "Brand is unavailable for content generation.", "missingInputs": ["brand_id"]})
            items = await ContentDraftService(drafts, h._brand_generation_profile(brand)).create(
                quotation_id=quotation_id,
                payload=facts,
                facts_hash=resolved["factsHash"],
                document_revision=document.revision,
                lang=lang,
                scope=payload.scope,
                mode=payload.generationMode,
                instruction=payload.instruction,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail={"message": str(exc)}) from exc
        except ContentGenerationError as exc:
            raise HTTPException(status_code=503, detail={"message": str(exc)}) from exc
        await session.commit()
        return {"draft": h._serialize_content_draft(items[0])}


@router.post("/{quotation_id}/content-drafts/prompt-preview")
async def preview_content_draft_prompt_v2(
    quotation_id: str,
    payload: ContentDraftCreateRequest,
    lang: str | None = None,
    principal: Principal = Depends(require_editor),
):
    h = _get_helpers()
    await h.require_owned_quotation(quotation_id, principal)
    _quotation, lang = await h._resolve_v2_locale(quotation_id, lang)
    async with h._get_db_session_factory()() as session:
        quotes, documents, drafts = QuotationRepository(session), QuotationDocumentRepository(session), ContentDraftRepository(session)
        quotation = await quotes.get_quotation_by_id(quotation_id)
        request = await quotes.get_latest_quotation_request(quotation_id) if quotation else None
        document = await documents.get_current_document(quotation_id, lang) if quotation else None
        if quotation is None or request is None or document is None:
            raise HTTPException(status_code=404, detail="Quotation content context was not found.")
        facts, _resolved = await h._resolve_v2_facts(CreateQuoteRequestV1.model_validate(h.normalize_legacy_facts_snapshot(request.request_json)))
        try:
            brand = await BrandRepository(session).get_active(quotation.brand_id)
            if brand is None:
                raise HTTPException(status_code=422, detail={"message": "Brand is unavailable for content generation.", "missingInputs": ["brand_id"]})
            preview = ContentDraftService(drafts, h._brand_generation_profile(brand)).preview_prompt(
                payload=facts,
                scope=payload.scope,
                mode=payload.generationMode,
                instruction=payload.instruction,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail={"message": str(exc)}) from exc
        return {"promptPreview": preview}


@router.post("/{quotation_id}/content-drafts/manual")

async def create_manual_content_draft_v2(
    quotation_id: str,
    payload: ContentDraftManualCreateRequest,
    lang: str | None = None,
    principal: Principal = Depends(require_editor),
):
    h = _get_helpers()
    await h.require_owned_quotation(quotation_id, principal)
    _quotation, lang = await h._resolve_v2_locale(quotation_id, lang)
    async with h._get_db_session_factory()() as session:
        quotes, documents, drafts = QuotationRepository(session), QuotationDocumentRepository(session), ContentDraftRepository(session)
        quotation = await quotes.get_quotation_by_id(quotation_id)
        request = await quotes.get_latest_quotation_request(quotation_id) if quotation else None
        document = await documents.get_current_document(quotation_id, lang) if quotation else None
        if quotation is None or request is None or document is None:
            raise HTTPException(status_code=404, detail="Quotation content context was not found.")
        if document.revision != payload.baseRevision:
            raise HTTPException(status_code=409, detail={"message": "Document revision conflict.", "currentRevision": document.revision})
        facts, resolved = await h._resolve_v2_facts(CreateQuoteRequestV1.model_validate(h.normalize_legacy_facts_snapshot(request.request_json)))
        brand = await BrandRepository(session).get_active(quotation.brand_id)
        if brand is None:
            raise HTTPException(status_code=422, detail={"message": "Brand is unavailable for Content Studio.", "missingInputs": ["brand_id"]})
        try:
            draft = await ContentDraftService(drafts, h._brand_generation_profile(brand)).create_manual(
                quotation_id=quotation_id,
                payload=facts,
                facts_hash=resolved["factsHash"],
                document_revision=document.revision,
                lang=lang,
                scope=payload.scope,
                candidate=payload.candidate,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail={"message": str(exc)}) from exc
        await session.commit()
        return {"draft": h._serialize_content_draft(draft)}


@router.patch("/{quotation_id}/content-drafts/{draft_id}")
async def patch_content_draft_v2(
    quotation_id: str,
    draft_id: str,
    payload: ContentDraftPatchRequest,
    principal: Principal = Depends(require_editor),
):
    h = _get_helpers()
    await h.require_owned_quotation(quotation_id, principal)
    async with h._get_db_session_factory()() as session:
        draft = await ContentDraftRepository(session).get(quotation_id, draft_id)
        if draft is None:
            raise HTTPException(status_code=404, detail="Content draft was not found.")
        if draft.status not in ("draft", "stale"):
            raise HTTPException(status_code=409, detail={"message": "Only a draft candidate can be edited."})
        try:
            draft.candidate_json = ContentDraftService.validate_candidate(draft.scope, payload.candidate)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail={"message": str(exc)}) from exc
        draft.generation_metadata = {**draft.generation_metadata, "manualEdited": True}
        await session.commit()
        return {"draft": h._serialize_content_draft(draft)}


@router.post("/{quotation_id}/content-drafts/{draft_id}/discard")
async def discard_content_draft_v2(
    quotation_id: str,
    draft_id: str,
    principal: Principal = Depends(require_editor),
):
    h = _get_helpers()
    await h.require_owned_quotation(quotation_id, principal)
    async with h._get_db_session_factory()() as session:
        draft = await ContentDraftRepository(session).get(quotation_id, draft_id)
        if draft is None:
            raise HTTPException(status_code=404, detail="Content draft was not found.")
        draft.status = "discarded"
        await session.commit()
        return {"draft": h._serialize_content_draft(draft)}


@router.post("/{quotation_id}/content-drafts/{draft_id}/apply")
async def apply_content_draft_v2(
    quotation_id: str,
    draft_id: str,
    payload: ContentDraftApplyRequest,
    principal: Principal = Depends(require_editor),
):
    h = _get_helpers()
    await h.require_owned_quotation(quotation_id, principal)
    async with h._get_db_session_factory()() as session:
        quotes, documents, drafts = QuotationRepository(session), QuotationDocumentRepository(session), ContentDraftRepository(session)
        quotation = await quotes.get_quotation_by_id(quotation_id)
        draft = await drafts.get(quotation_id, draft_id)
        if quotation is None or draft is None:
            raise HTTPException(status_code=404, detail="Quotation content draft was not found.")
        if draft.status not in ("draft", "stale"):
            raise HTTPException(status_code=409, detail={"message": "Only a current draft candidate can be applied."})
        current = await documents.get_current_document(quotation_id, draft.lang)
        if current is None:
            raise HTTPException(status_code=404, detail="Current document not found.")
        if payload.baseRevision != current.revision:
            raise HTTPException(status_code=409, detail={"message": "Document revision conflict.", "currentRevision": current.revision})
        draft.source_document_revision = current.revision
        try:
            merged = ContentDraftService.apply_candidate(copy.deepcopy(current.document_json), draft.scope, draft.candidate_json)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail={"message": str(exc)}) from exc
        try:
            saved = await documents.save_current_document(quotation_id=quotation_id, lang=draft.lang, document_json=merged, expected_revision=current.revision)
        except DocumentRevisionConflictError as exc:
            raise HTTPException(status_code=409, detail={"message": "Document revision conflict.", "currentRevision": exc.current_revision}) from exc
        merged.setdefault("meta", {})["revision"] = saved.revision
        await documents.append_document_revision(quotation_id=quotation_id, lang=draft.lang, revision=saved.revision, document_json=merged, change_source="apply_content_draft")
        draft.status = "applied"
        await drafts.mark_pending_drafts_stale(quotation_id)
        draft.status = "applied"
        await session.commit()
        return {"ok": True, "document": merged, "currentRevision": saved.revision}
