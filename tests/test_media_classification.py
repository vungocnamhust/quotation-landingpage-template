"""Plan 16.1 §2.10 / R7 — the media classification SSOT (core/rules/media_classification.py)."""
from core.rules.media_classification import MEDIA_CLASSIFICATION_TAGS, classify_media_asset


def test_classifies_exteriors_and_interiors_from_the_confirmed_r2_category_folder():
    assert classify_media_asset("accommodations/vietnam/north/ha-noi/metropole-hanoi/exteriors", "a.jpg") == "exterior"
    assert classify_media_asset("accommodations/vietnam/north/ha-noi/metropole-hanoi/interiors", "room.jpg") == "interior"


def test_classifies_hero_and_falls_back_to_generic():
    assert classify_media_asset("shared/media/vietnam/north/ha-noi", "hero-a.jpg") == "hero"
    assert classify_media_asset("shared/media/vietnam/north/ha-noi", "generic-b.jpg") == "generic"


def test_room_and_ornament_are_no_longer_classification_tags():
    assert "room" not in MEDIA_CLASSIFICATION_TAGS
    assert "ornament" not in MEDIA_CLASSIFICATION_TAGS
    # A literal "room" filename with no exterior/interior/hero cue in the path
    # now falls through to "generic" rather than the retired "room" tag.
    assert classify_media_asset("accommodations/vietnam/north/ha-noi/metropole-hanoi", "room.jpg") == "generic"
