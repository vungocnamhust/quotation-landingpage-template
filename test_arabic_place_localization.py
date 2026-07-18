import json
import sys
import types
from pathlib import Path


class _FakeAgent:
    def __init__(self, *args, **kwargs):
        pass


fake_pydantic_ai = types.ModuleType("pydantic_ai")
fake_pydantic_ai.Agent = _FakeAgent
sys.modules.setdefault("pydantic_ai", fake_pydantic_ai)

fake_llm_client = types.ModuleType("llm_client")
fake_llm_client.get_model = lambda: None
sys.modules.setdefault("llm_client", fake_llm_client)

import main


FORBIDDEN_ENGLISH_CITY_NAMES = {
    "Hanoi",
    "Ha Long Bay",
    "Halong Bay",
    "Halong",
    "Sapa",
    "Da Nang",
    "Hoi An",
    "Dalat",
    "Da Lat",
    "Ninh Binh",
    "Mekong Delta",
    "Ho Chi Minh City",
    "Ho Chi Minh",
    "Saigon",
}


def _extract_render_sensitive_location_fields(ctx: dict) -> list[str]:
    fields: list[str] = []

    route_txt = ctx.get("route_txt")
    if route_txt:
        fields.append(route_txt)

    for idx in range(1, 8):
        title = ctx.get(f"gal{idx}_title")
        if title:
            fields.append(title)

    for experience in ctx.get("experiences", []):
        title = experience.get("title")
        if title:
            fields.append(title)

    for day in ctx.get("itinerary", []):
        for key in ("title", "overnight"):
            value = day.get(key)
            if value:
                fields.append(value)
        for destination in day.get("destinations", []):
            if destination:
                fields.append(destination)

    for stop in ctx.get("route_stops", []):
        for key in ("displayName", "mapTitle"):
            value = stop.get(key)
            if value:
                fields.append(value)

    for segment in ctx.get("stay_segments", []):
        for key in ("displayName", "transportFromPrevious"):
            value = segment.get(key)
            if value:
                fields.append(value)
        for excursion in segment.get("excursions", []):
            if excursion:
                fields.append(excursion)

    return fields


def _assert_no_english_city_names(ctx: dict):
    offending: list[tuple[str, str]] = []
    for field in _extract_render_sensitive_location_fields(ctx):
        for forbidden in FORBIDDEN_ENGLISH_CITY_NAMES:
            if forbidden in field:
                offending.append((forbidden, field))
    assert not offending, f"English city names leaked into Arabic render fields: {offending}"


def _build_destinations_from_payload(payload: main.TourQuotationPayload) -> list[dict]:
    seen = set()
    destinations = []
    for day in payload.itinerary:
        if not day.destination or day.destination in seen:
            continue
        seen.add(day.destination)
        slug = main._normalize_location_slug(day.destination)
        destinations.append(
            {
                "name": day.destination,
                "slug": slug or "",
                "image_url": "/assets/vietnam-safar-logo.png",
                "images": ["/assets/vietnam-safar-logo.png"],
            }
        )
    return destinations


def test_arabic_place_names_are_localized_for_existing_quotation():
    quotation_id = "quo_3e9bcd4f2f85"
    ctx_data = json.loads((Path("published") / quotation_id / "ctx.json").read_text(encoding="utf-8"))
    payload_dict = (ctx_data.get("translations") or {}).get("ar") or ctx_data.get("baseline_payload")
    payload = main.TourQuotationPayload.model_validate(payload_dict)

    ctx = main._build_ctx(
        quotation_id,
        payload,
        ctx_data.get("img_0") or "/assets/vietnam-safar-logo.png",
        ctx_data.get("destinations") or [],
        lang="ar",
        template_name="vietnam_heritage_luxury.html",
    )

    _assert_no_english_city_names(ctx)


