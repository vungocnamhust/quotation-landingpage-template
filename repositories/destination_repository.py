from __future__ import annotations

import hashlib

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.rules.catalog_vocab import DESTINATION_TYPE_RANK
from db.models.destination import DestinationAlias, DestinationCatalog

_MAX_MERGE_CHAIN_DEPTH = 3
_MAX_PARENT_WALK_DEPTH = 6


def normalize_destination(value: str) -> str:
    return " ".join((value or "").casefold().replace("-", " ").split())


class DestinationHierarchyError(ValueError):
    """Parent/child tree invariant violation (maps to 422)."""


class DestinationMergeError(ValueError):
    """Merge precondition violation (maps to 409/422 by the caller)."""


class DestinationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(
        self,
        *,
        destination_id: str,
        canonical_name: str,
        slug: str,
        aliases: list[str],
        country_slug: str | None = None,
        region_slug: str | None = None,
        province_slug: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        media_prefix: str | None = None,
        parent_id: str | None = None,
        destination_type: str | None = None,
        country_code: str | None = None,
        iata_code: str | None = None,
        timezone: str | None = None,
    ) -> DestinationCatalog:
        item = await self.session.get(DestinationCatalog, destination_id)
        if item is None:
            item = DestinationCatalog(
                id=destination_id,
                canonical_name=canonical_name,
                slug=slug,
                country_slug=country_slug,
                region_slug=region_slug,
                province_slug=province_slug,
                latitude=latitude,
                longitude=longitude,
                media_prefix=media_prefix,
                is_active=True,
                parent_id=parent_id,
                **({"destination_type": destination_type} if destination_type is not None else {}),
                country_code=country_code,
                iata_code=iata_code,
                **({"timezone": timezone} if timezone is not None else {}),
            )
            self.session.add(item)

        else:
            # Seed calls are intentionally non-destructive: once an administrator
            # manages a destination, its identity and map anchor remain DB-owned.
            if item.latitude is None and latitude is not None:
                item.latitude = latitude
            if item.longitude is None and longitude is not None:
                item.longitude = longitude
            if item.media_prefix is None and media_prefix is not None:
                item.media_prefix = media_prefix
            if item.parent_id is None and parent_id is not None:
                item.parent_id = parent_id
            if item.country_code is None and country_code is not None:
                item.country_code = country_code
            if item.iata_code is None and iata_code is not None:
                item.iata_code = iata_code
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

    async def create(
        self,
        *,
        destination_id: str,
        canonical_name: str,
        slug: str,
        aliases: list[str],
        country_slug: str | None,
        region_slug: str | None,
        province_slug: str | None,
        latitude: float,
        longitude: float,
        media_prefix: str | None = None,
        parent_id: str | None = None,
        destination_type: str = "city",
        country_code: str | None = None,
        iata_code: str | None = None,
        timezone: str = "Asia/Ho_Chi_Minh",
    ) -> DestinationCatalog:
        item = DestinationCatalog(
            id=destination_id,
            canonical_name=canonical_name,
            slug=slug,
            country_slug=country_slug,
            region_slug=region_slug,
            province_slug=province_slug,
            latitude=latitude,
            longitude=longitude,
            media_prefix=media_prefix,
            is_active=True,
            parent_id=parent_id,
            destination_type=destination_type,
            country_code=country_code,
            iata_code=iata_code,
            timezone=timezone,
        )
        self.session.add(item)
        for alias in {normalize_destination(value) for value in [canonical_name, slug, *aliases] if normalize_destination(value)}:
            digest = hashlib.sha256(alias.encode("utf-8")).hexdigest()[:20]
            self.session.add(DestinationAlias(id=f"dal_{digest}", destination_id=destination_id, normalized_alias=alias))
        await self.session.flush()
        return item

    async def update(
        self,
        item: DestinationCatalog,
        *,
        canonical_name: str,
        aliases: list[str],
        country_slug: str | None,
        region_slug: str | None,
        province_slug: str | None,
        latitude: float,
        longitude: float,
        media_prefix: str | None = None,
        parent_id: str | None = None,
        destination_type: str | None = None,
        country_code: str | None = None,
        iata_code: str | None = None,
        timezone: str | None = None,
    ) -> DestinationCatalog:
        item.canonical_name = canonical_name
        item.country_slug, item.region_slug, item.province_slug = country_slug, region_slug, province_slug
        item.latitude, item.longitude = latitude, longitude
        item.media_prefix = media_prefix
        item.parent_id = parent_id
        if destination_type is not None:
            item.destination_type = destination_type
        item.country_code = country_code
        item.iata_code = iata_code
        if timezone is not None:
            item.timezone = timezone
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

    async def search(
        self,
        query: str = "",
        *,
        active: str = "true",
        country_slug: str | None = None,
        destination_types: list[str] | None = None,
        parent_id: str | None = None,
        limit: int = 20,
    ) -> list[tuple[DestinationCatalog, str | None, bool, str | None]]:
        """Returns (item, matched_alias, is_merge_alias, merge_source_slug) tuples.

        Default ``destination_types=None`` excludes ``country``/``region`` roots so existing
        itinerary dropdowns keep seeing only city-level results (15.2b §3.5).
        """

        def _apply_filters(stmt):
            if active == "true":
                stmt = stmt.where(DestinationCatalog.is_active.is_(True))
            elif active == "false":
                stmt = stmt.where(DestinationCatalog.is_active.is_(False))
            if country_slug:
                stmt = stmt.where(DestinationCatalog.country_slug == country_slug)
            if destination_types is not None:
                stmt = stmt.where(DestinationCatalog.destination_type.in_(destination_types))
            else:
                stmt = stmt.where(DestinationCatalog.destination_type.notin_(["country", "region"]))
            if parent_id is not None:
                stmt = stmt.where(DestinationCatalog.parent_id == parent_id)
            return stmt

        normalized = normalize_destination(query)
        if not normalized:
            stmt = _apply_filters(select(DestinationCatalog))
            stmt = stmt.order_by(DestinationCatalog.canonical_name.asc()).limit(limit)
            rows = (await self.session.scalars(stmt)).all()
            return [(item, None, False, None) for item in rows]

        stmt = select(
            DestinationCatalog,
            DestinationAlias.normalized_alias,
            DestinationAlias.is_merge_alias,
            DestinationAlias.source_slug,
        ).join(DestinationAlias, DestinationAlias.destination_id == DestinationCatalog.id)
        stmt = _apply_filters(stmt)
        stmt = stmt.where(
            or_(
                DestinationCatalog.canonical_name.ilike(f"%{query}%"),
                DestinationAlias.normalized_alias.ilike(f"%{normalized}%"),
            )
        )
        rows = (await self.session.execute(stmt.order_by(DestinationCatalog.canonical_name.asc()).limit(limit))).all()
        return [(row[0], row[1], row[2], row[3]) for row in rows]

    async def effective_destination_id(self, destination_id: str, *, max_depth: int = _MAX_MERGE_CHAIN_DEPTH) -> str:
        """Follows ``merged_into_id`` redirects to the final live destination id (15.4 roll-up)."""
        current_id = destination_id
        for _ in range(max_depth):
            item = await self.session.get(DestinationCatalog, current_id)
            if item is None or item.merged_into_id is None:
                return current_id
            current_id = item.merged_into_id
        return current_id

    async def validate_parent(self, *, parent_id: str | None, destination_type: str, child_id: str | None = None) -> None:
        """Enforces the commercial-tree invariant: parent must outrank child, no cycles, no
        merged rows as parents. Depth-limited walk-up guards against pathological chains."""
        if parent_id is None:
            return
        if parent_id == child_id:
            raise DestinationHierarchyError("A destination cannot be its own parent.")
        parent = await self.session.get(DestinationCatalog, parent_id)
        if parent is None:
            raise DestinationHierarchyError(f"Parent destination '{parent_id}' was not found.")
        if parent.merged_into_id is not None:
            raise DestinationHierarchyError("Parent destination has been merged and cannot be a parent.")
        parent_rank = DESTINATION_TYPE_RANK.get(parent.destination_type, -1)
        child_rank = DESTINATION_TYPE_RANK.get(destination_type, -1)
        if parent_rank <= child_rank:
            raise DestinationHierarchyError(
                f"Parent destination_type '{parent.destination_type}' must outrank "
                f"child destination_type '{destination_type}'."
            )
        current = parent
        for _ in range(_MAX_PARENT_WALK_DEPTH):
            if current.parent_id is None:
                return
            if current.parent_id == child_id:
                raise DestinationHierarchyError("Cycle detected: parent chain loops back to this destination.")
            current = await self.session.get(DestinationCatalog, current.parent_id)
            if current is None:
                return
        raise DestinationHierarchyError("Destination hierarchy exceeds the maximum depth of 6 levels.")

    async def merge(self, *, source_id: str, target_id: str) -> DestinationCatalog:
        """Atomically redirects ``source_id`` into ``target_id`` (15.2b §3.2).

        Never deletes or repoints product/supplier/accommodation FKs — those stay bound to the
        immutable source id forever; callers needing the live id use ``effective_destination_id``.
        """
        if source_id == target_id:
            raise DestinationMergeError("A destination cannot be merged into itself.")
        source = await self.session.get(DestinationCatalog, source_id)
        if source is None:
            raise DestinationMergeError(f"Destination '{source_id}' was not found.")
        target = await self.session.get(DestinationCatalog, target_id)
        if target is None:
            raise DestinationMergeError(f"Target destination '{target_id}' was not found.")
        if source.merged_into_id is not None:
            raise DestinationMergeError(
                f"Destination '{source_id}' has already been merged into '{source.merged_into_id}'."
            )
        if target.merged_into_id is not None:
            raise DestinationMergeError(
                f"Target destination '{target_id}' has itself been merged into '{target.merged_into_id}'."
            )
        if not target.is_active:
            raise DestinationMergeError(f"Target destination '{target_id}' is not active.")

        current_id = target_id
        for _ in range(_MAX_MERGE_CHAIN_DEPTH):
            if current_id == source_id:
                raise DestinationMergeError("Merge would create a cycle between source and target.")
            current = await self.session.get(DestinationCatalog, current_id)
            if current is None or current.merged_into_id is None:
                break
            current_id = current.merged_into_id

        identity_values = {normalize_destination(source.canonical_name), normalize_destination(source.slug)}
        alias_rows = (
            await self.session.scalars(select(DestinationAlias).where(DestinationAlias.destination_id == source_id))
        ).all()
        for alias_row in alias_rows:
            conflict = await self.session.scalar(
                select(DestinationAlias).where(
                    DestinationAlias.normalized_alias == alias_row.normalized_alias,
                    DestinationAlias.destination_id != source_id,
                )
            )
            if conflict is not None:
                continue
            alias_row.destination_id = target_id
            if alias_row.normalized_alias in identity_values:
                alias_row.is_merge_alias = True
                alias_row.source_slug = source.slug
        await self.session.flush()

        for value in (source.canonical_name, source.slug):
            normalized_identity = normalize_destination(value)
            if not normalized_identity:
                continue
            existing = await self.session.scalar(
                select(DestinationAlias).where(DestinationAlias.normalized_alias == normalized_identity)
            )
            if existing is not None:
                continue
            digest = hashlib.sha256(normalized_identity.encode("utf-8")).hexdigest()[:20]
            self.session.add(
                DestinationAlias(
                    id=f"dal_{digest}",
                    destination_id=target_id,
                    normalized_alias=normalized_identity,
                    is_merge_alias=True,
                    source_slug=source.slug,
                )
            )

        source.merged_into_id = target_id
        source.is_active = False
        source.mapping_version = "resolver-v2"
        await self.session.flush()
        return source

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

        # 3. Dynamic Fuzzy & Token-based Substring Matcher over DB Aliases (Layer 3)
        # Enables automatic matching for newly added destinations and aliases without code changes.
        import difflib
        import re
        from core.rules.destination_rules import remove_diacritics

        clean_input = remove_diacritics(value).casefold().strip()
        input_words = re.findall(r"\b\w+\b", clean_input)
        input_text = " ".join(input_words)
        if not input_text:
            return None

        alias_stmt = (
            select(DestinationCatalog, DestinationAlias.normalized_alias)
            .join(DestinationAlias, DestinationAlias.destination_id == DestinationCatalog.id)
            .where(DestinationCatalog.is_active.is_(True))
        )
        alias_rows = (await self.session.execute(alias_stmt)).all()

        best_item: DestinationCatalog | None = None
        best_score = 0.0

        for dest, alias_str in alias_rows:
            clean_alias = remove_diacritics(alias_str).casefold().strip()
            alias_words = re.findall(r"\b\w+\b", clean_alias)
            alias_text = " ".join(alias_words)
            if not alias_text:
                continue

            # Check 3.1: Multi-word / single significant word containment in input
            alias_regex = r"\b" + re.escape(alias_text) + r"\b"
            if re.search(alias_regex, input_text):
                containment_score = 0.85 + min(0.14, len(alias_words) * 0.05)
                if containment_score > best_score:
                    best_score = containment_score
                    best_item = dest
                continue

            # Check 3.2: Reverse containment (input is a sub-phrase of alias)
            if len(input_words) >= 2 and re.search(r"\b" + re.escape(input_text) + r"\b", alias_text):
                containment_score = 0.82 + min(0.10, len(input_words) * 0.04)
                if containment_score > best_score:
                    best_score = containment_score
                    best_item = dest
                continue

            # Check 3.3: SequenceMatcher ratio
            ratio = difflib.SequenceMatcher(None, input_text, alias_text).ratio()
            if ratio >= 0.80 and ratio > best_score:
                best_score = ratio
                best_item = dest

        if best_item is not None and best_score >= 0.80:
            return best_item

        return None


async def seed_destination_catalog(session: AsyncSession) -> None:
    from destination_catalog_seed import COUNTRY_PARENT_PROFILES, get_seed_destination_profiles

    repository = DestinationRepository(session)
    for parent in COUNTRY_PARENT_PROFILES:
        await repository.upsert(
            destination_id=parent["id"],
            canonical_name=parent["canonical_name"],
            slug=parent["slug"],
            aliases=[],
            country_slug=parent["country_slug"],
            latitude=parent["latitude"],
            longitude=parent["longitude"],
            destination_type=parent["destination_type"],
            country_code=parent["country_code"],
            timezone=parent["timezone"],
        )
    for profile in get_seed_destination_profiles():
        await repository.upsert(
            destination_id=f"dst_{profile['slug']}",
            canonical_name=profile["canonical_name"],
            slug=profile["slug"],
            aliases=profile["aliases"],
            country_slug=profile["country_slug"],
            region_slug=profile["region_slug"],
            province_slug=profile["province_slug"],
            latitude=profile["latitude"],
            longitude=profile["longitude"],
            parent_id=profile.get("parent_id"),
            timezone=profile.get("timezone"),
        )

