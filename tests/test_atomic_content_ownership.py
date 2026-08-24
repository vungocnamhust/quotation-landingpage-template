from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from quote_document import CreateQuoteHotelFact, CreateQuoteRequestV1, QuoteDocumentV1, validate_quote_content_block
from services.content_draft_service import ContentDraftService
from services.content_registry import content_registry_payload, scope_spec
from services.skeleton_builder import SkeletonBuilder
from scripts.migrate_v2_rich_content import migrate


def _facts() -> CreateQuoteRequestV1:
    return CreateQuoteRequestV1.model_validate({
        "trip_facts": {
            "destinations": ["Hanoi", "Ninh Binh"],
            "start_date": "2026-10-01",
            "end_date": "2026-10-02",
            "itinerary": [
                {"day_number": 1, "destination": "Hanoi", "summary": "Arrival", "overnight": "Hanoi"},
                {"day_number": 2, "destination": "Ninh Binh", "summary": "Explore karst landscapes", "overnight": "Ninh Binh"},
            ],
        },
        "service_facts": {"inclusions": ["Private guide"], "exclusions": ["International flights"]},
        "booking_facts": {"description": "All services remain subject to confirmation.", "items": [{"key": "deposit", "label": "Deposit", "body": "A 30 percent deposit is required."}]},
    })


def _document() -> dict:
    return SkeletonBuilder().build(
        quotation_id="quo_atomic_test",
        payload=_facts(),
        resolved_facts={"duration": {"label": "2 days / 1 night"}, "routeLabel": "Hanoi – Ninh Binh", "travelDateLabel": "01–02 Oct 2026"},
        template="quote-generator",
    )


def test_facts_reject_editorial_copy_fields_after_cutover():
    with pytest.raises(ValidationError):
        CreateQuoteRequestV1.model_validate({"trip_facts": {"title": "Legacy title"}})
    with pytest.raises(ValidationError):
        CreateQuoteRequestV1.model_validate({"trip_facts": {"itinerary": [{"day_number": 1, "display_title": "Legacy day"}]}})


def test_canonical_document_rejects_retired_rich_content_paths():
    document = _document()
    document["bookingTerms"] = {"description": "Legacy terms"}
    with pytest.raises(ValidationError, match="Legacy rich document fields"):
        QuoteDocumentV1.model_validate(document)


def test_rich_blocks_are_discriminated_and_reject_html_or_unknown_keys():
    assert validate_quote_content_block({"type": "paragraph", "text": "Plain canonical prose"}).type == "paragraph"
    with pytest.raises(ValidationError):
        validate_quote_content_block({"type": "paragraph", "text": "<p>unsafe</p>"})
    with pytest.raises(ValidationError):
        validate_quote_content_block({"type": "paragraph", "text": "Valid", "leftItems": ["wrong shape"]})


def test_skeleton_materializes_facts_but_never_editorial_copy():
    document = _document()
    assert document["trip"]["title"] == ""
    assert document["trip"]["lede"] == ""
    assert document["route"]["title"] == ""
    assert document["itinerary"]["days"][0]["title"] == ""
    assert document["content"]["sections"]["inclusions_exclusions"]["blocks"][0]["type"] == "twoColumnList"
    assert document["content"]["sections"]["booking_terms"]["blocks"][0]["type"] == "paragraph"


def test_hotel_facts_and_editorial_copy_are_separate_in_the_skeleton() -> None:
    facts = _facts()
    facts.service_facts.hotels = [
        CreateQuoteHotelFact(id="hotel_fact_1", destination="Hanoi", name="Hotel One", intro="Factual hotel description.")
    ]
    document = SkeletonBuilder().build(
        quotation_id="quo_hotel_identity",
        payload=facts,
        resolved_facts={"duration": {"label": "2 days / 1 night"}, "routeLabel": "Hanoi – Ninh Binh", "travelDateLabel": "01–02 Oct 2026"},
        template="quote-generator",
    )
    hotel = document["stays"]["hotels"][0]
    assert hotel["sourceFactId"] == "hotel_fact_1"
    assert hotel["introduction"] == "Factual hotel description."
    assert hotel["editorialIntroduction"] == ""


def test_candidate_apply_cannot_write_fact_or_design_paths():
    document = _document()
    with pytest.raises(ValueError):
        ContentDraftService.apply_candidate(document, "hero", {"pricing": {"title": "Not content-owned"}})
    with pytest.raises(ValueError):
        ContentDraftService.apply_candidate(document, "booking_terms", {"content": {"sections": {"booking_terms": {"blocks": [{"type": "paragraph", "text": "<b>unsafe</b>"}]}}}})


def test_content_apply_changes_only_its_registry_target():
    document = _document()
    original = copy.deepcopy(document)
    result = ContentDraftService.apply_candidate(document, "hero", {
        "trip": {"title": "A quiet two-day journey", "lede": "A quiet two-day journey."},
        "narrative": {"coverKicker": "Private journey", "footerText": "Prepared for a private party."},
    })
    assert result["trip"]["title"] == "A quiet two-day journey"
    assert result["trip"]["lede"] == "A quiet two-day journey."
    assert result["pricing"] == original["pricing"]
    assert result["content"] == original["content"]


