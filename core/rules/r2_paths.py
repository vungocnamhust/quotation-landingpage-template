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


def r2_province_segment(province_slug: str) -> str:
    """SSOT for the `{province}` segment — shared by the write path
    (`services/media_locations.py::destination_location`) and, going
    forward, anything else that needs to build rather than just parse an R2
    key (Plan 16.1 M2.2b).

    Resolved by `scripts/audit_r2_province_segments.py` against the live
    bucket (task M2.2a): the destination catalog roots (`vietnam/{region}/{province}/...`)
    already use the hyphenated form matching `DestinationCatalog.province_slug`
    exactly (`da-lat`, `mui-ne`, `nha-trang`, ...) — this is the bucket's own
    prevailing convention. `accommodations/vietnam/north/hanoi/...` is a
    single legacy folder predating this convention; it is not migrated by
    this change (a real production R2 rename needs an explicit, separate
    decision), and is unaffected because `_matches_destination`'s alias
    matching already tries the compact form as a fallback when reading.
    """
    return province_slug
