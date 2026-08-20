from __future__ import annotations

import hashlib

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.destination import DestinationAlias, DestinationCatalog


def normalize_destination(value: str) -> str:
    return " ".join((value or "").casefold().replace("-", " ").split())


class DestinationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(self, *, destination_id: str, canonical_name: str, slug: str, aliases: list[str], country_slug: str | None = None, region_slug: str | None = None, province_slug: str | None = None, latitude: float | None = None, longitude: float | None = None) -> DestinationCatalog:
        item = await self.session.get(DestinationCatalog, destination_id)
        if item is None:
            item = DestinationCatalog(id=destination_id, canonical_name=canonical_name, slug=slug, country_slug=country_slug, region_slug=region_slug, province_slug=province_slug, latitude=latitude, longitude=longitude)
            self.session.add(item)
        else:
            # Seed calls are intentionally non-destructive: once an administrator
            # manages a destination, its identity and map anchor remain DB-owned.
            if item.latitude is None and latitude is not None:
                item.latitude = latitude
            if item.longitude is None and longitude is not None:
                item.longitude = longitude
        for alias in {normalize_destination(value) for value in [canonical_name, slug, *aliases] if normalize_destination(value)}:
            existing = await self.session.scalar(select(DestinationAlias).where(DestinationAlias.normalized_alias == alias))
            if existing is None:
                digest = hashlib.sha256(alias.encode("utf-8")).hexdigest()[:20]
                self.session.add(DestinationAlias(id=f"dal_{digest}", destination_id=destination_id, normalized_alias=alias))
        await self.session.flush()
        return item

    async def get(self, destination_id: str) -> DestinationCatalog | None:
        return await self.session.get(DestinationCatalog, destination_id)

    async def aliases_for(self, destination_id: str) -> list[str]:
        rows = await self.session.scalars(
            select(DestinationAlias.normalized_alias)
            .where(DestinationAlias.destination_id == destination_id)
            .order_by(DestinationAlias.normalized_alias.asc())
        )
        return list(rows)

    async def conflicting_alias(self, values: list[str], *, destination_id: str | None = None) -> str | None:
        for value in {normalize_destination(item) for item in values if normalize_destination(item)}:
            existing = await self.session.scalar(
                select(DestinationAlias).where(DestinationAlias.normalized_alias == value)
            )
            if existing is not None and existing.destination_id != destination_id:
                return value
        return None

    async def create(self, *, destination_id: str, canonical_name: str, slug: str, aliases: list[str], country_slug: str | None, region_slug: str | None, province_slug: str | None, latitude: float, longitude: float) -> DestinationCatalog:
        item = DestinationCatalog(id=destination_id, canonical_name=canonical_name, slug=slug, country_slug=country_slug, region_slug=region_slug, province_slug=province_slug, latitude=latitude, longitude=longitude, is_active=True)
        self.session.add(item)
        for alias in {normalize_destination(value) for value in [canonical_name, slug, *aliases] if normalize_destination(value)}:
            digest = hashlib.sha256(alias.encode("utf-8")).hexdigest()[:20]
            self.session.add(DestinationAlias(id=f"dal_{digest}", destination_id=destination_id, normalized_alias=alias))
        await self.session.flush()
        return item

    async def update(self, item: DestinationCatalog, *, canonical_name: str, aliases: list[str], country_slug: str | None, region_slug: str | None, province_slug: str | None, latitude: float, longitude: float) -> DestinationCatalog:
        item.canonical_name = canonical_name
        item.country_slug, item.region_slug, item.province_slug = country_slug, region_slug, province_slug
        item.latitude, item.longitude = latitude, longitude
        for alias in {normalize_destination(value) for value in [canonical_name, item.slug, *aliases] if normalize_destination(value)}:
            existing = await self.session.scalar(select(DestinationAlias).where(DestinationAlias.normalized_alias == alias))
            if existing is None:
                digest = hashlib.sha256(alias.encode("utf-8")).hexdigest()[:20]
                self.session.add(DestinationAlias(id=f"dal_{digest}", destination_id=item.id, normalized_alias=alias))
        await self.session.flush()
        return item

    async def set_status(self, item: DestinationCatalog, *, is_active: bool) -> DestinationCatalog:
        item.is_active = is_active
        await self.session.flush()
        return item

    async def search(self, query: str, *, limit: int = 20) -> list[tuple[DestinationCatalog, str]]:
        normalized = normalize_destination(query)
        stmt = select(DestinationCatalog, DestinationAlias.normalized_alias).join(DestinationAlias, DestinationAlias.destination_id == DestinationCatalog.id).where(DestinationCatalog.is_active.is_(True))
        if normalized:
            stmt = stmt.where(or_(DestinationCatalog.canonical_name.ilike(f"%{query}%"), DestinationAlias.normalized_alias.ilike(f"%{normalized}%")))
        rows = (await self.session.execute(stmt.order_by(DestinationCatalog.canonical_name.asc()).limit(limit))).all()
        return [(row[0], row[1]) for row in rows]

    async def resolve(self, value: str) -> DestinationCatalog | None:
        normalized = normalize_destination(value)
        if not normalized:
            return None

        # 1. Exact alias match in DB (fast index lookup)
        stmt = (
            select(DestinationCatalog)
            .join(DestinationAlias, DestinationAlias.destination_id == DestinationCatalog.id)
            .where(DestinationAlias.normalized_alias == normalized, DestinationCatalog.is_active.is_(True))
        )
        item = await self.session.scalar(stmt)
        if item is not None:
            return item

        # 2. Fallback to deterministic pure-domain matcher (core.rules.destination_rules)
        from core.rules.destination_rules import match_destination_slug

        matched_slug = match_destination_slug(value)
        if matched_slug:
            fallback_stmt = (
                select(DestinationCatalog).where(
                    or_(
                        DestinationCatalog.slug == matched_slug,
                        DestinationCatalog.province_slug == matched_slug,
                    ),
                    DestinationCatalog.is_active.is_(True),
                )
            )
            item = await self.session.scalar(fallback_stmt)
            if item is not None:
                return item

        return None
