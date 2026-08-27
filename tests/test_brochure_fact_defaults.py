import unittest

from pydantic import ValidationError

import main
from quote_document import CreateQuoteRequestV1
from services.content_readiness_service import resolve_content_readiness
from services.skeleton_builder import SkeletonBuilder


class BrochureFactDefaultsTests(unittest.TestCase):
    def test_api_rejects_more_than_four_commercial_options(self):
        with self.assertRaises(ValidationError):
            CreateQuoteRequestV1.model_validate({
                "brand_id": "vietnam_safar",
                "lang": "en",
                "pricing_facts": {"options": [{
                    "id": f"option-{index}", "label": f"Option {index}", "currency": "USD",
                    "per_traveler_amount_minor": 100_00, "group_total_amount_minor": 200_00,
                } for index in range(5)]},
            })

    def test_skeleton_keeps_day_date_and_derives_hotel_date_when_not_overridden(self):
        payload = CreateQuoteRequestV1.model_validate({
            "brand_id": "vietnam_safar",
            "lang": "en",
            "trip_facts": {"itinerary": [{"day_number": 1, "display_date": "2027-03-30", "destination": "Hanoi"}]},
            "service_facts": {"hotels": [{"destination": "Hanoi", "check_in": "2027-03-30", "check_out": "2027-04-02"}]},
        })
        document = SkeletonBuilder().build(
            quotation_id="quo_test",
            payload=payload,
            resolved_facts={"duration": {"label": ""}, "routeLabel": "", "travelDateLabel": ""},
            template="quote-generator",
        )
        self.assertEqual(document["itinerary"]["days"][0]["dayDate"], "2027-03-30")
        self.assertEqual(document["stays"]["hotels"][0]["hotelDate"], "2027-03-30 – 2027-04-02")

    def test_skeleton_uses_brand_boilerplate_for_empty_inclusions_and_booking_terms(self):
        payload = CreateQuoteRequestV1.model_validate({
            "brand_id": "capella_travel",
            "lang": "en",
        })
        document = SkeletonBuilder().build(
            quotation_id="quo_boilerplate",
            payload=payload,
            resolved_facts={"duration": {"label": ""}, "routeLabel": "", "travelDateLabel": ""},
            template="quote-generator",
        )

        inclusions_section = document["content"]["sections"]["inclusions_exclusions"]
        booking_section = document["content"]["sections"]["booking_terms"]
        self.assertTrue(inclusions_section["blocks"])
        self.assertTrue(booking_section["blocks"])
        self.assertIn("premium airport transfers", " ".join(inclusions_section["blocks"][0]["leftItems"]))

        readiness = resolve_content_readiness(document, fact_missing_inputs=[])
        blocker_sections = {
            item["sectionType"]: item
            for item in readiness
            if item["sectionType"] in {"inclusions_exclusions", "booking_terms"}
        }
        self.assertIsNone(blocker_sections["inclusions_exclusions"]["status"])
        self.assertIsNone(blocker_sections["booking_terms"]["status"])

    def test_designer_profile_snapshot_keeps_the_canonical_r2_portrait(self):
        document = {"designer": {"quote": "Quotation-owned editorial copy"}}

        main._apply_travel_designer_snapshot(document, {
            "id": "td_1",
            "name": "Eddie",
            "email": "sales@example.com",
            "phone": "+84 913 393 119",
            "imageR2Key": "library/team/eddie/portrait.jpg",
        })

        self.assertEqual(document["designer"]["profileId"], "td_1")
        self.assertEqual(document["designer"]["image"]["r2Key"], "library/team/eddie/portrait.jpg")
        self.assertEqual(document["designer"]["quote"], "Quotation-owned editorial copy")


if __name__ == "__main__":
    unittest.main()
