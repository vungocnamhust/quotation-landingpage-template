"""Deterministic canonical defaults for V2 brochure media.

This deliberately consumes the indexed R2 catalogue, never a local assets
directory. The resolver is pure after catalogue loading so dry-runs and apply
produce exactly the same patch for a given quotation/version/catalogue.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Iterable

from core.rules.destination_rules import (
    COUNTRY_GATEWAY_MAP,
    DESTINATION_KEYWORD_MAP,
    VALID_DESTINATION_SLUGS,
    match_destination_slug,
)
from core.rules.media_classification import classify_media_asset
from core.rules.r2_paths import accommodation_slug_segment


RESOLVER_VERSION = "brochure-media-v3"
GALLERY_LIMIT = 3

_NON_ALPHANUM = re.compile(r"[^a-z0-9]+")
_HOTEL_STOP_WORDS = {
    "hotel", "resort", "spa", "and", "the", "grand", "luxury", "villas", "villas-and-spa",
    "suites", "palace", "international", "khach", "san", "khach-san", "vietnam", "residence",
    "boutique", "lodge", "retreat", "an", "a", "of", "in", "by", "premium", "collection",
}


@dataclass(frozen=True)
class Candidate:
    r2_key: str
    parent_prefix: str
    width: int | None = None
    height: int | None = None
    preview_ready: bool = False
    source: str = "auto"
    review_required: bool = False

    @property
    def classification(self) -> str:
        return classify_media_asset(self.parent_prefix, self.r2_key.rsplit("/", 1)[-1])

    @property
    def landscape(self) -> bool:
        return self.width is None or self.height is None or self.width >= self.height


def remove_diacritics(text: str) -> str:
    """Normalize and strip Vietnamese / international diacritics."""
    if not text:
        return ""
    text = text.replace("đ", "d").replace("Đ", "d")
    normalized = unicodedata.normalize("NFD", text)
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")


def destination_aliases(destination_ref: Any, fallback_ref: Any = None) -> set[str]:
    """Extract all possible normalized alias tokens for matching against R2 parent prefixes."""
    destination = _record(destination_ref)
    fallback = _record(fallback_ref)

    aliases: set[str] = set()

    # 1. Raw fields inspection
    for field in ("id", "destinationId", "slug", "name", "segmentCity", "destination", "city", "overnight", "media_prefix", "mediaPrefix", "defaultMediaPrefix"):
        val = str(destination.get(field) or fallback.get(field) or "").strip()
        if not val or val.startswith(("day-", "hotel-", "stay-")):
            continue
        cleaned = val.casefold()
        aliases.add(cleaned)
        aliases.add(_NON_ALPHANUM.sub("-", cleaned).strip("-"))
        aliases.add(_NON_ALPHANUM.sub("", cleaned))

        no_accent = remove_diacritics(cleaned)
        aliases.add(no_accent)
        aliases.add(_NON_ALPHANUM.sub("-", no_accent).strip("-"))
        aliases.add(_NON_ALPHANUM.sub("", no_accent))

        # Extract individual path segments if value is a folder path
        if "/" in val:
            for sub_segment in val.split("/"):
                sub_clean = sub_segment.strip().casefold()
                if len(sub_clean) >= 2 and sub_clean not in ("destination", "accommodations", "vietnam", "thailand", "cambodia", "laos"):
                    aliases.add(sub_clean)
                    aliases.add(_NON_ALPHANUM.sub("-", sub_clean).strip("-"))
                    aliases.add(_NON_ALPHANUM.sub("", sub_clean))
                    no_accent_sub = remove_diacritics(sub_clean)
                    aliases.add(no_accent_sub)
                    aliases.add(_NON_ALPHANUM.sub("-", no_accent_sub).strip("-"))
                    aliases.add(_NON_ALPHANUM.sub("", no_accent_sub))

        # Match using domain rules
        matched_slug = match_destination_slug(val)
        if matched_slug:
            aliases.add(matched_slug)
            aliases.add(matched_slug.replace("-", ""))

    # 1.1 List aliases inspection
    for key in ("aliases", "searchAliases"):
        raw_list = destination.get(key) or fallback.get(key)
        if isinstance(raw_list, (list, tuple, set)):
            for item in raw_list:
                if isinstance(item, str) and item.strip():
                    item_clean = item.strip().casefold()
                    aliases.add(item_clean)
                    aliases.add(_NON_ALPHANUM.sub("-", item_clean).strip("-"))
                    no_accent_item = remove_diacritics(item_clean)
                    aliases.add(no_accent_item)
                    aliases.add(_NON_ALPHANUM.sub("-", no_accent_item).strip("-"))

    # 2. Enrich with all aliases from DESTINATION_KEYWORD_MAP
    matched_slugs = {a for a in aliases if a in VALID_DESTINATION_SLUGS}
    for kw, target_slug in DESTINATION_KEYWORD_MAP.items():
        if target_slug in matched_slugs or kw in aliases:
            aliases.add(target_slug)
            aliases.add(target_slug.replace("-", ""))
            kw_no_accent = remove_diacritics(kw)
            aliases.add(kw_no_accent)
            aliases.add(_NON_ALPHANUM.sub("-", kw_no_accent).strip("-"))
            aliases.add(_NON_ALPHANUM.sub("", kw_no_accent))

    return {a for a in aliases if len(a) >= 2}


def accommodation_distinct_tokens(name: str | None) -> set[str]:
    """Extract distinctive brand/name tokens from hotel name."""
    if not name:
        return set()
    cleaned = remove_diacritics(name.casefold())
    tokens = {t for t in _NON_ALPHANUM.split(cleaned) if len(t) >= 3 and t not in _HOTEL_STOP_WORDS}
    token_list = [t for t in _NON_ALPHANUM.split(cleaned) if len(t) >= 3 and t not in _HOTEL_STOP_WORDS]
    if len(token_list) >= 2:
        tokens.add("-".join(token_list))
        tokens.add("".join(token_list))
    return tokens


def _matches_destination(candidate: Candidate, aliases: set[str]) -> bool:
    if not aliases:
        return False
    path_norm = remove_diacritics(f"{candidate.parent_prefix}/{candidate.r2_key}".casefold())
    segments = [s for s in _NON_ALPHANUM.split(path_norm) if s]
    compact_path = "".join(segments)

    for alias in aliases:
        alias_clean = alias.strip("-")
        alias_compact = alias_clean.replace("-", "")
        if alias_clean in segments or alias_compact in segments:
            return True
        if f"/{alias_clean}" in path_norm or f"/{alias_compact}" in path_norm or f"-{alias_clean}" in path_norm:
            return True
        if f"{alias_clean}/" in path_norm or f"{alias_compact}/" in path_norm:
            return True
        if alias_compact and alias_compact in compact_path and len(alias_compact) >= 4:
            return True
    return False


def _matches_accommodation(candidate: Candidate, hotel_tokens: set[str], dest_aliases: set[str]) -> tuple[bool, int]:
    """Returns (is_match, tier) where tier 1 is exact hotel, tier 2 is dest accommodation, tier 3 is dest scenic."""
    path_norm = remove_diacritics(f"{candidate.parent_prefix}/{candidate.r2_key}".casefold())
    path_segments = [s for s in path_norm.split("/") if s]
    segments = [s for s in _NON_ALPHANUM.split(path_norm) if s]

    if "accommodations" in segments:
        # Index-aware (R3): a hotel-name token only proves tier-1 identity
        # when it appears in the {hotel-slug} segment itself. Matching it
        # anywhere in the flattened path (the old behavior) let the shared
        # {province} segment — present for every hotel in that city — cause
        # every hotel's images to collide with every other hotel's search.
        hotel_segment = accommodation_slug_segment(path_segments)
        if hotel_segment:
            hotel_segment_tokens = {t for t in _NON_ALPHANUM.split(hotel_segment) if t}
            compact_segment = hotel_segment.replace("-", "")
            # A token shared with the destination (the city name is
            # routinely suffixed onto every hotel slug in that city, e.g.
            # `metropole-hanoi` / `lotte-hanoi`) is not hotel-distinctive by
            # itself; require an actual hotel-name token unless the hotel
            # name is nothing but the destination name.
            distinctive_tokens = {t for t in hotel_tokens if t not in dest_aliases} or hotel_tokens
            for token in distinctive_tokens:
                if token in hotel_segment_tokens or token == hotel_segment or (len(token) >= 4 and token in compact_segment):
                    return True, 1
        if _matches_destination(candidate, dest_aliases):
            return True, 2

    if _matches_destination(candidate, dest_aliases):
        return True, 3

    return False, 4


def _record(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _assets(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else []


def _r2(value: Any) -> str:
    return str(_record(value).get("r2Key") or "").strip()


def _stable_rank(quotation_id: str, lang: str, field_id: str, key: str) -> int:
    return int(hashlib.sha256(f"{RESOLVER_VERSION}:{quotation_id}:{lang}:{field_id}:{key}".encode()).hexdigest(), 16)


def _ref(candidate: Candidate) -> dict[str, str]:
    result = {
        "r2Key": candidate.r2_key,
        "status": "review_required" if candidate.review_required else "ready",
        "source": candidate.source,
        "resolverVersion": RESOLVER_VERSION,
    }
    return result


class BrochureMediaResolver:
    def __init__(self, candidates: Iterable[Candidate]) -> None:
        # The resolver is catalogue-only: review-required placeholders and
        # brand-local files are not eligible photography candidates.
        self.candidates = tuple(
            candidate
            for candidate in candidates
            if candidate.r2_key and not candidate.review_required
        )
        self.catalogue_candidates = self.candidates
        self.valid_keys = {c.r2_key for c in self.candidates}

    def _is_valid_r2(self, value: Any) -> bool:
        key = _r2(value)
        return bool(key and key in self.valid_keys)

    @staticmethod
    def _has_assigned_r2(value: Any) -> bool:
        """A staff-selected Fact asset remains authoritative even if the
        catalogue is stale or has not indexed that object yet."""
        return bool(_r2(value))

    def _pick(
        self,
        *,
        quotation_id: str,
        lang: str,
        field_id: str,
        pool: Iterable[Candidate],
        preferred: tuple[str, ...] = (),
        excluded: set[str] | None = None,
        limit: int = 1,
    ) -> list[Candidate]:
        excluded = excluded or set()
        unique = {item.r2_key: item for item in pool if item.r2_key not in excluded}
        if not unique and excluded:
            # If all pool candidates were in excluded set, allow reusing pool if limit requires
            unique = {item.r2_key: item for item in pool}

        def score(item: Candidate) -> tuple[int, int, int, int]:
            return (
                0 if item.classification in preferred else 1,
                0 if item.landscape else 1,
                0 if item.preview_ready else 1,
                _stable_rank(quotation_id, lang, field_id, item.r2_key),
            )
        return sorted(unique.values(), key=score)[:limit]

    def _destination_pool(self, primary_aliases: set[str], fallback_aliases: set[str] | None = None) -> list[Candidate]:
        # Tier 1: Match primary destination aliases
        tier1 = [item for item in self.catalogue_candidates if _matches_destination(item, primary_aliases)]
        if tier1:
            return tier1
        # Tier 2: Match another destination already present in the trip.
        if fallback_aliases:
            tier2 = [item for item in self.catalogue_candidates if _matches_destination(item, fallback_aliases)]
            if tier2:
                return tier2
        # Tier 3: All scenic / generic candidates
        return list(self.catalogue_candidates)

    def _accommodation_pool(self, hotel_tokens: set[str], dest_aliases: set[str], fallback_aliases: set[str] | None = None) -> list[Candidate]:
        # Tier 1: Exact hotel brand/name token match under accommodations/
        tier1 = [item for item in self.catalogue_candidates if _matches_accommodation(item, hotel_tokens, dest_aliases)[1] == 1]
        if tier1:
            return tier1
        # Tier 2: Destination accommodation match
        tier2 = [item for item in self.catalogue_candidates if _matches_accommodation(item, hotel_tokens, dest_aliases)[1] == 2]
        if tier2:
            return tier2
        # Tier 3: Destination scenic match
        tier3 = [item for item in self.catalogue_candidates if _matches_accommodation(item, hotel_tokens, dest_aliases)[1] == 3]
        if tier3:
            return tier3
        # Tier 4: Another destination already present in the trip.
        if fallback_aliases:
            tier4 = [item for item in self.catalogue_candidates if _matches_destination(item, fallback_aliases)]
            if tier4:
                return tier4
        # Tier 5: All candidates
        return list(self.catalogue_candidates)

    def resolve_missing(self, *, document: dict[str, Any], quotation_id: str, lang: str) -> dict[str, Any]:
        """Build a non-mutating patch. Existing values are never overwritten unless invalid."""
        assets_patch: dict[str, Any] = {}
        itinerary_patch: dict[str, Any] = {}
        stays_patch: dict[str, Any] = {}
        rationale: list[dict[str, Any]] = []
        used_covers: set[str] = set()

        assets = _record(document.get("assets"))
        for name in ("hero", "itineraryDivider", "staysDivider", "hotelDivider"):
            if self._has_assigned_r2(assets.get(name)):
                used_covers.add(_r2(assets.get(name)))

        days = _assets(_record(document.get("itinerary")).get("days"))
        hotels = _assets(_record(document.get("stays")).get("hotels"))

        # Pre-collect trip destinations as secondary catalogue-match aliases.
        trip_dest_aliases: set[str] = set()
        for day in days:
            trip_dest_aliases.update(destination_aliases(_record(day).get("destinationRef"), fallback_ref=day))
        for hotel in hotels:
            trip_dest_aliases.update(destination_aliases(_record(hotel).get("destinationRef"), fallback_ref=hotel))

        patched_days: dict[int, dict[str, Any]] = {}
        gallery_candidates: list[Candidate] = []

        # 1. Resolve Day Galleries — top-up preserving order (D5). A day that
        # already carries 1-2 images is never wiped to fill it; it is only
        # ever topped up to GALLERY_LIMIT, and existing refs (manual or auto)
        # keep both their position and their original payload untouched.
        for index, day in enumerate(days):
            images = _record(_record(day).get("images"))
            existing_assets = [asset for asset in _assets(images.get("carousel")) if self._has_assigned_r2(asset)]
            existing_candidates = [Candidate(_r2(asset), "", None, None, True) for asset in existing_assets]
            gallery_candidates.extend(existing_candidates)

            if len(existing_assets) >= GALLERY_LIMIT:
                continue

            field_id = f"itinerary.days.{index}.gallery"
            day_aliases = destination_aliases(_record(day).get("destinationRef"), fallback_ref=day)
            pool = self._destination_pool(day_aliases, fallback_aliases=trip_dest_aliases)
            needed = GALLERY_LIMIT - len(existing_assets)
            existing_keys = {candidate.r2_key for candidate in existing_candidates}
            picks = self._pick(
                quotation_id=quotation_id,
                lang=lang,
                field_id=field_id,
                pool=pool,
                preferred=("hero", "generic"),
                excluded=existing_keys,
                limit=needed,
            )
            if picks:
                patched_days[index] = {"images": {"carousel": [*existing_assets, *[_ref(item) for item in picks]]}}
                gallery_candidates.extend(picks)
                rationale.append({
                    "fieldId": field_id,
                    "candidateCount": len(pool),
                    "reason": (
                        "insufficient_catalogue_media"
                        if len(existing_assets) + len(picks) < GALLERY_LIMIT
                        else "destination catalogue" if any(_matches_destination(p, day_aliases) for p in picks) else "trip catalogue"
                    ),
                })

        if patched_days:
            itinerary_patch["days"] = patched_days

        # 2. Resolve assets.hero
        if not self._has_assigned_r2(assets.get("hero")):
            first_day_aliases = destination_aliases(_record(days[0]).get("destinationRef"), fallback_ref=days[0]) if days else trip_dest_aliases
            hero_pool = (
                self._destination_pool(first_day_aliases, fallback_aliases=trip_dest_aliases)
                or gallery_candidates
                or list(self.candidates)
            )
            picks = self._pick(
                quotation_id=quotation_id,
                lang=lang,
                field_id="assets.hero",
                pool=hero_pool,
                preferred=("hero", "generic"),
                excluded=used_covers,
            )
            if picks:
                assets_patch["hero"] = _ref(picks[0])
                used_covers.add(picks[0].r2_key)
                rationale.append({
                    "fieldId": "assets.hero",
                    "candidateCount": len(hero_pool),
                    "reason": "itinerary gallery pool" if picks[0] in gallery_candidates else "destination hero candidate",
                })

        # 3. Resolve assets.itineraryDivider
        if not self._has_assigned_r2(assets.get("itineraryDivider")):
            mid_index = len(days) // 2 if days else 0
            mid_day_aliases = destination_aliases(_record(days[mid_index]).get("destinationRef"), fallback_ref=days[mid_index]) if days else trip_dest_aliases
            divider_pool = (
                self._destination_pool(mid_day_aliases, fallback_aliases=trip_dest_aliases)
                or gallery_candidates
                or list(self.candidates)
            )
            picks = self._pick(
                quotation_id=quotation_id,
                lang=lang,
                field_id="assets.itineraryDivider",
                pool=divider_pool,
                preferred=("generic", "hero"),
                excluded=used_covers,
            )
            if picks:
                assets_patch["itineraryDivider"] = _ref(picks[0])
                used_covers.add(picks[0].r2_key)
                rationale.append({
                    "fieldId": "assets.itineraryDivider",
                    "candidateCount": len(divider_pool),
                    "reason": "mid-itinerary scenic asset",
                })

        first_hotel_aliases = (
            destination_aliases(_record(hotels[0]).get("destinationRef"), fallback_ref=hotels[0])
            if hotels
            else trip_dest_aliases
        )

        # 4. Resolve assets.staysDivider
        if not self._has_assigned_r2(assets.get("staysDivider")):
            stays_pool = (
                self._destination_pool(first_hotel_aliases, fallback_aliases=trip_dest_aliases)
                or gallery_candidates
                or list(self.candidates)
            )
            picks = self._pick(
                quotation_id=quotation_id,
                lang=lang,
                field_id="assets.staysDivider",
                pool=stays_pool,
                preferred=("interior", "exterior", "generic"),
                excluded=used_covers,
            )
            if picks:
                assets_patch["staysDivider"] = _ref(picks[0])
                used_covers.add(picks[0].r2_key)
                rationale.append({
                    "fieldId": "assets.staysDivider",
                    "candidateCount": len(stays_pool),
                    "reason": "stay scenic asset",
                })

        # 5. Resolve assets.hotelDivider
        if not self._has_assigned_r2(assets.get("hotelDivider")):
            hotel_divider_pool = (
                self._destination_pool(first_hotel_aliases, fallback_aliases=trip_dest_aliases)
                or gallery_candidates
                or list(self.candidates)
            )
            picks = self._pick(
                quotation_id=quotation_id,
                lang=lang,
                field_id="assets.hotelDivider",
                pool=hotel_divider_pool,
                preferred=("exterior", "interior", "generic"),
                excluded=used_covers,
            )
            if picks:
                assets_patch["hotelDivider"] = _ref(picks[0])
                used_covers.add(picks[0].r2_key)
                rationale.append({
                    "fieldId": "assets.hotelDivider",
                    "candidateCount": len(hotel_divider_pool),
                    "reason": "hotel scenic asset",
                })

        # 6. Resolve Stays Hotels
        patched_hotels: dict[int, dict[str, Any]] = {}
        for index, hotel in enumerate(hotels):
            hotel_rec = _record(hotel)
            hotel_changes: dict[str, Any] = {}
            hotel_name = hotel_rec.get("name")
            hotel_dest_aliases = destination_aliases(hotel_rec.get("destinationRef"), fallback_ref=hotel_rec) or trip_dest_aliases
            hotel_tokens = accommodation_distinct_tokens(hotel_name)

            hotel_pool = self._accommodation_pool(hotel_tokens, hotel_dest_aliases, fallback_aliases=trip_dest_aliases)

            if not self._has_assigned_r2(hotel_rec.get("hotelImage")):
                picks = self._pick(
                    quotation_id=quotation_id,
                    lang=lang,
                    field_id=f"stays.hotels.{index}.hotelImage",
                    pool=hotel_pool,
                    preferred=("exterior", "generic"),
                )
                if picks:
                    hotel_changes["hotelImage"] = _ref(picks[0])

            if not self._has_assigned_r2(hotel_rec.get("roomImage")):
                picked_keys = {hotel_changes["hotelImage"]["r2Key"]} if "hotelImage" in hotel_changes else set()
                picks = self._pick(
                    quotation_id=quotation_id,
                    lang=lang,
                    field_id=f"stays.hotels.{index}.roomImage",
                    pool=hotel_pool,
                    preferred=("interior", "generic"),
                    excluded=picked_keys,
                )
                if picks:
                    hotel_changes["roomImage"] = _ref(picks[0])

            if hotel_changes:
                patched_hotels[index] = hotel_changes
                for field in hotel_changes:
                    rationale.append({
                        "fieldId": f"stays.hotels.{index}.{field}",
                        "candidateCount": len(hotel_pool),
                        "reason": "accommodation catalogue" if any("accommodations" in p.parent_prefix for p in hotel_pool) else "trip catalogue",
                    })

        if patched_hotels:
            stays_patch["hotels"] = patched_hotels

        has_changes = bool(assets_patch or patched_days or patched_hotels)
        patch = {
            "assets": assets_patch,
            "itinerary": itinerary_patch,
            "stays": stays_patch,
        }

        applied_count = (
            len(assets_patch)
            + sum(len(d.get("images", {}).get("carousel", [])) for d in patched_days.values())
            + sum(len(h) for h in patched_hotels.values())
        )

        return {
            "resolverVersion": RESOLVER_VERSION,
            "patch": patch,
            "rationale": rationale,
            "appliedCount": applied_count,
            "hasChanges": has_changes,
        }
