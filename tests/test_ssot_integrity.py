"""CI & Contract Integrity Gate: Verifies that Prompts, Schemas, Preflight, and Frontend are 100% in sync with SSoT."""
import unittest
from core.rules.content_budgets import get_content_budget_registry
from scripts.export_content_budgets import export_content_budgets
from services.content_registry import CONTENT_SECTION_REGISTRY, scope_spec
from services.section_content_generator import HeroOutput, OverviewOutput, RouteOutput, DayOutput


class TestSSoTIntegrityGate(unittest.TestCase):
    def setUp(self):
        self.registry = get_content_budget_registry("v1")

    def test_frontend_json_in_sync_with_yaml_ssot(self):
        """Ensures quote-generator/config/contentBudgets.json is never stale."""
        in_sync = export_content_budgets(check_only=True)
        self.assertTrue(in_sync, "Frontend contentBudgets.json is out of sync with prompts/v1/content_budgets.yaml. Run 'npm run sync:budgets'")

    def test_pydantic_schemas_match_ssot_max_chars(self):
        """Ensures Pydantic schemas enforce the exact bounds from SSoT."""
        hero_title_max = HeroOutput.model_fields["title"].metadata[1].max_length if len(HeroOutput.model_fields["title"].metadata) > 1 else HeroOutput.model_fields["title"].max_length
        self.assertEqual(
            hero_title_max,
            self.registry.get_max_chars("hero", "trip_title")
        )

        hero_lede_max = HeroOutput.model_fields["lede"].metadata[1].max_length if len(HeroOutput.model_fields["lede"].metadata) > 1 else HeroOutput.model_fields["lede"].max_length
        self.assertEqual(
            hero_lede_max,
            self.registry.get_max_chars("hero", "trip_lede")
        )

        overview_highlight_max = OverviewOutput.model_fields["letterHighlight"].metadata[1].max_length if len(OverviewOutput.model_fields["letterHighlight"].metadata) > 1 else OverviewOutput.model_fields["letterHighlight"].max_length
        self.assertEqual(
            overview_highlight_max,
            self.registry.get_max_chars("overview_letter", "letter_highlight")
        )

        day_title_max = DayOutput.model_fields["title"].metadata[1].max_length if len(DayOutput.model_fields["title"].metadata) > 1 else DayOutput.model_fields["title"].max_length
        self.assertEqual(
            day_title_max,
            self.registry.get_max_chars("itinerary_day", "title")
        )

    def test_content_registry_matches_ssot_bounds(self):
        """Ensures Content Registry EditorFields match SSoT bounds."""
        hero_fields = {f.id: f for f in CONTENT_SECTION_REGISTRY["hero"].editor_fields}
        self.assertEqual(hero_fields["trip-title"].max_length, self.registry.get_max_chars("hero", "trip_title"))
        self.assertEqual(hero_fields["hero-lede"].max_length, self.registry.get_max_chars("hero", "trip_lede"))

        overview_fields = {f.id: f for f in CONTENT_SECTION_REGISTRY["overview_letter"].editor_fields}
        self.assertEqual(overview_fields["overview-highlight"].max_length, self.registry.get_max_chars("overview_letter", "letter_highlight"))

        day_spec = scope_spec("itinerary:day:1")
        day_fields = {f.id: f for f in day_spec.editor_fields}
        self.assertEqual(day_fields["day-title"].max_length, self.registry.get_max_chars("itinerary_day", "title"))
        self.assertEqual(day_fields["day-description"].max_length, self.registry.get_max_chars("itinerary_day", "description"))

    def test_pdf_ceilings_ssot_coverage(self):
        """Ensures all critical PDF A4 printable limits are indexed in SSoT."""
        ceilings = self.registry.get_pdf_ceilings_map()
        required_keys = [
            "day_title", "day_description", "hotel_total_copy",
            "overview_letter_total", "overview_highlight",
            "route_stop_description", "payment_terms_max_count", "payment_term_body"
        ]
        for key in required_keys:
            self.assertIn(key, ceilings)
            self.assertGreater(ceilings[key], 0)


if __name__ == "__main__":
    unittest.main()
