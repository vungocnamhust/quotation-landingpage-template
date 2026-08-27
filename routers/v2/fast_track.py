"""HTTP boundary for server-owned Fast Track assembly."""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import DbSessionDep, EditorPrincipalDep, OwnedV2QuotationDep
from repositories.errors import DocumentRevisionConflictError
from services.fast_track_assembly_service import FastTrackAssemblyService, FastTrackReviewBlockedError

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
        )
        return FastTrackAssembleResponse(**result)
    except FastTrackReviewBlockedError as error:
        raise HTTPException(status_code=422, detail={"message": str(error), "review": error.review}) from error
    except DocumentRevisionConflictError as error:
        raise HTTPException(status_code=409, detail={"message": "Document revision conflict.", "currentRevision": error.current_revision}) from error
