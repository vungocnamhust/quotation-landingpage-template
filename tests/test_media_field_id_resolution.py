"""Plan 16.1 M3.3 — media fieldIds resolve by stable id first, numeric index
as a legacy fallback, so a save submitted with a stale array position still
lands on the right day/hotel after a reorder."""
from editable_brochure_contract import resolve_media_entity_index
from main import _get_fact_media_field, _set_fact_media_field


def _document():
    return {
        "itinerary": {
            "days": [
                {"sourceFactId": "day_a", "images": {}},
                {"sourceFactId": "day_b", "images": {}},
            ]
        },
        "stays": {
            "hotels": [
                {"sourceFactId": "hotel_a", "hotelImage": {}},
                {"sourceFactId": "hotel_b", "hotelImage": {}},
            ]
        },
    }


def test_resolves_by_stable_id_regardless_of_array_position():
    document = _document()
    assert resolve_media_entity_index("itinerary", "days", "day_b", document) == 1
    assert resolve_media_entity_index("stays", "hotels", "hotel_a", document) == 0


def test_falls_back_to_numeric_index_for_legacy_field_ids():
    document = _document()
    assert resolve_media_entity_index("itinerary", "days", "1", document) == 1


def test_returns_none_for_an_id_that_no_longer_exists():
    document = _document()
    assert resolve_media_entity_index("itinerary", "days", "day_z", document) is None


def test_set_and_get_fact_media_field_survive_an_itinerary_reorder():
    document = _document()
    _set_fact_media_field(document, "itinerary.days.day_b.gallery", [{"r2Key": "b.jpg"}])

    # Reorder the itinerary — day_b moves from index 1 to index 0.
    document["itinerary"]["days"] = list(reversed(document["itinerary"]["days"]))

    value = _get_fact_media_field(document, "itinerary.days.day_b.gallery")
    assert value == [{"r2Key": "b.jpg"}]
    # A numeric-index fieldId built before the reorder would now hit day_a.
    assert document["itinerary"]["days"][1]["sourceFactId"] == "day_a"
    assert document["itinerary"]["days"][1]["images"].get("carousel") is None


def test_set_fact_media_field_rejects_an_id_that_no_longer_exists():
    document = _document()
    import pytest
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        _set_fact_media_field(document, "stays.hotels.hotel_z.hotelImage", {"r2Key": "x.jpg"})
    assert exc.value.status_code == 422
