from __future__ import annotations

from datetime import datetime

from sqlalchemy import distinct, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.media_library import MediaLibraryObject, MediaLibrarySyncRun


class MediaLibraryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_sync_run(self, *, run_id: str, prefixes: list[str]) -> MediaLibrarySyncRun:
        run = MediaLibrarySyncRun(id=run_id, prefixes=prefixes)
        self.session.add(run)
        await self.session.flush()
        return run

    async def get_sync_run(self, run_id: str) -> MediaLibrarySyncRun | None:
        return await self.session.get(MediaLibrarySyncRun, run_id)

    async def get_active_sync_run(self) -> MediaLibrarySyncRun | None:
        result = await self.session.scalars(
            select(MediaLibrarySyncRun)
            .where(MediaLibrarySyncRun.status.in_(("queued", "indexing", "previewing")))
            .order_by(MediaLibrarySyncRun.created_at.asc())
            .limit(1)
        )
        return result.first()

    async def has_media_for_destination(self, destination_id: str) -> bool:
        """True if any active object is anchored to this destination (15.2b §4 storage freeze)."""
        result = await self.session.scalar(
            select(MediaLibraryObject.id)
            .where(MediaLibraryObject.destination_id == destination_id, MediaLibraryObject.is_active.is_(True))
            .limit(1)
        )
        return result is not None

    async def get_active_media_keys(self, keys: set[str]) -> set[str]:
        if not keys:
            return set()
        result = await self.session.scalars(
            select(MediaLibraryObject.r2_key).where(
                MediaLibraryObject.r2_key.in_(keys),
                MediaLibraryObject.is_active.is_(True),
            )
        )
        return set(result.all())

    async def list_active_candidates(self) -> list[MediaLibraryObject]:
        """Return the indexed catalogue once for a quotation-level resolver."""
        result = await self.session.scalars(
            select(MediaLibraryObject).where(MediaLibraryObject.is_active.is_(True))
        )
        return list(result.all())

    async def mark_run_started(self, run: MediaLibrarySyncRun) -> None:
        run.status = "indexing"
        run.started_at = datetime.now().astimezone()
        await self.session.flush()

    async def upsert_object(self, *, run_id: str | None, bucket: str, r2_key: str, parent_prefix: str, file_name: str, content_type: str | None, size_bytes: int, etag: str | None, source_modified_at: datetime | None, metadata: dict | None = None) -> MediaLibraryObject:
        metadata = metadata or {}
        result = await self.session.scalars(select(MediaLibraryObject).where(MediaLibraryObject.r2_key == r2_key))
        item = result.first()
        if item is None:
            item = MediaLibraryObject(bucket=bucket, r2_key=r2_key, parent_prefix=parent_prefix, file_name=file_name, content_type=content_type, size_bytes=size_bytes, etag=etag, source_modified_at=source_modified_at, last_seen_run_id=run_id, is_active=True, **metadata)
            self.session.add(item)
        else:
            changed = item.etag != etag
            item.bucket, item.parent_prefix, item.file_name = bucket, parent_prefix, file_name
            item.content_type, item.size_bytes, item.etag, item.source_modified_at = content_type, size_bytes, etag, source_modified_at
            item.last_seen_run_id, item.is_active = run_id, True
            for key, value in metadata.items():
                setattr(item, key, value)
            if changed:
                item.preview_r2_key, item.preview_status, item.preview_error = None, "pending", None
        await self.session.flush()
        return item

    async def deactivate_missing(self, *, prefix: str, run_id: str) -> None:
        await self.session.execute(update(MediaLibraryObject).where(MediaLibraryObject.r2_key.startswith(prefix), MediaLibraryObject.last_seen_run_id != run_id).values(is_active=False))

    async def list_children(self, *, prefix: str, cursor: int = 0, limit: int = 60, search: str = "") -> list[MediaLibraryObject]:
        stmt = select(MediaLibraryObject).where(MediaLibraryObject.parent_prefix == prefix, MediaLibraryObject.is_active.is_(True))
        if search:
            stmt = stmt.where(MediaLibraryObject.file_name.ilike(f"%{search}%"))
        result = await self.session.scalars(stmt.order_by(MediaLibraryObject.file_name.asc(), MediaLibraryObject.id.asc()).offset(cursor).limit(limit + 1))
        return list(result.all())

    async def list_child_prefixes(self, *, prefix: str) -> list[str]:
        needle = f"{prefix.rstrip('/')}/" if prefix else ""
        rows = await self.session.scalars(select(distinct(MediaLibraryObject.parent_prefix)).where(MediaLibraryObject.is_active.is_(True), MediaLibraryObject.parent_prefix.startswith(needle)))
        children: set[str] = set()
        for parent in rows:
            remainder = parent[len(needle):] if needle else parent
            if not remainder:
                continue
            children.add(f"{needle}{remainder.split('/', 1)[0]}".rstrip("/"))
        return sorted(children)

    async def list_pending_previews(self, *, limit: int) -> list[MediaLibraryObject]:
        result = await self.session.scalars(select(MediaLibraryObject).where(MediaLibraryObject.is_active.is_(True), MediaLibraryObject.preview_status == "pending").order_by(MediaLibraryObject.id.asc()).limit(limit))
        return list(result.all())

    async def search(self, *, prefix: str, query: str, cursor: int = 0, limit: int = 60) -> list[MediaLibraryObject]:
        stmt = select(MediaLibraryObject).where(MediaLibraryObject.r2_key.startswith(f"{prefix.rstrip('/')}/"), MediaLibraryObject.is_active.is_(True))
        if query:
            stmt = stmt.where(MediaLibraryObject.file_name.ilike(f"%{query}%"))
        result = await self.session.scalars(stmt.order_by(MediaLibraryObject.file_name.asc(), MediaLibraryObject.id.asc()).offset(cursor).limit(limit + 1))
        return list(result.all())