def test_arabic_place_names_are_localized_for_new_generated_quotation():
    payload = main.TourQuotationPayload.model_validate(
        {
            "quotationNumber": "QT-AR-LOCALIZATION-0001",
            "quotationNarrative": "Regression test payload to verify Arabic localization of destination names.",
            "programOverview": {
                "heading": "PROGRAM OVERVIEW",
                "paragraphs": [
                    "A multi-stop Vietnam routing scenario for Arabic localization regression coverage."
                ],
            },
            "landingpageContent": {
                "heroSection": {
                    "headline": "LUXURY QUOTATION",
                    "subtitle": "VIETNAM ROUTE LOCALIZATION TEST – 6D5N",
                },
                "visualDescription": "A route-focused quotation test with multiple destination names.",
            },
            "journeyGlance": {
                "market": "GCC",
                "guestProfile": "2 Adults",
                "hotelStandard": "4★",
                "mealPreference": "Breakfast",
                "priceType": "Indicative",
                "tourCode": "VS-AR-LOC-TEST",
                "domesticFlights": "Included",
                "priceBasis": "Twin sharing",
                "partnerNote": "Arabic localization regression test",
                "validity": "On request",
            },
            "whyWorks": {
                "privateFlexible": "Private pacing across multiple destinations.",
                "comfort": "Comfort-led routing.",
                "muslimFriendly": "Suitable for Arabic market testing.",
                "balancedHighlights": "Combines transfers, returns, and excursions.",
            },
            "itinerary": [
                {
                    "dayNumber": 1,
                    "destination": "Hanoi",
                    "summary": "Arrival in Hanoi and check-in.",
                    "mainInclusions": "Airport transfer.",
                    "senseOfPace": "Relaxed",
                    "dining": "",
                },
                {
                    "dayNumber": 2,
                    "destination": "Ninh Binh",
                    "summary": "Day trip to Ninh Binh and return to Hanoi.",
                    "mainInclusions": "Private excursion.",
                    "senseOfPace": "Moderate",
                    "dining": "Breakfast",
                },
                {
                    "dayNumber": 3,
                    "destination": "Halong Bay",
                    "summary": "Transfer from Hanoi to Halong Bay.",
                    "mainInclusions": "Private transfer.",
                    "senseOfPace": "Relaxed",
                    "dining": "Breakfast",
                },
                {
                    "dayNumber": 4,
                    "destination": "Da Nang",
                    "summary": "Fly to Da Nang and continue to Hoi An before returning to Da Nang.",
                    "mainInclusions": "Domestic flight and transfers.",
                    "senseOfPace": "Immersive",
                    "dining": "Breakfast",
                },
                {
                    "dayNumber": 5,
                    "destination": "Dalat",
                    "summary": "Continue to Dalat for a cool mountain stay.",
                    "mainInclusions": "Transfer and hotel.",
                    "senseOfPace": "Relaxed",
                    "dining": "Breakfast",
                },
                {
                    "dayNumber": 6,
                    "destination": "Ho Chi Minh City",
                    "summary": "Visit the Mekong Delta and return to Ho Chi Minh City for departure.",
                    "mainInclusions": "Private excursion and airport transfer.",
                    "senseOfPace": "Moderate",
                    "dining": "Breakfast",
                },
            ],
            "hotelPlan": {
                "hotels": [
                    {
                        "destination": "Hanoi",
                        "checkInDate": "2026-09-01",
                        "checkOutDate": "2026-09-03",
                        "hotelArrangement": "Minasi Premium Hotel",
                    },
                    {
                        "destination": "Halong Bay",
                        "checkInDate": "2026-09-03",
                        "checkOutDate": "2026-09-04",
                        "hotelArrangement": "La Casta Cruise",
                    },
                    {
                        "destination": "Da Nang",
                        "checkInDate": "2026-09-04",
                        "checkOutDate": "2026-09-05",
                        "hotelArrangement": "Minh Toan SAFI Ocean Hotel",
                    },
                    {
                        "destination": "Dalat",
                        "checkInDate": "2026-09-05",
                        "checkOutDate": "2026-09-06",
                        "hotelArrangement": "CICILIA Rouge Dalat",
                    },
                    {
                        "destination": "Ho Chi Minh City",
                        "checkInDate": "2026-09-06",
                        "checkOutDate": "2026-09-07",
                        "hotelArrangement": "Cicilia Saigon Center",
                    },
                ],
                "roomNotes": "Test rooming only.",
            },
            "optionalEnhancements": [],
            "bookingTerms": {
                "deposit": "30% deposit.",
                "balance": "Balance before arrival.",
                "cancellation": "Standard policy applies.",
                "confirmation": "Subject to confirmation.",
            },
            "finalization": {
                "finalDetailsRequired": "Passport copies.",
                "afterConfirmation": "Final vouchers issued.",
            },
            "pricing": {
                "totalPriceUsd": 3990.0,
                "currency": "USD",
                "markupApplied": 0.1,
                "breakdown": {
                    "hotels": 2200.0,
                    "activities": 500.0,
                    "guides": 300.0,
                    "transfers": 490.0,
                    "flights": 500.0,
                },
            },
            "retrievalStatus": {
                "hotel": "pending",
                "activity": "pending",
                "guide": "pending",
                "transfer": "pending",
                "flight": "pending",
            },
            "candidateBlocks": [],
        }
    )

    destinations = _build_destinations_from_payload(payload)
    ctx = main._build_ctx(
        "quo_regression_ar_new",
        payload,
        "/assets/vietnam-safar-logo.png",
        destinations,
        lang="ar",
        template_name="vietnam_heritage_luxury.html",
    )

    _assert_no_english_city_names(ctx)
