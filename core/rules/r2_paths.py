"""R2 media bucket path grammar SSOT (Plan 16.1 quyết định #2 / §2.9).

Pure, no I/O. The confirmed real bucket layout for accommodations is:

    accommodations/{country}/{region}/{province}/{hotel-slug}/{exteriors|interiors}/<file>

There is no `hotels/...` variant. This module exists so both the resolver's
index-aware hotel matcher (R3) and the write path (`services/media_locations.py`,
task M2.2b) share one definition of "which segment is the hotel identity" —
never a second, independently-maintained guess at the grammar.
"""
from __future__ import annotations

from dataclasses import dataclass

ACCOMMODATION_ROOT = "accommodations"
ACCOMMODATION_CATEGORIES: frozenset[str] = frozenset({"exteriors", "interiors"})

# Segment offsets counted from the `accommodations` root segment.
_COUNTRY_OFFSET = 1
_REGION_OFFSET = 2
_PROVINCE_OFFSET = 3
_ACCOMMODATION_SLUG_OFFSET = 4
_CATEGORY_OFFSET = 5


@dataclass(frozen=True)
class AccommodationKeyParts:
    country: str
    region: str
    province: str
    accommodation_slug: str
    category: str


def parse_accommodation_key(segments: list[str]) -> AccommodationKeyParts | None:
    """Parse already-split, lowercased path segments containing `accommodations`.

    `segments` is the full key's `/`-delimited segments (e.g. from
    `"parent/prefix/file".split("/")`) — this function locates its own
    `accommodations` root rather than assuming a fixed starting index, since a
    candidate's `parent_prefix` may itself be rooted under a catalog prefix
    (`shared/media/...`, `library/media/...`).
    """
    if ACCOMMODATION_ROOT not in segments:
        return None
    root_index = segments.index(ACCOMMODATION_ROOT)
    try:
        return AccommodationKeyParts(
            country=segments[root_index + _COUNTRY_OFFSET],
            region=segments[root_index + _REGION_OFFSET],
            province=segments[root_index + _PROVINCE_OFFSET],
            accommodation_slug=segments[root_index + _ACCOMMODATION_SLUG_OFFSET],
            category=segments[root_index + _CATEGORY_OFFSET],
        )
    except IndexError:
        return None


def accommodation_slug_segment(segments: list[str]) -> str | None:
    """The one segment that may carry hotel-identity tokens for tier-1
    matching — never a sibling segment such as `{province}`, which is shared
    by every accommodation in the same city and would otherwise make any
    destination-name token match every hotel in that destination (R3)."""
    parts = parse_accommodation_key(segments)
    return parts.accommodation_slug if parts else None
