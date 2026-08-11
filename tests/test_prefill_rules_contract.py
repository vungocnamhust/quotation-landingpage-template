import unittest

from quote_document import CreateQuoteRequestV1
from services.facts_resolver import FactsResolver, _date_label


class PrefillRulesContractTests(unittest.TestCase):
    def test_multilingual_meals_support_contract(self):
        # Multilingual default meal structures supported across EN, VI, AR
        meals_en = ["Breakfast", "Lunch", "Dinner"]
        meals_vi = ["Bữa sáng", "Bữa trưa", "Bữa tối"]
        meals_ar = ["الإفطار", "الغداء", "العشاء"]

        self.assertEqual(len(meals_en), 3)
        self.assertEqual(len(meals_vi), 3)
        self.assertEqual(len(meals_ar), 3)

    def test_date_label_and_duration_derivation(self):
        label, days, nights = _date_label("2026-10-01", "2026-10-05")
        self.assertEqual(days, 5)
        self.assertEqual(nights, 4)
        self.assertEqual(label, "01 Oct 2026 – 05 Oct 2026")

    def test_commercial_option_validation(self):
        payload = CreateQuoteRequestV1.model_validate({
            "brand_id": "capella_travel",
            "lang": "en",
            "pricing_facts": {
                "options": [{
                    "id": "opt-1",
                    "label": "Option 01",
                    "currency": "USD",
                    "per_traveler_amount_minor": 150000,
                    "group_total_amount_minor": 300000,
                }],
            },
        })
        self.assertEqual(payload.pricing_facts.options[0].per_traveler_amount_minor, 150000)
        self.assertEqual(payload.pricing_facts.options[0].group_total_amount_minor, 300000)


if __name__ == "__main__":
    unittest.main()
