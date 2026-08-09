"""Deterministic canonical defaults for V2 brochure media.

This deliberately consumes the indexed R2 catalogue, never a local assets
directory.  The resolver is pure after catalogue loading so dry-runs and apply
produce exactly the same patch for a given quotation/version/catalogue.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Iterable


RESOLVER_VERSION = "brochure-media-v1"
GALLERY_LIMIT = 3


@dataclass(frozen=True)
class Candidate:
    r2_key: str
    parent_prefix: str
    width: int | None = None
    height: int | None = None
    preview_ready: bool = False

    @property
    def classification(self) -> str:
        value = f"{self.parent_prefix}/{self.r2_key.rsplit('/', 1)[-1]}".lower()
        for tag in ("exterior", "interior", "room", "hero", "ornament"):
            if tag in value:
                return tag
        return "generic"

    @property
    def landscape(self) -> bool:
        return self.width is None or self.height is None or self.width >= self.height


def _record(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _assets(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else []


def _r2(value: Any) -> str:
    return str(_record(value).get("r2Key") or "").strip()


def _stable_rank(quotation_id: str, lang: str, field_id: str, key: str) -> int:
    return int(hashlib.sha256(f"{RESOLVER_VERSION}:{quotation_id}:{lang}:{field_id}:{key}".encode()).hexdigest(), 16)


def _ref(candidate: Candidate) -> dict[str, str]:
    return {"r2Key": candidate.r2_key, "status": "ready", "source": "auto", "resolverVersion": RESOLVER_VERSION}


class BrochureMediaResolver:
    def __init__(self, candidates: Iterable[Candidate]) -> None:
        self.candidates = tuple(candidate for candidate in candidates if candidate.r2_key)
        self.valid_keys = {c.r2_key for c in self.candidates}

    def _is_valid_r2(self, value: Any) -> bool:
        key = _r2(value)
        return bool(key and key in self.valid_keys)

    @staticmethod
    def _has_assigned_r2(value: Any) -> bool:
        """A staff-selected Fact asset remains authoritative even if the
        catalogue is stale or has not indexed that object yet."""
        return bool(_r2(value))

    def _pick(self, *, quotation_id: str, lang: str, field_id: str, pool: Iterable[Candidate], preferred: tuple[str, ...] = (), excluded: set[str] | None = None, limit: int = 1) -> list[Candidate]:
        excluded = excluded or set()
        unique = {item.r2_key: item for item in pool if item.r2_key not in excluded}
        def score(item: Candidate) -> tuple[int, int, int, int]:
            return (
                0 if item.classification in preferred else 1,
                0 if item.landscape else 1,
                0 if item.preview_ready else 1,
                _stable_rank(quotation_id, lang, field_id, item.r2_key),
            )
        return sorted(unique.values(), key=score)[:limit]

    def _destination_pool(self, destination_ref: Any, fallback_ref: Any = None) -> list[Candidate]:
        destination = _record(destination_ref)
        fallback = _record(fallback_ref)
        destination_id = str(destination.get("id") or destination.get("destinationId") or fallback.get("destinationId") or "")
        if destination_id.startswith(("day-", "hotel-", "stay-")):
            destination_id = ""
        slug = str(destination.get("slug") or fallback.get("slug") or "")
        if not slug and not destination_id:
            name = str(destination.get("name") or destination.get("segmentCity") or destination.get("destination") or fallback.get("name") or fallback.get("segmentCity") or fallback.get("destination") or fallback.get("city") or "")
            if name:
                slug = "-".join(name.casefold().split())
        return [item for item in self.candidates if (destination_id and destination_id in item.parent_prefix) or (slug and f"/{slug}" in item.parent_prefix)]

    def _accommodation_pool(self, destination_ref: Any, name: Any) -> list[Candidate]:
        slug = "-".join(str(name or "").casefold().split())
        destination = _record(destination_ref)
        destination_slug = str(destination.get("slug") or "")
        return [item for item in self.candidates if "accommodations/" in item.parent_prefix and (not slug or slug in item.parent_prefix) and (not destination_slug or destination_slug in item.parent_prefix)]

    def resolve_missing(self, *, document: dict[str, Any], quotation_id: str, lang: str) -> dict[str, Any]:
        """Build a non-mutating patch. Existing values are never overwritten unless invalid."""
        patch: dict[str, Any] = {"assets": {}, "itinerary": {}, "stays": {}}
        rationale: list[dict[str, Any]] = []
        used_covers: set[str] = set()
        assets = _record(document.get("assets"))
        for name in ("hero", "itineraryDivider", "hotelDivider"):
            if self._has_assigned_r2(assets.get(name)):
                used_covers.add(_r2(assets.get(name)))
        days = _assets(_record(document.get("itinerary")).get("days"))
        patched_days: dict[int, dict[str, Any]] = {}
        gallery_candidates: list[Candidate] = []
        for index, day in enumerate(days):
            images = _record(_record(day).get("images"))
            carousel_assets = [Candidate(_r2(asset), "", None, None, True) for asset in _assets(images.get("carousel")) if self._has_assigned_r2(asset)]
            if carousel_assets:
                gallery_candidates.extend(carousel_assets)
                continue
            field_id = f"itinerary.days.{index}.gallery"
            pool = self._destination_pool(_record(day).get("destinationRef"), fallback_ref=day)
            picks = self._pick(quotation_id=quotation_id, lang=lang, field_id=field_id, pool=pool, preferred=("hero", "generic"), limit=GALLERY_LIMIT)
            if picks:
                patched_days[index] = {"images": {"carousel": [_ref(item) for item in picks]}}
                gallery_candidates.extend(picks)
                rationale.append({"fieldId": field_id, "candidateCount": len(pool), "reason": "exact destination catalogue"})
        if patched_days:
            patch["itinerary"]["days"] = patched_days
        if not self._has_assigned_r2(assets.get("hero")):
            pool = gallery_candidates or (self._destination_pool(_record(days[0]).get("destinationRef"), fallback_ref=days[0]) if days else [])
            picks = self._pick(quotation_id=quotation_id, lang=lang, field_id="assets.hero", pool=pool, preferred=("hero",), excluded=used_covers)
            if picks:
                patch["assets"]["hero"] = _ref(picks[0]); used_covers.add(picks[0].r2_key)
                rationale.append({"fieldId": "assets.hero", "candidateCount": len(pool), "reason": "itinerary gallery pool"})
        for field_id, asset_name, day_index in (("assets.itineraryDivider", "itineraryDivider", len(days) // 2), ("assets.hotelDivider", "hotelDivider", 0)):
            if self._has_assigned_r2(assets.get(asset_name)):
                continue
            pool = self._destination_pool(_record(days[day_index]).get("destinationRef"), fallback_ref=days[day_index]) if days else gallery_candidates
            picks = self._pick(quotation_id=quotation_id, lang=lang, field_id=field_id, pool=pool, excluded=used_covers)
            if picks:
                patch["assets"][asset_name] = _ref(picks[0]); used_covers.add(picks[0].r2_key)
                rationale.append({"fieldId": field_id, "candidateCount": len(pool), "reason": "unused destination asset"})
        hotels = _assets(_record(document.get("stays")).get("hotels"))
        patched_hotels: dict[int, dict[str, Any]] = {}
        for index, hotel in enumerate(hotels):
            hotel = _record(hotel); changes: dict[str, Any] = {}
            exact = self._accommodation_pool(hotel.get("destinationRef"), hotel.get("name"))
            destination = self._destination_pool(hotel.get("destinationRef"), fallback_ref=hotel)
            if not self._has_assigned_r2(hotel.get("hotelImage")):
                pick = self._pick(quotation_id=quotation_id, lang=lang, field_id=f"stays.hotels.{index}.hotelImage", pool=exact or destination, preferred=("exterior",))[0:1]
                if pick: changes["hotelImage"] = _ref(pick[0])
            if not self._has_assigned_r2(hotel.get("roomImage")):
                pick = self._pick(quotation_id=quotation_id, lang=lang, field_id=f"stays.hotels.{index}.roomImage", pool=exact or destination, preferred=("room", "interior"))[0:1]
                if pick: changes["roomImage"] = _ref(pick[0])
            if changes:
                patched_hotels[index] = changes
                for field in changes: rationale.append({"fieldId": f"stays.hotels.{index}.{field}", "candidateCount": len(exact or destination), "reason": "accommodation catalogue" if exact else "destination fallback"})
        if patched_hotels: patch["stays"]["hotels"] = patched_hotels
        return {"resolverVersion": RESOLVER_VERSION, "patch": patch, "rationale": rationale}
