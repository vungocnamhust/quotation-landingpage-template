"""Plan 16.1 §2.9(a) — the R2 accommodation-path grammar SSOT (core/rules/r2_paths.py)."""
from core.rules.r2_paths import (
    ACCOMMODATION_CATEGORIES,
    ACCOMMODATION_ROOT,
    accommodation_slug_segment,
    parse_accommodation_key,
)


def test_parses_the_confirmed_accommodation_grammar():
    segments = "accommodations/vietnam/north/ha-noi/metropole-hanoi/exteriors/a.jpg".split("/")
    parts = parse_accommodation_key(segments)
    assert parts is not None
    assert parts.country == "vietnam"
    assert parts.region == "north"
    assert parts.province == "ha-noi"
    assert parts.accommodation_slug == "metropole-hanoi"
    assert parts.category == "exteriors"


def test_locates_the_accommodations_root_even_when_prefixed_by_a_catalog_root():
    segments = "library/media/accommodations/vietnam/north/ha-noi/metropole-hanoi/interiors/room.jpg".split("/")
    parts = parse_accommodation_key(segments)
    assert parts is not None
    assert parts.accommodation_slug == "metropole-hanoi"
    assert parts.category == "interiors"


def test_returns_none_for_a_non_accommodation_key():
    assert parse_accommodation_key("shared/media/vietnam/north/ha-noi/hero.jpg".split("/")) is None


def test_returns_none_when_the_key_is_truncated_before_the_slug_segment():
    assert parse_accommodation_key("accommodations/vietnam/north".split("/")) is None


def test_accommodation_slug_segment_is_the_single_source_for_hotel_identity():
    assert accommodation_slug_segment("accommodations/vietnam/north/ha-noi/metropole-hanoi/exteriors/a.jpg".split("/")) == "metropole-hanoi"
    assert accommodation_slug_segment("shared/media/vietnam/hero.jpg".split("/")) is None


def test_category_vocabulary_matches_the_confirmed_r2_grammar():
    assert ACCOMMODATION_CATEGORIES == {"exteriors", "interiors"}
    assert ACCOMMODATION_ROOT == "accommodations"
