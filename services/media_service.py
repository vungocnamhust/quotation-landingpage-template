from __future__ import annotations

import asyncio
import hashlib
import io
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.models.media import MediaAsset
from repositories import MediaRepository, QuotationRepository
from services.storage.r2_storage import R2Storage

ALLOWED_IMAGE_MIME_TYPES = {
    "image/jpeg": ("JPEG", "jpg"),
    "image/png": ("PNG", "png"),
    "image/webp": ("WEBP", "webp"),
}

PIL_FORMAT_TO_MIME = {
    "JPEG": ("image/jpeg", "jpg"),
    "PNG": ("image/png", "png"),
    "WEBP": ("image/webp", "webp"),
}


class MediaValidationError(ValueError):
    pass


class MediaNotFoundError(LookupError):
    pass


class MediaSelectionError(ValueError):
    pass


class MediaSyncPathError(ValueError):
    pass


@dataclass(frozen=True)
class PreparedImage:
    content: bytes
    mime_type: str
    extension: str
    width: int
    height: int
    checksum_sha256: str
    preview_bytes: bytes


def compute_sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def compute_sha256_file(local_path: str) -> str:
    digest = hashlib.sha256()
    with open(local_path, "rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_image_metadata(content: bytes) -> tuple[str, str, int, int]:
    try:
        with Image.open(io.BytesIO(content)) as image:
            normalized = ImageOps.exif_transpose(image)
            image_format = (normalized.format or image.format or "").upper()
            if image_format not in PIL_FORMAT_TO_MIME:
                raise MediaValidationError("Only JPEG, PNG, and WEBP images are supported.")
            mime_type, extension = PIL_FORMAT_TO_MIME[image_format]
            width, height = normalized.size
            if width <= 0 or height <= 0:
                raise MediaValidationError("Uploaded image has invalid dimensions.")
            return mime_type, extension, width, height
    except UnidentifiedImageError as exc:
        raise MediaValidationError("Uploaded file is not a readable image.") from exc


def build_preview_bytes(
    content: bytes,
    *,
    max_width: int,
    max_height: int,
    quality: int,
) -> bytes:
    try:
        with Image.open(io.BytesIO(content)) as image:
            normalized = ImageOps.exif_transpose(image)
            normalized.thumbnail((max_width, max_height))
            if normalized.mode not in ("RGB", "L"):
                canvas = Image.new("RGB", normalized.size, "white")
                alpha = normalized.getchannel("A") if "A" in normalized.getbands() else None
                canvas.paste(normalized.convert("RGB"), mask=alpha)
                normalized = canvas
            elif normalized.mode == "L":
                normalized = normalized.convert("RGB")

            output = io.BytesIO()
            normalized.save(
                output,
                format="JPEG",
                quality=quality,
                optimize=True,
            )
            return output.getvalue()
    except UnidentifiedImageError as exc:
        raise MediaValidationError("Uploaded file is not a readable image.") from exc


class MediaService:
    max_upload_size_bytes = 15 * 1024 * 1024

    def __init__(
        self,
        *,
        storage: R2Storage,
        preview_max_width: int | None = None,
        preview_max_height: int | None = None,
        preview_quality: int | None = None,
    ) -> None:
        self.storage = storage
        self.preview_max_width = preview_max_width or settings.media_preview_max_width
        self.preview_max_height = preview_max_height or settings.media_preview_max_height
        self.preview_quality = preview_quality or settings.media_preview_quality

    async def prepare_upload(
        self,
        *,
        content: bytes,
        declared_mime_type: str | None,
    ) -> PreparedImage:
        if not content:
            raise MediaValidationError("Uploaded file is empty.")
        if len(content) > self.max_upload_size_bytes:
            raise MediaValidationError("Uploaded file exceeds the 15 MB limit.")
        if declared_mime_type and declared_mime_type not in ALLOWED_IMAGE_MIME_TYPES:
            raise MediaValidationError("Only JPEG, PNG, and WEBP uploads are supported.")

        mime_type, extension, width, height = await asyncio.to_thread(read_image_metadata, content)
        preview_bytes = await asyncio.to_thread(
            build_preview_bytes,
            content,
            max_width=self.preview_max_width,
            max_height=self.preview_max_height,
            quality=self.preview_quality,
        )
        checksum_sha256 = await asyncio.to_thread(compute_sha256_bytes, content)
        return PreparedImage(
            content=content,
            mime_type=mime_type,
            extension=extension,
            width=width,
            height=height,
            checksum_sha256=checksum_sha256,
            preview_bytes=preview_bytes,
        )

    async def create_media_asset(
        self,
        session: AsyncSession,
        *,
        original_filename: str,
        content: bytes,
        declared_mime_type: str | None,
        quotation_id: str | None,
        source_type: str,
        local_path: str | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> MediaAsset:
        prepared = await self.prepare_upload(content=content, declared_mime_type=declared_mime_type)
        asset_id = f"med_{uuid.uuid4().hex}"
        original_key, preview_key = self.build_storage_keys(
            asset_id=asset_id,
            extension=prepared.extension,
            quotation_id=quotation_id,
        )
        upload_started = False
        try:
            await asyncio.to_thread(
                self.storage.upload_bytes,
                original_key,
                prepared.content,
                prepared.mime_type,
            )
            await asyncio.to_thread(
                self.storage.upload_bytes,
                preview_key,
                prepared.preview_bytes,
                "image/jpeg",
            )
            upload_started = True
            repository = MediaRepository(session)
            return await repository.create_media_asset(
                asset_id=asset_id,
                quotation_id=quotation_id,
                bucket=self.storage.bucket,
                r2_key=original_key,
                preview_r2_key=preview_key,
                original_filename=os.path.basename(original_filename or "upload"),
                mime_type=prepared.mime_type,
                size_bytes=len(prepared.content),
                checksum_sha256=prepared.checksum_sha256,
                source_type=source_type,
                width=prepared.width,
                height=prepared.height,
                local_path=local_path,
                metadata_json=metadata_json or {},
            )
        except Exception:
            if upload_started:
                await self.delete_objects(original_key, preview_key)
            raise

    async def list_media_assets(
        self,
        session: AsyncSession,
        *,
        quotation_id: str | None = None,
        source_type: str | None = None,
        status: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 24,
    ) -> dict[str, Any]:
        repository = MediaRepository(session)
        items = await repository.list_media_assets(
            quotation_id=quotation_id,
            source_type=source_type,
            status=status,
            search=search,
            page=page,
            page_size=page_size,
        )
        total = await repository.count_media_assets(
            quotation_id=quotation_id,
            source_type=source_type,
            status=status,
            search=search,
        )
        return {
            "items": [self.serialize_media_asset(item) for item in items],
            "page": page,
            "pageSize": page_size,
            "total": total,
        }

    async def select_media_asset(
        self,
        session: AsyncSession,
        *,
        asset_id: str,
        quotation_id: str,
        section_key: str,
        slot_key: str,
        lang: str | None = None,
        display_order: int = 0,
    ) -> None:
        media_repository = MediaRepository(session)
        quotation_repository = QuotationRepository(session)

        quotation = await quotation_repository.get_quotation_by_id(quotation_id)
        if quotation is None:
            raise MediaSelectionError(f"Quotation '{quotation_id}' not found.")

        asset = await media_repository.get_media_asset_by_id(asset_id)
        if asset is None:
            raise MediaNotFoundError(f"Media asset '{asset_id}' not found.")
        if asset.quotation_id and asset.quotation_id != quotation_id:
            raise MediaSelectionError("Cannot attach a quotation-scoped media asset to a different quotation.")

        await media_repository.upsert_media_selection(
            quotation_id=quotation_id,
            asset_id=asset_id,
            section_key=section_key,
            slot_key=slot_key,
            lang=lang,
            display_order=display_order,
        )

    async def sync_media_folder(
        self,
        session: AsyncSession,
        *,
        folder: str,
        recursive: bool,
        quotation_id: str | None,
    ) -> dict[str, Any]:
        resolved_folder = self.resolve_sync_folder(folder)
        media_repository = MediaRepository(session)
        quotation_repository = QuotationRepository(session)

        if quotation_id:
            quotation = await quotation_repository.get_quotation_by_id(quotation_id)
            if quotation is None:
                raise MediaSyncPathError(f"Quotation '{quotation_id}' not found.")

        scanned = 0
        uploaded = 0
        skipped = 0
        failed = 0
        items: list[dict[str, Any]] = []

        iterator = resolved_folder.rglob("*") if recursive else resolved_folder.glob("*")
        for candidate in sorted(iterator):
            if not candidate.is_file():
                continue
            scanned += 1
            try:
                content = await asyncio.to_thread(candidate.read_bytes)
                prepared = await self.prepare_upload(content=content, declared_mime_type=None)
                existing = await media_repository.get_media_asset_by_checksum(
                    prepared.checksum_sha256,
                    quotation_id=quotation_id,
                )
                if existing is not None:
                    if existing.local_path != str(candidate):
                        existing.local_path = str(candidate)
                        await session.flush()
                    skipped += 1
                    items.append(
                        {
                            "status": "skipped",
                            "assetId": existing.id,
                            "localPath": str(candidate),
                            "reason": "checksum_exists",
                        }
                    )
                    continue

                created = await self.create_media_asset(
                    session,
                    original_filename=candidate.name,
                    content=content,
                    declared_mime_type=prepared.mime_type,
                    quotation_id=quotation_id,
                    source_type="local_sync",
                    local_path=str(candidate),
                    metadata_json={"syncFolder": folder},
                )
                uploaded += 1
                items.append(
                    {
                        "status": "uploaded",
                        **self.serialize_media_asset(created),
                        "localPath": str(candidate),
                    }
                )
            except MediaValidationError as exc:
                failed += 1
                items.append(
                    {
                        "status": "failed",
                        "localPath": str(candidate),
                        "reason": str(exc),
                    }
                )
            except Exception as exc:
                failed += 1
                items.append(
                    {
                        "status": "failed",
                        "localPath": str(candidate),
                        "reason": str(exc) or exc.__class__.__name__,
                    }
                )

        return {
            "scanned": scanned,
            "uploaded": uploaded,
            "skipped": skipped,
            "failed": failed,
            "items": items,
        }

    def build_storage_keys(self, *, asset_id: str, extension: str, quotation_id: str | None) -> tuple[str, str]:
        if quotation_id:
            prefix = f"quotations/{quotation_id}/media"
        else:
            prefix = "shared/media"
        return (
            f"{prefix}/original/{asset_id}.{extension}",
            f"{prefix}/preview/{asset_id}.jpg",
        )

    def resolve_sync_folder(self, folder: str) -> Path:
        sync_root = Path(settings.media_sync_dir).resolve()
        target = (sync_root / folder).resolve() if folder else sync_root
        if target != sync_root and sync_root not in target.parents:
            raise MediaSyncPathError("Requested folder is outside the configured media sync directory.")
        if not target.exists() or not target.is_dir():
            raise MediaSyncPathError("Requested folder does not exist.")
        return target

    def serialize_media_asset(self, asset: MediaAsset) -> dict[str, Any]:
        return {
            "id": asset.id,
            "quotationId": asset.quotation_id,
            "status": asset.status,
            "sourceType": asset.source_type,
            "originalFilename": asset.original_filename,
            "mimeType": asset.mime_type,
            "sizeBytes": asset.size_bytes,
            "width": asset.width,
            "height": asset.height,
            "localPath": asset.local_path,
            "r2Key": asset.r2_key,
            "previewR2Key": asset.preview_r2_key,
            "originalUrl": self.storage.build_public_url(asset.r2_key),
            "previewUrl": self.storage.build_public_url(asset.preview_r2_key) if asset.preview_r2_key else None,
            "createdAt": asset.created_at.isoformat() if asset.created_at else None,
        }

    async def delete_objects(self, *keys: str | None) -> None:
        for key in keys:
            if not key:
                continue
            try:
                await asyncio.to_thread(self.storage.delete_object, key)
            except Exception:
                continue