def test_hero_registry_and_candidate_include_content_owned_trip_title():
    assert "trip.title" in scope_spec("hero").canonical_targets
    document = _document()
    result = ContentDraftService.apply_candidate(document, "hero", {
        "trip": {"title": "A Hanoi interlude", "lede": "A quiet journey through northern Vietnam."},
        "narrative": {"coverKicker": "Privately arranged", "footerText": "Prepared for considered travellers."},
    })
    assert result["trip"]["title"] == "A Hanoi interlude"


def test_hero_meta_and_route_stop_descriptions_have_content_controls_and_preserve_route_facts():
    hero_fields = {field["id"] for field in content_registry_payload()["hero"]["fields"]}
    route_fields = {field["id"] for field in content_registry_payload()["route"]["fields"]}
    assert {"hero-meta-primary", "hero-meta-secondary"} <= hero_fields
    assert "route-stop-descriptions" in route_fields

    document = _document()
    original_segments = copy.deepcopy(document["route"]["staySegments"])
    result = ContentDraftService.apply_candidate(document, "route", {
        "route": {
            "title": "Northern rhythm",
            "description": "A considered route through northern Vietnam.",
            "mapSegmentDescriptions": ["Arrival and first impressions", "Karst landscapes and a quiet stay"],
        },
    })
    assert [item["mapSegmentDesc"] for item in result["route"]["staySegments"]] == ["Arrival and first impressions", "Karst landscapes and a quiet stay"]
    assert [item["displayName"] for item in result["route"]["staySegments"]] == [item["displayName"] for item in original_segments]


@pytest.mark.parametrize(
    ("scope", "required_fact"),
    (
        ("hotel_plan", "service_facts.hotels"),
        ("pricing", "pricing_facts.options"),
        ("inclusions_exclusions", "service_facts.inclusions"),
    ),
)
def test_manual_editorial_sections_keep_authoritative_fact_handoffs(scope: str, required_fact: str):
    spec = scope_spec(scope)
    assert spec.owner == "content"
    assert spec.generation is False
    assert spec.automation_policy == "manual"
    assert required_fact in spec.required_facts


@pytest.mark.parametrize(("scope", "required_fact"), (("designer", "designer_facts"), ("booking_terms", "booking_facts")))
def test_fact_owned_sections_remain_read_only(scope: str, required_fact: str):
    spec = scope_spec(scope)
    assert spec.owner == "fact"
    assert spec.generation is False
    assert required_fact in spec.required_facts


def test_migration_moves_and_removes_legacy_rich_fields():
    document = _document()
    document.update({
        "inclusions": [{"id": "inc", "text": "Private guide"}],
        "exclusions": [{"id": "exc", "text": "Flights"}],
        "bookingTerms": {"description": "Approved terms", "items": [{"id": "deposit", "label": "Deposit", "body": "30 percent"}]},
        "finalization": {"requiredItems": [{"id": "passport", "text": "Passport copy"}]},
    })
    migrated, request = migrate(document, _facts().model_dump(mode="json"))
    assert not {"inclusions", "exclusions", "bookingTerms", "finalization"}.intersection(migrated)
    assert migrated["content"]["sections"]["booking_terms"]["blocks"][0]["type"] == "paragraph"
    assert request["trip_facts"] == _facts().model_dump(mode="json")["trip_facts"]


def test_content_owned_targets_includes_itinerary_day_targets():
    from services.content_registry import content_owned_targets
    targets = content_owned_targets()
    assert "itinerary.days.*.title" in targets
    assert "itinerary.days.*.description" in targets
    assert "itinerary.days.*.activities" in targets


def test_preserve_content_owned_values_keeps_itinerary_day_content_and_price_basis():
    from main import _preserve_content_owned_values
    current = _document()
    current["itinerary"]["days"][0]["title"] = "Day 1: Arrival in Hanoi"
    current["itinerary"]["days"][0]["description"] = ["Welcome to Vietnam.", "Transfer to hotel."]
    current["itinerary"]["days"][0]["activities"] = ["Airport pickup", "Old Quarter tour"]
    current["itinerary"]["days"][0]["labelHighlights"] = "Key Highlights"
    current["itinerary"]["days"][0]["labelNotes"] = "Day Notes"
    current["trip"]["priceBasis"] = "Based on twin share accommodation."
    current["viewOverrides"] = {"web": {"itinerary": {"variant": "compact"}}, "pdf": {}}

    rebuilt = _document()
    _preserve_content_owned_values(current, rebuilt)

    assert rebuilt["itinerary"]["days"][0]["title"] == "Day 1: Arrival in Hanoi"
    assert rebuilt["itinerary"]["days"][0]["description"] == ["Welcome to Vietnam.", "Transfer to hotel."]
    assert rebuilt["itinerary"]["days"][0]["activities"] == ["Airport pickup", "Old Quarter tour"]
    assert rebuilt["itinerary"]["days"][0]["labelHighlights"] == "Key Highlights"
    assert rebuilt["itinerary"]["days"][0]["labelNotes"] == "Day Notes"
    assert rebuilt["trip"]["priceBasis"] == "Based on twin share accommodation."
