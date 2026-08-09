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

    async def upsert(self, *, destination_id: str, canonical_name: str, slug: str, aliases: list[str], country_slug: str | None = None, region_slug: str | None = None, province_slug: str | None = None) -> DestinationCatalog:
        item = await self.session.get(DestinationCatalog, destination_id)
        if item is None:
            item = DestinationCatalog(id=destination_id, canonical_name=canonical_name, slug=slug, country_slug=country_slug, region_slug=region_slug, province_slug=province_slug)
            self.session.add(item)
        else:
            item.canonical_name, item.slug, item.is_active = canonical_name, slug, True
            item.country_slug, item.region_slug, item.province_slug = country_slug, region_slug, province_slug
        for alias in {normalize_destination(value) for value in [canonical_name, slug, *aliases] if normalize_destination(value)}:
            existing = await self.session.scalar(select(DestinationAlias).where(DestinationAlias.normalized_alias == alias))
            if existing is None:
                digest = hashlib.sha256(alias.encode("utf-8")).hexdigest()[:20]
                self.session.add(DestinationAlias(id=f"dal_{digest}", destination_id=destination_id, normalized_alias=alias))
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
        return await self.session.scalar(select(DestinationCatalog).join(DestinationAlias).where(DestinationAlias.normalized_alias == normalized, DestinationCatalog.is_active.is_(True)))
