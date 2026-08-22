from __future__ import annotations

import asyncio
import hashlib
import mimetypes
import os
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.config import settings
from repositories.media_library_repository import MediaLibraryRepository
from db.models.media_library import MediaLibraryObject
from services.media_service import build_preview_bytes, read_image_metadata
from services.storage.r2_storage import R2Storage
from services.media_service import PreparedImage
from services.media_locations import MediaLocation
from services.media_default_service import seed_brand_fallback_media

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def catalogue_metadata_for_key(key: str) -> dict[str, str]:
    """Recover the V2 taxonomy for objects discovered by an R2 sync."""
    parts = normalize_library_prefix(key).split("/")
    if "accommodations" in parts:
        index = parts.index("accommodations")
        if len(parts) > index + 4:
            category = parts[-2] if len(parts) >= 2 else ""
            accommodation_slug = parts[-3] if category in {"exteriors", "interiors"} and len(parts) >= 3 else (parts[-2] if category != "preview" else "")
            return {"media_kind": "accommodation", "subject_type": "accommodation", "destination_id": "", "accommodation_slug": accommodation_slug, "accommodation_kind": "hotel"}
    if len(parts) >= 5 and parts[0] not in {"team", "published"}:
        return {"media_kind": "destination", "subject_type": "destination", "subject_id": parts[-2] if parts[-2] != "preview" else ""}
    if len(parts) >= 3 and parts[0] == "team":
        return {"media_kind": "team", "subject_type": "travel_designer", "subject_id": parts[1]}
    return {}


def normalize_library_prefix(prefix: str) -> str:
    return (prefix or "").strip().strip("/")


def is_allowed_prefix(prefix: str, prefixes: tuple[str, ...] | None = None) -> bool:
    requested = normalize_library_prefix(prefix)
    allowed = prefixes or settings.media_library_roots
    return any(requested == item or requested.startswith(f"{item}/") for item in allowed)


def is_media_key(key: str) -> bool:
    normalized = key.lower()
    segments = [segment for segment in normalized.split("/") if segment]
    return "published" not in segments and "preview" not in segments and os.path.splitext(normalized)[1] in IMAGE_EXTENSIONS


