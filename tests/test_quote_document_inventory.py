from __future__ import annotations

import unittest
from quote_document import (
    QuoteDocumentV1,
    QuoteDocumentTrip,
    QuoteDocumentRouteSegment,
    CreateQuoteRequestV1,
)
from services.skeleton_builder import SkeletonBuilder


class QuoteDocumentInventoryTests(unittest.TestCase):
    def test_trip_model_has_no_price_basis_field(self):
        self.assertNotIn("priceBasis", QuoteDocumentTrip.model_fields)

    def test_route_segment_has_no_map_segment_duration_field(self):
        self.assertNotIn("mapSegmentDuration", QuoteDocumentRouteSegment.model_fields)

    def test_skeleton_builder_does_not_emit_deprecated_fields(self):
        payload = CreateQuoteRequestV1.model_validate({
            "brand_id": "selvara",
            "lang": "en",
            "trip_facts": {
                "destinations": ["Hanoi", "Halong"],
                "start_date": "2026-11-01",
                "end_date": "2026-11-04",
                "itinerary": [
                    {"day_number": 1, "destination": "Hanoi", "overnight": "Hanoi", "summary": "Arrival"},
                    {"day_number": 2, "destination": "Halong", "overnight": "Halong", "summary": "Cruise"},
                ],
            },
            "customer_facts": {
                "customer_name": "Test Traveler",
                "adults": 2,
            },
            "pricing_facts": {
                "options": [{
                    "id": "opt-1",
                    "label": "Classic",
                    "currency": "USD",
                    "group_total_amount_minor": 500000,
                    "per_traveler_amount_minor": 250000,
                }],
            },
            "service_facts": {
                "hotels": [
                    {"name": "Hotel 1", "destination": "Hanoi", "check_in": "2026-11-01", "check_out": "2026-11-02"},
                    {"name": "Hotel 2", "destination": "Halong", "check_in": "2026-11-02", "check_out": "2026-11-03"},
                ],
            },
            "designer_facts": {
                "designer_name": "Eddie",
            },
        })

        resolved_facts = {
            "duration": {"label": "4 Days / 3 Nights", "days": 4, "nights": 3},
            "routeLabel": "Hanoi · Halong",
            "travelDateLabel": "01 Nov 2026 – 04 Nov 2026",
            "itinerary": [],
            "hotels": [],
        }

        builder = SkeletonBuilder()
        doc = builder.build(
            quotation_id="quo_test_123",
            payload=payload,
            resolved_facts=resolved_facts,
            template="itinerary-imagery-v1",
        )

        # Verify no priceBasis in trip
        self.assertNotIn("priceBasis", doc.get("trip", {}))

        # Verify no mapSegmentDuration in staySegments
        for segment in (doc.get("route") or {}).get("staySegments") or []:
            self.assertNotIn("mapSegmentDuration", segment)

        # Verify days do not have legacy fact fields left over
        for day in (doc.get("itinerary") or {}).get("days") or []:
            self.assertNotIn("factSummary", day)
            self.assertNotIn("factHighlights", day)

    def test_legacy_snapshot_with_deprecated_fields_still_parses(self):
        legacy_doc = {
            "meta": {"id": "quo_legacy", "quotationId": "quo_legacy", "quotationNumber": "Q-001", "lang": "en", "brandId": "selvara", "template": "quote-generator", "revision": 1, "status": "draft", "contentSchemaVersion": 1},
            "trip": {"title": "Legacy Trip", "priceBasis": "per person"},
            "route": {
                "title": "Route",
                "staySegments": [
                    {"id": "seg-1", "displayName": "Hanoi", "mapSegmentDuration": "2 Days"}
                ],
            },
            "itinerary": {
                "title": "Itinerary",
                "days": [
                    {"id": "day-1", "dayNumber": 1, "title": "Day 1", "labelHighlights": "Highlights:"}
                ],
            },
            "traveler": {"customerName": "John Doe"},
            "pricing": {"title": "Pricing"},
            "stays": {"hotels": []},
            "content": {
                "sections": {
                    "inclusions": {"title": "Inclusions", "items": ["Item 1"]},
                    "booking_terms": {"title": "Booking Terms", "items": ["Deposit: 20%"]},
                }
            },
            "designer": {"name": "Eddie"},
        }

        # Tolerant parsing of snapshot containing extra deprecated keys
        validated = QuoteDocumentV1.model_validate(legacy_doc)
        self.assertEqual(validated.trip.title, "Legacy Trip")
        self.assertEqual(validated.itinerary.days[0].title, "Day 1")


if __name__ == "__main__":
    unittest.main()
