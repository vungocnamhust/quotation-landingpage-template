from __future__ import annotations

from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.media import MediaAsset, MediaSelection


class MediaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_media_asset(
        self,
        *,
        asset_id: str,
        bucket: str,
        r2_key: str,
        original_filename: str,
        mime_type: str,
        size_bytes: int,
        checksum_sha256: str,
        source_type: str,
        quotation_id: str | None = None,
        preview_r2_key: str | None = None,
        width: int | None = None,
        height: int | None = None,
        local_path: str | None = None,
        status: str = "ready",
        metadata_json: dict[str, Any] | None = None,
    ) -> MediaAsset:
        asset = MediaAsset(
            id=asset_id,
            quotation_id=quotation_id,
            source_type=source_type,
            bucket=bucket,
            r2_key=r2_key,
            preview_r2_key=preview_r2_key,
            original_filename=original_filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            checksum_sha256=checksum_sha256,
            width=width,
            height=height,
            local_path=local_path,
            status=status,
            metadata_json=metadata_json or {},
        )
        self.session.add(asset)
        await self.session.flush()
        return asset

    async def get_media_asset_by_id(self, asset_id: str) -> MediaAsset | None:
        return await self.session.get(MediaAsset, asset_id)

    async def get_media_asset_by_checksum(
        self,
        checksum_sha256: str,
        *,
        quotation_id: str | None = None,
    ) -> MediaAsset | None:
        stmt = select(MediaAsset).where(MediaAsset.checksum_sha256 == checksum_sha256)
        if quotation_id is not None:
            stmt = stmt.where(MediaAsset.quotation_id == quotation_id)
        stmt = stmt.order_by(MediaAsset.created_at.desc(), MediaAsset.id.desc()).limit(1)
        result = await self.session.scalars(stmt)
        return result.first()

    async def list_media_assets(
        self,
        *,
        quotation_id: str | None = None,
        source_type: str | None = None,
        status: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> list[MediaAsset]:
        stmt: Select[tuple[MediaAsset]] = select(MediaAsset).order_by(MediaAsset.created_at.desc(), MediaAsset.id.desc())
        if quotation_id:
            stmt = stmt.where(
                or_(
                    MediaAsset.quotation_id == quotation_id,
                    MediaAsset.quotation_id.is_(None),
                )
            )
        if source_type:
            stmt = stmt.where(MediaAsset.source_type == source_type)
        if status:
            stmt = stmt.where(MediaAsset.status == status)
        if search:
            term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    MediaAsset.original_filename.ilike(term),
                    MediaAsset.local_path.ilike(term),
                    MediaAsset.r2_key.ilike(term),
                )
            )
        offset = max(page - 1, 0) * page_size
        stmt = stmt.limit(page_size).offset(offset)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def count_media_assets(
        self,
        *,
        quotation_id: str | None = None,
        source_type: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(MediaAsset)
        if quotation_id:
            stmt = stmt.where(
                or_(
                    MediaAsset.quotation_id == quotation_id,
                    MediaAsset.quotation_id.is_(None),
                )
            )
        if source_type:
            stmt = stmt.where(MediaAsset.source_type == source_type)
        if status:
            stmt = stmt.where(MediaAsset.status == status)
        if search:
            term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    MediaAsset.original_filename.ilike(term),
                    MediaAsset.local_path.ilike(term),
                    MediaAsset.r2_key.ilike(term),
                )
            )
        return int((await self.session.scalar(stmt)) or 0)

    async def upsert_media_selection(
        self,
        *,
        quotation_id: str,
        asset_id: str,
        section_key: str,
        slot_key: str,
        lang: str | None = None,
        display_order: int = 0,
    ) -> MediaSelection:
        stmt = (
            select(MediaSelection)
            .where(MediaSelection.quotation_id == quotation_id)
            .where(MediaSelection.lang == lang)
            .where(MediaSelection.section_key == section_key)
            .where(MediaSelection.slot_key == slot_key)
            .where(MediaSelection.display_order == display_order)
        )
        result = await self.session.execute(stmt)
        selection = result.scalar_one_or_none()
        if selection is None:
            selection = MediaSelection(
                quotation_id=quotation_id,
                asset_id=asset_id,
                lang=lang,
                section_key=section_key,
                slot_key=slot_key,
                display_order=display_order,
            )
            self.session.add(selection)
        else:
            selection.asset_id = asset_id
        await self.session.flush()
        return selection

    async def list_media_selections(
        self,
        *,
        quotation_id: str,
        lang: str | None = None,
        section_key: str | None = None,
        slot_key: str | None = None,
    ) -> list[MediaSelection]:
        stmt: Select[tuple[MediaSelection]] = select(MediaSelection).where(MediaSelection.quotation_id == quotation_id)
        if lang is not None:
            stmt = stmt.where(MediaSelection.lang == lang)
        if section_key is not None:
            stmt = stmt.where(MediaSelection.section_key == section_key)
        if slot_key is not None:
            stmt = stmt.where(MediaSelection.slot_key == slot_key)
        stmt = stmt.order_by(MediaSelection.section_key.asc(), MediaSelection.slot_key.asc(), MediaSelection.display_order.asc())
        result = await self.session.scalars(stmt)
        return list(result.all())
