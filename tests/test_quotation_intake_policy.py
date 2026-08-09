import unittest

from quote_document import CreateQuoteRequestV1
from services.quotation_intake_policy import quotation_intake_missing_inputs


def valid_payload() -> CreateQuoteRequestV1:
    return CreateQuoteRequestV1.model_validate({
        "brand_id": "vietnam_safar",
        "lang": "en",
        "presentation_options": {"template_id": "quote-generator", "travel_designer_id": "designer_1"},
        "trip_facts": {
            "start_date": "2026-10-01",
            "end_date": "2026-10-02",
            "itinerary": [
                {"day_number": 1, "destination": "Hanoi", "overnight": "Hanoi", "summary": "Arrive in Hanoi", "meals": ["Dinner"], "notes": ["Private arrival"]},
                {"day_number": 2, "destination": "Ha Long", "overnight": "Ha Long", "summary": "Cruise the bay", "meals": ["Breakfast"], "notes": ["Pack overnight bag"]},
            ],
        },
        "customer_facts": {"customer_name": "Ada", "nationality": "British", "adults": 2, "children": 0},
        "service_facts": {"hotels": [{"accommodation_id": "acc_1", "destination": "Hanoi", "name": "Example Hotel", "room_type": "Deluxe", "check_in": "2026-10-01", "check_out": "2026-10-02"}]},
    })


class QuotationIntakePolicyTests(unittest.TestCase):
    def test_accepts_complete_intake(self):
        self.assertEqual(quotation_intake_missing_inputs(valid_payload()), [])

    def test_rejects_missing_setup_and_traveller_inputs(self):
        payload = valid_payload()
        payload.presentation_options.template_id = None
        payload.presentation_options.travel_designer_id = None
        payload.customer_facts.adults = 0
        missing = quotation_intake_missing_inputs(payload)
        self.assertIn("presentation_options.template_id", missing)
        self.assertIn("presentation_options.travel_designer_id", missing)
        self.assertIn("customer_facts.adults", missing)

    def test_rejects_route_that_does_not_match_dates(self):
        payload = valid_payload()
        payload.trip_facts.itinerary.pop()
        self.assertIn("trip_facts.itinerary", quotation_intake_missing_inputs(payload))

    def test_requires_day_details_and_selected_accommodation_snapshot(self):
        payload = valid_payload()
        day = payload.trip_facts.itinerary[0]
        day.summary, day.meals, day.notes, day.overnight = None, [], [], None
        hotel = payload.service_facts.hotels[0]
        hotel.accommodation_id, hotel.check_in = None, None
        missing = quotation_intake_missing_inputs(payload)
        self.assertIn("trip_facts.itinerary[0].summary", missing)
        self.assertNotIn("trip_facts.itinerary[0].meals", missing)
        self.assertNotIn("trip_facts.itinerary[0].notes", missing)
        self.assertIn("trip_facts.itinerary[0].overnight", missing)
        self.assertIn("service_facts.hotels[0].accommodation_id", missing)
        self.assertIn("service_facts.hotels[0].check_in", missing)


if __name__ == "__main__":
    unittest.main()
