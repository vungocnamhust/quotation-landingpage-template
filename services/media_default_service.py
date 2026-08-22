"""Canonical, deterministic media defaults for V2 quotation documents.

The service deliberately keeps R2/media-library I/O outside the pure resolver.
It is safe to call during quotation creation: missing destination imagery falls
back to a brand-owned, review-required asset instead of leaving required slots
empty.  Publication remains responsible for proving that every referenced R2
object exists.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from repositories.destination_repository import DestinationRepository
from repositories.media_library_repository import MediaLibraryRepository
from services.brochure_media_resolver import BrochureMediaResolver, Candidate
from services.media_locations import destination_default_media_prefix
from services.storage.r2_storage import R2Storage


BRAND_FALLBACK_MEDIA: dict[str, tuple[str, str]] = {
    "selvara": ("shared/media/brand-fallbacks/selvara/selvara.png", "selvara.png"),
    "capella_travel": ("shared/media/brand-fallbacks/capella_travel/capella_travel.png", "capella_travel.png"),
    "vietnam_safar": ("shared/media/brand-fallbacks/vietnam_safar/vietnam_safar.png", "vietnam_safar.png"),
}
DEFAULT_FALLBACK_BRAND = "vietnam_safar"


class MediaDefaultsIncompleteError(RuntimeError):
    """Raised only when a malformed document still has required media gaps."""

    def __init__(self, missing_slots: list[str]) -> None:
        super().__init__("Media defaults did not satisfy required quotation slots.")
        self.missing_slots = missing_slots


def brand_fallback_key(brand_id: str | None) -> str:
    return BRAND_FALLBACK_MEDIA.get(brand_id or "", BRAND_FALLBACK_MEDIA[DEFAULT_FALLBACK_BRAND])[0]


def _record(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _asset_key(value: Any) -> str:
    return str(_record(value).get("r2Key") or "").strip()


class MediaDefaultService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.destination_repository = DestinationRepository(session)
        self.media_repository = MediaLibraryRepository(session)

    async def apply_missing(
        self,
        *,
        document: dict[str, Any],
        quotation_id: str,
        lang: str,
        brand_id: str | None,
    ) -> dict[str, Any]:
        await self._hydrate_destination_refs(document)
        catalogue = await self.media_repository.list_active_candidates()
        candidates = [
            Candidate(item.r2_key, item.parent_prefix, item.width, item.height, item.preview_status == "ready")
            for item in catalogue
        ]
        # The fallback key is stable and must be seeded into the R2 catalogue by
        # MediaLibraryService.  It remains usable during an indexing delay so a
        # new quotation is never persisted with empty mandatory media slots.
        fallback_key = brand_fallback_key(brand_id)
        if fallback_key not in {candidate.r2_key for candidate in candidates}:
            candidates.append(Candidate(fallback_key, fallback_key.rsplit("/", 1)[0], source="fallback", review_required=True))
        else:
            candidates = [
                Candidate(
                    item.r2_key,
                    item.parent_prefix,
                    item.width,
                    item.height,
                    item.preview_status == "ready",
                    source="fallback" if item.r2_key == fallback_key else "auto",
                    review_required=item.r2_key == fallback_key,
                )
                for item in catalogue
            ]
        result = BrochureMediaResolver(candidates).resolve_missing(document=document, quotation_id=quotation_id, lang=lang)
        self.apply_patch(document, result["patch"])
        fallback_slots = [entry["fieldId"] for entry in result["rationale"] if entry.get("fallback")]
        document.setdefault("presentation", {})["mediaDefaults"] = {
            "resolverVersion": result["resolverVersion"],
            "rationale": result["rationale"],
            "fallbackSlots": fallback_slots,
        }
        missing = self.required_missing_slots(document)
        if missing:
            raise MediaDefaultsIncompleteError(missing)
        return result

    async def _hydrate_destination_refs(self, document: dict[str, Any]) -> None:
        for collection, destination_fields in (("itinerary", ("days",)), ("stays", ("hotels",))):
            parent = _record(document.get(collection))
            values = parent.get(destination_fields[0])
            if not isinstance(values, list):
                continue
            for item in values:
                if not isinstance(item, dict):
                    continue
                destination_ref = _record(item.get("destinationRef"))
                query = item.get("destination") or item.get("city") or destination_ref.get("name")
                if not query:
                    continue
                resolved = await self.destination_repository.resolve(str(query))
                if resolved is None:
                    continue
                item["destinationRef"] = {
                    **destination_ref,
                    "id": destination_ref.get("id") or resolved.id,
                    "name": destination_ref.get("name") or resolved.canonical_name,
                    "slug": destination_ref.get("slug") or resolved.slug,
                    "mediaPrefix": destination_ref.get("mediaPrefix") or resolved.media_prefix,
                    "defaultMediaPrefix": destination_ref.get("defaultMediaPrefix") or destination_default_media_prefix(resolved),
                }

    @staticmethod
    def apply_patch(document: dict[str, Any], patch: dict[str, Any]) -> None:
        assets = _record(patch.get("assets"))
        if assets:
            document.setdefault("assets", {}).update(assets)
        for raw_index, value in _record(_record(patch.get("itinerary")).get("days")).items():
            try:
                index = int(raw_index)
            except (TypeError, ValueError):
                continue
            days = _record(document.get("itinerary")).get("days")
            if not isinstance(days, list) or index < 0 or index >= len(days) or not isinstance(days[index], dict):
                continue
            images = _record(_record(value).get("images"))
            if images:
                days[index].setdefault("images", {}).update(images)
        for raw_index, value in _record(_record(patch.get("stays")).get("hotels")).items():
            try:
                index = int(raw_index)
            except (TypeError, ValueError):
                continue
            hotels = _record(document.get("stays")).get("hotels")
            if not isinstance(hotels, list) or index < 0 or index >= len(hotels) or not isinstance(hotels[index], dict):
                continue
            changes = _record(value)
            hotels[index].update(changes)
            if "hotelImage" not in changes:
                continue
            for segment in _record(document.get("route")).get("staySegments") or []:
                if not isinstance(segment, dict):
                    continue
                if (hotels[index].get("name") and segment.get("hotelName") == hotels[index].get("name")) or (hotels[index].get("city") and segment.get("displayName") == hotels[index].get("city")):
                    segment["hotelImage"] = changes["hotelImage"]

    @staticmethod
    def required_missing_slots(document: dict[str, Any]) -> list[str]:
        missing: list[str] = []
        assets = _record(document.get("assets"))
        for field in ("hero", "itineraryDivider", "hotelDivider"):
            if not _asset_key(assets.get(field)):
                missing.append(f"assets.{field}")
        days = _record(document.get("itinerary")).get("days")
        if isinstance(days, list):
            for index, day in enumerate(days):
                carousel = _record(_record(day).get("images")).get("carousel") if isinstance(day, dict) else None
                if not isinstance(carousel, list) or not any(_asset_key(asset) for asset in carousel):
                    missing.append(f"itinerary.days.{index}.gallery")
        return missing


async def seed_brand_fallback_media(storage: R2Storage) -> None:
    """Idempotently upload the bundled fallback logos before an R2 index run."""
    asset_dir = Path(__file__).resolve().parents[1] / "assets" / "brands"
    for key, filename in BRAND_FALLBACK_MEDIA.values():
        try:
            await asyncio.to_thread(storage.head_object, key)
            continue
        except Exception:
            pass
        source = asset_dir / filename
        if not source.is_file():
            raise RuntimeError(f"Bundled brand fallback asset is missing: {source}")
        content = await asyncio.to_thread(source.read_bytes)
        await asyncio.to_thread(storage.upload_bytes, key, content, "image/png", cache_control="public, max-age=31536000, immutable")
