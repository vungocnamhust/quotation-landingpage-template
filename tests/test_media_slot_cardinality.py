"""Plan 16.1 R9/M1.4 — minItems must be enforced, not just maxItems."""
import pytest
from fastapi import HTTPException

from main import _validate_v2_fact_media_slots


def _item(key: str) -> dict:
    return {"r2Key": key, "altText": ""}


def test_gallery_below_min_items_is_rejected():
    with pytest.raises(HTTPException) as exc:
        _validate_v2_fact_media_slots([
            {
                "fieldId": "itinerary.days.0.gallery",
                "value": [_item("shared/media/a.jpg"), _item("shared/media/b.jpg")],
            }
        ])
    assert exc.value.status_code == 422
    assert exc.value.detail["invalidKeys"] == ["itinerary.days.0.gallery"]


def test_gallery_above_max_items_is_still_rejected():
    with pytest.raises(HTTPException) as exc:
        _validate_v2_fact_media_slots([
            {
                "fieldId": "itinerary.days.0.gallery",
                "value": [_item("shared/media/a.jpg"), _item("shared/media/b.jpg"), _item("shared/media/c.jpg"), _item("shared/media/d.jpg")],
            }
        ])
    assert exc.value.status_code == 422


def test_gallery_at_exactly_min_items_is_accepted():
    result = _validate_v2_fact_media_slots([
        {
            "fieldId": "itinerary.days.0.gallery",
            "value": [_item("shared/media/a.jpg"), _item("shared/media/b.jpg"), _item("shared/media/c.jpg")],
        }
    ])
    assert len(result["itinerary.days.0.gallery"]) == 3


def test_gallery_cleared_to_empty_is_still_allowed():
    result = _validate_v2_fact_media_slots([
        {"fieldId": "itinerary.days.0.gallery", "value": []},
    ])
    assert result["itinerary.days.0.gallery"] == []


def test_single_image_slot_is_unaffected_by_gallery_min_items_check():
    result = _validate_v2_fact_media_slots([
        {"fieldId": "assets.hero", "value": _item("shared/media/hero.jpg")},
    ])
    assert result["assets.hero"]["r2Key"] == "shared/media/hero.jpg"
