from __future__ import annotations

import re
from dataclasses import dataclass

from db.models.destination import DestinationCatalog
from db.models.travel_designer import TravelDesignerProfile


_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def storage_slug(value: str) -> str:
    return _SLUG_PATTERN.sub("-", (value or "").casefold()).strip("-")


@dataclass(frozen=True)
class MediaLocation:
    kind: str
    leaf_prefix: str
    subject_type: str
    subject_id: str
    destination_id: str | None = None
    accommodation_slug: str | None = None
    accommodation_kind: str | None = None
    asset_category: str | None = None


def destination_location(destination: DestinationCatalog) -> MediaLocation:
    if destination.media_prefix and destination.media_prefix.strip():
        leaf_prefix = destination.media_prefix.strip().strip("/")
        return MediaLocation("destination", leaf_prefix, "destination", destination.id, destination_id=destination.id)
    parts = [destination.country_slug, destination.region_slug, destination.province_slug, destination.slug]
    if not all(parts):
        raise ValueError("Destination geographic mapping is incomplete.")
    return MediaLocation("destination", "/".join(parts), "destination", destination.id, destination_id=destination.id)


def destination_default_media_prefix(destination: DestinationCatalog) -> str:
    return destination_location(destination).leaf_prefix


def accommodation_location(destination: DestinationCatalog, name: str, kind: str) -> MediaLocation:
    base = destination_location(destination)
    accommodation = storage_slug(name)
    if not accommodation:
        raise ValueError("Accommodation name is required.")
    return MediaLocation("accommodation", f"accommodations/{base.leaf_prefix}/{accommodation}", "accommodation", accommodation, destination_id=destination.id, accommodation_slug=accommodation, accommodation_kind=kind)


def accommodation_asset_location(*, asset_prefix: str, profile_id: str, destination_id: str, accommodation_slug: str, asset_category: str) -> MediaLocation:
    """Build an upload location from the persisted accommodation storage identity.

    The accommodation name and destination are editable catalogue metadata.  They
    must never be used to recompute the R2 root of an existing profile, because
    that would orphan its assets after a rename or destination correction.
    """
    normalized_prefix = (asset_prefix or "").strip().strip("/")
    if not normalized_prefix:
        raise ValueError("Accommodation asset prefix is missing.")
    if asset_category not in {"exteriors", "interiors"}:
        raise ValueError("Accommodation asset category must be exteriors or interiors.")
    return MediaLocation(
        "accommodation",
        f"{normalized_prefix}/{asset_category}",
        "accommodation",
        profile_id,
        destination_id=destination_id,
        accommodation_slug=accommodation_slug,
        accommodation_kind="hotel",
        asset_category=asset_category,
    )


def team_location(profile: TravelDesignerProfile) -> MediaLocation:
    slug = profile.storage_slug or storage_slug(profile.email.split("@", 1)[0])
    if not slug:
        raise ValueError("Travel Designer storage slug is missing.")
    return MediaLocation("team", f"team/{slug}", "travel_designer", profile.id)
