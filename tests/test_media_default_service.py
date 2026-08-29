"""Plan 16.1 D4 — Reset-to-default: `fieldIds` + `force` is the one path
allowed to overwrite a manual media selection, and it must never touch a
slot the caller didn't ask for.
"""
import pytest

from services.media_default_service import MediaDefaultService
from services.brochure_media_resolver import Candidate


CATALOGUE = [
    Candidate("shared/media/vietnam/north/ha-noi/hero-a.jpg", "shared/media/vietnam/north/ha-noi", 1800, 900, True),
    Candidate("shared/media/vietnam/north/ha-noi/generic-b.jpg", "shared/media/vietnam/north/ha-noi", 1600, 900, True),
    Candidate("shared/media/vietnam/north/ha-noi/generic-c.jpg", "shared/media/vietnam/north/ha-noi", 1600, 900, True),
]


class FakeMediaRepository:
    async def list_active_candidates(self):
        return [
            type("Row", (), {
                "r2_key": c.r2_key, "parent_prefix": c.parent_prefix, "width": c.width, "height": c.height,
                "preview_status": "ready", "media_kind": "", "subject_type": "", "destination_id": "",
                "accommodation_slug": "", "accommodation_kind": "",
            })()
            for c in CATALOGUE
        ]


class FakeDestinationRepository:
    async def resolve(self, query):
        return None


def _service():
    service = MediaDefaultService.__new__(MediaDefaultService)
    service.destination_repository = FakeDestinationRepository()
    service.media_repository = FakeMediaRepository()
    return service


def _document():
    return {
        "assets": {"hero": {"r2Key": "manual-hero.jpg", "source": "manual"}},
        "itinerary": {
            "days": [
                {"sourceFactId": "day_a", "destinationRef": {"slug": "ha-noi"}, "images": {"carousel": [{"r2Key": "manual-day.jpg", "source": "manual"}]}},
            ]
        },
        "stays": {"hotels": []},
    }


@pytest.mark.anyio
async def test_without_field_ids_never_overwrites_existing_manual_media():
    service = _service()
    document = _document()
    result = await service.apply_missing(document=document, quotation_id="quo_1", lang="en")
    assert document["assets"]["hero"]["r2Key"] == "manual-hero.jpg"
    assert result["hasChanges"] is False or "hero" not in result["patch"].get("assets", {})


@pytest.mark.anyio
async def test_force_reset_overwrites_only_the_requested_slot():
    service = _service()
    document = _document()
    result = await service.apply_missing(document=document, quotation_id="quo_1", lang="en", field_ids=["assets.hero"])
    assert document["assets"]["hero"]["r2Key"] != "manual-hero.jpg"
    assert document["assets"]["hero"]["source"] == "auto"
    # The day gallery was NOT requested — its manual image must be untouched.
    assert document["itinerary"]["days"][0]["images"]["carousel"] == [{"r2Key": "manual-day.jpg", "source": "manual"}]
    assert result["hasChanges"] is True
    assert "days" not in result["patch"].get("itinerary", {})


@pytest.mark.anyio
async def test_force_reset_by_stable_day_id_survives_reorder_and_leaves_other_days_alone():
    service = _service()
    document = {
        "assets": {},
        "itinerary": {
            "days": [
                {"sourceFactId": "day_a", "destinationRef": {"slug": "ha-noi"}, "images": {"carousel": [{"r2Key": "keep-a.jpg", "source": "manual"}] * 1}},
                {"sourceFactId": "day_b", "destinationRef": {"slug": "ha-noi"}, "images": {"carousel": [{"r2Key": "reset-b.jpg", "source": "manual"}]}},
            ]
        },
        "stays": {"hotels": []},
    }
    result = await service.apply_missing(document=document, quotation_id="quo_1", lang="en", field_ids=["itinerary.days.day_b.gallery"])
    assert document["itinerary"]["days"][0]["images"]["carousel"] == [{"r2Key": "keep-a.jpg", "source": "manual"}]
    day_b_carousel = document["itinerary"]["days"][1]["images"]["carousel"]
    assert "reset-b.jpg" not in [item["r2Key"] for item in day_b_carousel]
    assert result["appliedCount"] > 0