class MediaLibraryService:
    def __init__(self, *, storage: R2Storage, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.storage = storage
        self.session_factory = session_factory

    async def create_run(self) -> str:
        run_id = f"mls_{uuid.uuid4().hex}"
        async with self.session_factory() as session:
            await MediaLibraryRepository(session).create_sync_run(run_id=run_id, prefixes=list(settings.media_library_roots))
            await session.commit()
        return run_id

    async def process_run(self, run_id: str) -> None:
        try:
            # These R2-backed fallbacks make quotation creation total even when
            # a destination catalogue has not yet been populated.
            await seed_brand_fallback_media(self.storage)
            async with self.session_factory() as session:
                repository = MediaLibraryRepository(session)
                run = await repository.get_sync_run(run_id)
                if run is None or run.status == "completed":
                    return
                if run.status in {"queued", "indexing"}:
                    await repository.mark_run_started(run)
                await session.commit()

            for prefix in settings.media_library_roots:
                await self._index_prefix(run_id, prefix)

            async with self.session_factory() as session:
                run = await MediaLibraryRepository(session).get_sync_run(run_id)
                if run is not None:
                    run.status = "previewing"
                    await session.commit()
            await self._create_pending_previews(run_id)
            async with self.session_factory() as session:
                run = await MediaLibraryRepository(session).get_sync_run(run_id)
                if run is not None:
                    run.status = "completed"
                    run.finished_at = datetime.now().astimezone()
                    await session.commit()
        except Exception as exc:
            async with self.session_factory() as session:
                run = await MediaLibraryRepository(session).get_sync_run(run_id)
                if run is not None:
                    run.status, run.error_message, run.finished_at = "failed", str(exc)[:1024], datetime.now().astimezone()
                    await session.commit()

    async def _index_prefix(self, run_id: str, prefix: str) -> None:
        token: str | None = None
        while True:
            response = await asyncio.to_thread(self.storage.list_objects, prefix=f"{prefix.rstrip('/')}/", continuation_token=token)
            async with self.session_factory() as session:
                repository = MediaLibraryRepository(session)
                run = await repository.get_sync_run(run_id)
                if run is None:
                    return
                for entry in response.get("Contents") or []:
                    key = entry.get("Key") or ""
                    run.scanned_count += 1
                    if not is_media_key(key):
                        continue
                    parent, file_name = key.rsplit("/", 1) if "/" in key else ("", key)
                    await repository.upsert_object(run_id=run_id, bucket=self.storage.bucket, r2_key=key, parent_prefix=parent, file_name=file_name, content_type=mimetypes.guess_type(file_name)[0], size_bytes=int(entry.get("Size") or 0), etag=(entry.get("ETag") or "").strip('"') or None, source_modified_at=entry.get("LastModified"), metadata={"source": "r2_sync", **catalogue_metadata_for_key(key)})
                    run.indexed_count += 1
                run.cursor = {"prefix": prefix, "continuationToken": response.get("NextContinuationToken")}
                await session.commit()
            token = response.get("NextContinuationToken")
            if not response.get("IsTruncated") or not token:
                break
        async with self.session_factory() as session:
            await MediaLibraryRepository(session).deactivate_missing(prefix=f"{prefix.rstrip('/')}/", run_id=run_id)
            await session.commit()

    async def _create_pending_previews(self, run_id: str) -> None:
        semaphore = asyncio.Semaphore(max(settings.media_library_preview_concurrency, 1))
        async with self.session_factory() as session:
            candidates = await MediaLibraryRepository(session).list_pending_previews(limit=10000)
            candidate_ids = [item.id for item in candidates]
        await asyncio.gather(*(self._create_preview(item_id, run_id, semaphore) for item_id in candidate_ids))

    async def _create_preview(self, object_id: int, run_id: str, semaphore: asyncio.Semaphore) -> None:
        async with semaphore:
            async with self.session_factory() as session:
                item = await session.get(MediaLibraryObject, object_id)
                if item is None or item.preview_status != "pending":
                    return
                item.preview_status = "processing"
                await session.commit()
                key, etag = item.r2_key, item.etag or ""
            try:
                content = await asyncio.to_thread(self.storage.download_bytes, key)
                _, _, width, height = await asyncio.to_thread(read_image_metadata, content)
                preview = await asyncio.to_thread(build_preview_bytes, content, max_width=settings.media_preview_max_width, max_height=settings.media_preview_max_height, quality=settings.media_preview_quality)
                preview_key = f"{item.parent_prefix}/preview/{hashlib.sha256(f'{key}:{etag}'.encode()).hexdigest()}.jpg"
                await asyncio.to_thread(self.storage.upload_bytes, preview_key, preview, "image/jpeg")
                async with self.session_factory() as session:
                    item = await session.get(MediaLibraryObject, object_id)
                    run = await MediaLibraryRepository(session).get_sync_run(run_id)
                    if item is not None:
                        item.preview_r2_key, item.preview_status, item.preview_error = preview_key, "ready", None
                        item.width, item.height = width, height
                    if run is not None:
                        run.preview_count += 1
                    await session.commit()
            except Exception as exc:
                async with self.session_factory() as session:
                    item = await session.get(MediaLibraryObject, object_id)
                    run = await MediaLibraryRepository(session).get_sync_run(run_id)
                    if item is not None:
                        item.preview_status, item.preview_error = "failed", str(exc)[:512]
                    if run is not None:
                        run.error_count += 1
                    await session.commit()

    async def create_library_asset(self, *, location: MediaLocation, prepared: PreparedImage) -> MediaLibraryObject:
        asset_id = uuid.uuid4().hex
        # Object identity is opaque.  R2 routing uses the persisted profile root
        # and exterior/interior folder, not a filename convention supplied by an editor.
        original_key = f"{location.leaf_prefix}/{asset_id}.{prepared.extension}"
        preview_key = f"{location.leaf_prefix}/preview/{asset_id}.jpg"
        await asyncio.to_thread(self.storage.upload_bytes, original_key, prepared.content, prepared.mime_type)
        try:
            await asyncio.to_thread(self.storage.upload_bytes, preview_key, prepared.preview_bytes, "image/jpeg")
            async with self.session_factory() as session:
                item = await MediaLibraryRepository(session).upsert_object(
                    run_id=None, bucket=self.storage.bucket, r2_key=original_key, parent_prefix=location.leaf_prefix,
                    file_name=os.path.basename(original_key), content_type=prepared.mime_type, size_bytes=len(prepared.content),
                    etag=prepared.checksum_sha256, source_modified_at=datetime.now().astimezone(),
                    metadata={"media_kind": location.kind, "subject_type": location.subject_type, "subject_id": location.subject_id, "destination_id": location.destination_id, "accommodation_slug": location.accommodation_slug, "accommodation_kind": location.accommodation_kind, "source": "library_upload"},
                )
                item.preview_r2_key, item.preview_status, item.width, item.height = preview_key, "ready", prepared.width, prepared.height
                await session.commit()
                return item
        except Exception:
            await asyncio.to_thread(self.storage.delete_object, original_key)
            raise
