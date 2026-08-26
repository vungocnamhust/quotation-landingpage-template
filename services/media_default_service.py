"""Canonical, deterministic media defaults for V2 quotation documents.

The service deliberately keeps R2/media-library I/O outside the pure resolver.
It is safe to call during quotation creation: it applies every qualifying R2
catalogue image it can find and reports remaining required slots explicitly.
Publication remains responsible for proving that every referenced R2 object
exists.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from repositories.destination_repository import DestinationRepository
from repositories.media_library_repository import MediaLibraryRepository
from services.brochure_media_resolver import BrochureMediaResolver, Candidate
from services.media_locations import destination_default_media_prefix


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
    ) -> dict[str, Any]:
        await self._hydrate_destination_refs(document)
        catalogue = await self.media_repository.list_active_candidates()
        candidates = [
            Candidate(item.r2_key, item.parent_prefix, item.width, item.height, item.preview_status == "ready")
            for item in catalogue
        ]
        result = BrochureMediaResolver(candidates).resolve_missing(document=document, quotation_id=quotation_id, lang=lang)
        self.apply_patch(document, result["patch"])
        document.setdefault("presentation", {})["mediaDefaults"] = {
            "resolverVersion": result["resolverVersion"],
            "rationale": result["rationale"],
        }
        result["missingSlots"] = self.required_missing_slots(document)
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
            hotel_identity = str(hotels[index].get("sourceFactId") or hotels[index].get("id") or "").strip()
            if not hotel_identity or "hotelImage" not in changes:
                continue
            for segment in _record(document.get("route")).get("staySegments") or []:
                if not isinstance(segment, dict):
                    continue
                if str(segment.get("hotelSourceFactId") or "").strip() == hotel_identity:
                    segment["hotelImage"] = changes["hotelImage"]

    @staticmethod
    def required_missing_slots(document: dict[str, Any]) -> list[str]:
        missing: list[str] = []
        assets = _record(document.get("assets"))
        if not _asset_key(assets.get("hero")):
            missing.append("assets.hero")
        days = _record(document.get("itinerary")).get("days")
        if isinstance(days, list):
            for index, day in enumerate(days):
                carousel = _record(_record(day).get("images")).get("carousel") if isinstance(day, dict) else None
                valid_images = [asset for asset in carousel if _asset_key(asset)] if isinstance(carousel, list) else []
                if len(valid_images) != 3:
                    missing.append(f"itinerary.days.{index}.gallery")
        hotels = _record(document.get("stays")).get("hotels")
        if isinstance(hotels, list):
            for index, hotel in enumerate(hotels):
                values = _record(hotel)
                if not _asset_key(values.get("hotelImage")):
                    missing.append(f"stays.hotels.{index}.hotelImage")
                if not _asset_key(values.get("roomImage")):
                    missing.append(f"stays.hotels.{index}.roomImage")
        return missing
