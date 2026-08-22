"""Unit tests for content_budgets SSoT loader."""
import unittest
from core.rules.content_budgets import get_content_budget_registry


class TestContentBudgets(unittest.TestCase):
    def setUp(self):
        self.registry = get_content_budget_registry("v1")

    def test_loads_all_key_scopes(self):
        scopes = {"hero", "overview_letter", "route", "itinerary", "itinerary_day", "hotel_plan", "payment_terms"}
        for scope in scopes:
            self.assertIn(scope, self.registry._specs)

    def test_day_description_has_buffer_and_limits(self):
        spec = self.registry.get_spec("itinerary_day", "description")
        self.assertIsNotNone(spec)
        self.assertEqual(spec.max_chars, 1200)
        self.assertEqual(spec.pdf_ceiling_chars, 1150)
        self.assertEqual(spec.buffer_chars, 350)
        self.assertEqual(spec.target_words, "~120 words")

    def test_pdf_ceilings_map(self):
        ceilings = self.registry.get_pdf_ceilings_map()
        self.assertEqual(ceilings["day_title"], 170)
        self.assertEqual(ceilings["day_description"], 1150)
        self.assertEqual(ceilings["hotel_total_copy"], 2100)
        self.assertEqual(ceilings["overview_letter_total"], 4000)
        self.assertEqual(ceilings["route_stop_description"], 500)
        self.assertEqual(ceilings["payment_terms_max_count"], 4)
        self.assertEqual(ceilings["payment_term_body"], 1600)

    def test_export_to_dict(self):
        data = self.registry.to_dict()
        self.assertEqual(data["version"], "v1")
        self.assertIn("pdfCeilings", data)
        self.assertIn("budgets", data)
        self.assertIn("hero", data["budgets"])


if __name__ == "__main__":
    unittest.main()
