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

from editable_brochure_contract import resolve_media_entity_index
from repositories.destination_repository import DestinationRepository
from repositories.media_library_repository import MediaLibraryRepository
from services.brochure_media_resolver import BrochureMediaResolver, Candidate
from services.media_locations import destination_default_media_prefix


def _record(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _asset_key(value: Any) -> str:
    return str(_record(value).get("r2Key") or "").strip()


def _clear_media_field(document: dict[str, Any], field_id: str) -> None:
    """Blank a single fact media field so the resolver treats it as empty.

    Used only by the `fieldIds` + `force` Reset-to-default path (Plan 16.1
    D4) — the one deliberate way to overwrite a manual selection, always
    initiated by the user on an exact slot.
    """
    if field_id.startswith("assets."):
        key = field_id.rsplit(".", 1)[-1]
        assets = document.get("assets")
        if isinstance(assets, dict):
            assets[key] = {"status": "empty"}
        return
    if field_id.startswith("itinerary.days."):
        index = resolve_media_entity_index("itinerary", "days", field_id.split(".")[2], document)
        days = _record(document.get("itinerary")).get("days")
        if index is not None and isinstance(days, list) and 0 <= index < len(days) and isinstance(days[index], dict):
            images = days[index].get("images")
            if isinstance(images, dict):
                images["carousel"] = []
        return
    if field_id.startswith("stays.hotels."):
        parts = field_id.split(".")
        index = resolve_media_entity_index("stays", "hotels", parts[2], document)
        hotels = _record(document.get("stays")).get("hotels")
        if index is not None and isinstance(hotels, list) and 0 <= index < len(hotels) and isinstance(hotels[index], dict):
            hotels[index][parts[3]] = {"status": "empty"}


def _requested_media_targets(field_ids: list[str], document: dict[str, Any]) -> dict[str, Any]:
    """Resolve requested fieldIds into a filter spec, so a Reset-to-default
    call touches exactly those slots and never incidentally autofills an
    unrelated empty slot elsewhere in the document."""
    assets: set[str] = set()
    days: set[int] = set()
    hotel_fields: set[tuple[int, str]] = set()
    for field_id in field_ids:
        if field_id.startswith("assets."):
            assets.add(field_id.rsplit(".", 1)[-1])
        elif field_id.startswith("itinerary.days."):
            index = resolve_media_entity_index("itinerary", "days", field_id.split(".")[2], document)
            if index is not None:
                days.add(index)
        elif field_id.startswith("stays.hotels."):
            parts = field_id.split(".")
            index = resolve_media_entity_index("stays", "hotels", parts[2], document)
            if index is not None:
                hotel_fields.add((index, parts[3]))
    return {"assets": assets, "days": days, "hotel_fields": hotel_fields}


def _filter_media_patch(patch: dict[str, Any], targets: dict[str, Any]) -> dict[str, Any]:
    filtered_assets = {k: v for k, v in _record(patch.get("assets")).items() if k in targets["assets"]}
    filtered_days: dict[str, Any] = {}
    for raw_index, value in _record(_record(patch.get("itinerary")).get("days")).items():
        try:
            index = int(raw_index)
        except (TypeError, ValueError):
            continue
        if index in targets["days"]:
            filtered_days[raw_index] = value
    filtered_hotels: dict[str, Any] = {}
    for raw_index, value in _record(_record(patch.get("stays")).get("hotels")).items():
        try:
            index = int(raw_index)
        except (TypeError, ValueError):
            continue
        changes = {k: v for k, v in _record(value).items() if (index, k) in targets["hotel_fields"]}
        if changes:
            filtered_hotels[raw_index] = changes
    return {
        "assets": filtered_assets,
        "itinerary": {"days": filtered_days} if filtered_days else {},
        "stays": {"hotels": filtered_hotels} if filtered_hotels else {},
    }


def _count_patch_entries(patch: dict[str, Any]) -> int:
    return (
        len(_record(patch.get("assets")))
        + sum(len(_record(_record(day).get("images")).get("carousel") or []) for day in _record(_record(patch.get("itinerary")).get("days")).values())
        + sum(len(_record(hotel)) for hotel in _record(_record(patch.get("stays")).get("hotels")).values())
    )


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
        field_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Fill missing media defaults.

        Without `field_ids`: fills every empty slot, never overwrites an
        existing value (today's behavior). With `field_ids` (Plan 16.1 D4,
        Reset-to-default): the listed slots are cleared and re-resolved —
        the one deliberate path allowed to overwrite a manual selection —
        and the resulting patch is restricted to exactly those slots, so no
        other empty slot is incidentally autofilled in the same call.
        """
        if field_ids:
            for field_id in field_ids:
                _clear_media_field(document, field_id)
        await self._hydrate_destination_refs(document)
        catalogue = await self.media_repository.list_active_candidates()
        candidates = [
            Candidate(item.r2_key, item.parent_prefix, item.width, item.height, item.preview_status == "ready")
            for item in catalogue
        ]
        result = BrochureMediaResolver(candidates).resolve_missing(document=document, quotation_id=quotation_id, lang=lang)
        patch = result["patch"]
        if field_ids:
            patch = _filter_media_patch(patch, _requested_media_targets(field_ids, document))
            result["patch"] = patch
            result["appliedCount"] = _count_patch_entries(patch)
            result["hasChanges"] = bool(patch["assets"] or patch["itinerary"] or patch["stays"])
        self.apply_patch(document, patch)
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
