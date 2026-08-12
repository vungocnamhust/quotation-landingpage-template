"""Legacy V2 media inventory routes, separated from the ASGI entrypoint."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from api import runtime
from schemas.v2.media import MediaSelectionRequest, MediaSyncRequest
from repositories import QuotationRepository
from services.media_service import MediaNotFoundError, MediaSelectionError, MediaSyncPathError, MediaValidationError
from services.storage.r2_storage import R2StorageConfigurationError


router = APIRouter(prefix="/api/v2/media", tags=["legacy-media"])


@router.post("/upload")
async def upload_media_asset(
    file: Annotated[UploadFile, File()],
    quotationId: Annotated[str | None, Form()] = None,
) -> dict:
    media_service = runtime.get_media_service()
    asset = None
    fallback_ctx_exists = bool(quotationId and runtime.load_context(quotationId))
    try:
        content = await file.read()
        if fallback_ctx_exists:
            try:
                async with runtime.get_session_factory()() as session:
                    quotation = await QuotationRepository(session).get_quotation_by_id(quotationId)
                    if quotation is None:
                        return await runtime.store_draft_asset(
                            quotation_id=quotationId,
                            file_name=file.filename or "upload",
                            content=content,
                            declared_mime_type=file.content_type,
                        )
            except Exception as exc:
                if runtime.is_database_unavailable(exc):
                    return await runtime.store_draft_asset(
                        quotation_id=quotationId,
                        file_name=file.filename or "upload",
                        content=content,
                        declared_mime_type=file.content_type,
                    )
                raise
        async with runtime.get_session_factory()() as session:
            if quotationId:
                quotation = await QuotationRepository(session).get_quotation_by_id(quotationId)
                if quotation is None:
                    raise HTTPException(status_code=404, detail=f"Quotation '{quotationId}' not found.")
            asset = await media_service.create_media_asset(
                session,
                original_filename=file.filename or "upload",
                content=content,
                declared_mime_type=file.content_type,
                quotation_id=quotationId,
                source_type="editor_upload",
            )
            await session.commit()
    except HTTPException:
        raise
    except MediaValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except R2StorageConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception:
        if asset is not None:
            await media_service.delete_objects(asset.r2_key, asset.preview_r2_key)
        raise

    payload = media_service.serialize_media_asset(asset)
    return {
        "assetId": payload["id"], "quotationId": payload["quotationId"], "status": payload["status"],
        "originalUrl": payload["originalUrl"], "previewUrl": payload["previewUrl"],
        "width": payload["width"], "height": payload["height"],
    }


@router.get("")
async def list_media_assets(
    quotationId: str | None = None,
    sourceType: str | None = None,
    status: str | None = None,
    search: str | None = None,
    page: int = 1,
    pageSize: int = 24,
) -> dict:
    try:
        async with runtime.get_session_factory()() as session:
            return await runtime.get_media_service().list_media_assets(
                session, quotation_id=quotationId, source_type=sourceType, status=status,
                search=search, page=max(page, 1), page_size=min(max(pageSize, 1), 100),
            )
    except R2StorageConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{asset_id}/select")
async def select_media_asset(asset_id: str, payload: MediaSelectionRequest) -> dict:
    try:
        async with runtime.get_session_factory()() as session:
            await runtime.get_media_service().select_media_asset(
                session, asset_id=asset_id, quotation_id=payload.quotationId, lang=payload.lang,
                section_key=payload.sectionKey, slot_key=payload.slotKey, display_order=payload.displayOrder,
            )
            await session.commit()
    except MediaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MediaSelectionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/sync")
async def sync_media_assets(payload: MediaSyncRequest) -> dict:
    try:
        async with runtime.get_session_factory()() as session:
            result = await runtime.get_media_service().sync_media_folder(
                session, folder=payload.folder, recursive=payload.recursive, quotation_id=payload.quotationId,
            )
            await session.commit()
            return result
    except MediaSyncPathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MediaValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except R2StorageConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
