import unittest
from typing import Any

from quote_document import (
    CreateQuotePricingOptionFact,
    CreateQuoteRequestV1,
    TripFactDay,
)
from services.facts_resolver import FactsResolver


class MockDestination:
    def __init__(self, id: str, canonical_name: str, slug: str, latitude: float, longitude: float):
        self.id = id
        self.canonical_name = canonical_name
        self.slug = slug
        self.latitude = latitude
        self.longitude = longitude


DESTINATION_CATALOG = {
    "ho-chi-minh-city": MockDestination("dst_hcm", "Ho Chi Minh City", "ho-chi-minh-city", 10.8231, 106.6297),
    "mekong-delta": MockDestination("dst_mekong", "Mekong Delta", "mekong-delta", 10.0333, 105.7833),
}


async def mock_resolve_destination(value: str | None) -> Any | None:
    if not value:
        return None
    slug = value.casefold().strip().replace(" ", "-")
    return DESTINATION_CATALOG.get(slug)


class QuotationFactsPutPayloadTests(unittest.IsolatedAsyncioTestCase):
    def test_user_reported_422_curl_payload_validates_successfully(self):
        payload_data = {
            "source": {"kind": "manual", "handoff_id": None},
            "brand_id": "selvara",
            "lang": "en",
            "presentation_options": {
                "template_id": "quote-generator",
                "travel_designer_id": "td_b49deb4d9586",
                "renderer": "quote-generator",
                "theme_id": "brochure",
                "layout_version": 1,
            },
            "trip_facts": {
                "destinations": ["Ho Chi Minh City", "Mekong Delta"],
                "start_date": "2026-09-26",
                "end_date": "2026-09-28",
                "duration_days": 3,
                "duration_nights": 2,
                "itinerary": [
                    {
                        "day_number": 1,
                        "destination": "Ho Chi Minh City",
                        "summary": "THam quan nhà thờ đức bà, bưu điện sài gòn, dinh độc lập",
                        "overnight": "Ho Chi Minh City",
                        "meals": ["Breakfast"],
                        "highlights": [],
                        "notes": [],
                        "sense_of_pace": "balanced",
                        "display_date": "2026-09-26",
                        "id": "day_1_7lutsrj",
                    },
                    {
                        "day_number": 2,
                        "destination": "Mekong Delta",
                        "summary": "Chèo thuyền thúng",
                        "overnight": "Ho Chi Minh City",
                        "meals": ["Breakfast"],
                        "highlights": [],
                        "notes": [],
                        "sense_of_pace": "balanced",
                        "display_date": "2026-09-27",
                        "id": "day_2_86fn0b8",
                    },
                    {
                        "day_number": 3,
                        "destination": "Ho Chi Minh City",
                        "summary": "Departure day",
                        "overnight": "Ho Chi Minh City",
                        "meals": ["Breakfast"],
                        "highlights": [],
                        "notes": [],
                        "sense_of_pace": "balanced",
                        "display_date": "2026-09-28",
                        "id": "day_3_m941yp4",
                    },
                ],
                "special_requirements": [
                    "balcony view room",
                    "Dietary: severe nut allergy",
                    "Halal/Prayer: alcohol free",
                    "Mobility: wheelchair assistant",
                    "Health: altitude sensitive",
                ],
                "display_route_text": "Ho Chi Minh City & Mekong Delta",
                "display_travel_dates": None,
            },
            "customer_facts": {
                "customer_name": "nam vu",
                "adults": 10,
                "children": 5,
                "nationality": "Vietnam",
                "guest_profile": "5 children (ages 6, 6, 6, 6, 6)",
                "travel_style": "5 children (ages 6, 6, 6, 6, 6)",
                "market": "Vietnam",
                "party_label": "10 Adults, 5 children (ages 6, 6, 6, 6, 6)",
                "greeting_name": "nam vu",
            },
            "service_facts": {
                "hotels": [],
                "inclusions": [
                    "Airport transfer and arrival greeting",
                    "Private vehicle transfers (7-seat SUV)",
                    "Full-trip private English-speaking tour director/guide",
                    "Domestic flights as specified in the confirmed route",
                    "Boat / Cruise / Rail: Mekong day trip",
                    "Meals included according to plan: Full board",
                    "Accommodations, experiences, admission fees, and exclusive arrangements",
                ],
                "exclusions": [
                    "International flights to and from destinations",
                    "Comprehensive travel insurance",
                    "Personal expenses (beverages, laundry, telephone)",
                    "Optional experiences not specified in the confirmed itinerary",
                    "Tips and gratuities for guides and drivers",
                    "Any services not expressly listed as included",
                ],
                "room_notes": "Family Suite / Multi-bedroom Villa",
            },
            "pricing_facts": {
                "conditions": ["Prices based on 10 guests sharing"],
                "options": [
                    {
                        "id": "opt-standard",
                        "label": "Standard Luxury Option",
                        "currency": "USD",
                        "per_traveler_amount_minor": 50909,
                        "group_total_amount_minor": 700000,
                        "per_adult_amount_minor": 50909,
                        "per_child_amount_minor": None,
                    }
                ],
            },
            "booking_facts": {
                "title": "Journey for nam vu",
                "description": "Custom luxury journey proposal prepared from enquiry details.",
                "items": [],
            },
            "designer_facts": {
                "seller_subtitle": "Luxury Journey Designer",
                "designer_signature": None,
                "designer_kicker": "Personalized Proposal",
                "designer_quote": "Crafting unforgettable bespoke travel experiences across Indochina.",
                "designer_experience": "Over 10 years of luxury travel design excellence.",
                "designer_title": "Senior Travel Designer",
                "cta_body": "Contact your travel designer to personalize this itinerary.",
            },
            "opportunity_id": "req_cdda12b423644000",
            "factMediaSlots": [],
            "content_overrides": {},
            "asset_overrides": {},
            "generation_options": {},
            "retrieval_refs": [],
        }

        # Model validation must succeed without 422 extra_forbidden
        req = CreateQuoteRequestV1.model_validate(payload_data)
        self.assertEqual(req.brand_id, "selvara")
        self.assertEqual(len(req.trip_facts.itinerary), 3)
        self.assertEqual(req.trip_facts.itinerary[0].id, "day_1_7lutsrj")
        self.assertEqual(req.pricing_facts.options[0].per_traveler_amount_minor, 50909)
        self.assertEqual(req.pricing_facts.options[0].per_adult_amount_minor, 50909)
        self.assertIsNone(req.pricing_facts.options[0].per_child_amount_minor)

    async def test_resolver_resolves_canonical_facts_from_user_payload(self):
        payload_data = {
            "brand_id": "selvara",
            "lang": "en",
            "trip_facts": {
                "destinations": ["Ho Chi Minh City", "Mekong Delta"],
                "start_date": "2026-09-26",
                "end_date": "2026-09-28",
                "itinerary": [
                    {
                        "day_number": 1,
                        "destination": "Ho Chi Minh City",
                        "summary": "City tour",
                        "overnight": "Ho Chi Minh City",
                        "id": "day_1_7lutsrj",
                    },
                    {
                        "day_number": 2,
                        "destination": "Mekong Delta",
                        "summary": "Boat trip",
                        "overnight": "Ho Chi Minh City",
                        "id": "day_2_86fn0b8",
                    },
                ],
            },
            "pricing_facts": {
                "options": [
                    {
                        "id": "opt-1",
                        "label": "Standard",
                        "currency": "USD",
                        "group_total_amount_minor": 700000,
                        "per_adult_amount_minor": 50909,
                        "per_child_amount_minor": None,
                    }
                ]
            },
            "customer_facts": {
                "adults": 10,
                "children": 5,
                "travel_style": "Family luxury",
            },
        }

        req = CreateQuoteRequestV1.model_validate(payload_data)
        canonical, resolved = await FactsResolver().resolve(req, mock_resolve_destination)
        self.assertEqual(canonical.trip_facts.destinations, ["Ho Chi Minh City", "Mekong Delta"])
        self.assertEqual(canonical.trip_facts.itinerary[0].id, "day_1_7lutsrj")
        self.assertEqual(canonical.pricing_facts.options[0].per_traveler_amount_minor, 50909)
        self.assertEqual(resolved["durationDays"], 3)
        self.assertEqual(resolved["durationNights"], 2)

    def test_pricing_option_bidirectional_sync(self):
        # 1. When only per_adult_amount_minor is provided
        opt1 = CreateQuotePricingOptionFact.model_validate({
            "label": "Option 1",
            "currency": "USD",
            "group_total_amount_minor": 100000,
            "per_adult_amount_minor": 50000,
        })
        self.assertEqual(opt1.per_traveler_amount_minor, 50000)
        self.assertEqual(opt1.per_adult_amount_minor, 50000)

        # 2. When only per_traveler_amount_minor is provided
        opt2 = CreateQuotePricingOptionFact.model_validate({
            "label": "Option 2",
            "currency": "USD",
            "group_total_amount_minor": 100000,
            "per_traveler_amount_minor": 60000,
        })
        self.assertEqual(opt2.per_traveler_amount_minor, 60000)
        self.assertEqual(opt2.per_adult_amount_minor, 60000)


if __name__ == "__main__":
    unittest.main()
