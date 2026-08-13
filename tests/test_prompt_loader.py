import unittest
from prompts.loader import get_prompt_loader

class TestPromptLoader(unittest.TestCase):
    def test_prompt_loader_v1_hero(self):
        loader = get_prompt_loader("v1")
        bundle = loader.build_prompt_bundle(
            scope="hero",
            brand_name="Vietnam Safar",
            brand_tone="warm luxury",
            vocabulary=["authentic"],
            avoid=["cheap"],
            mode="storytelling",
            effective_instruction="Craft an evocative title",
            facts_snapshot={"destinations": ["Hanoi", "Halong Bay"]},
            brand_id="vietnam_safar",
        )
        self.assertEqual(bundle.version, "v1")
        self.assertEqual(bundle.scope, "hero")
        self.assertIn("Vietnam Safar", bundle.system_prompt)
        self.assertIn("Must show clear detail, easy to read, and simple to understand", bundle.system_prompt)
        self.assertIn("Storytelling mode", bundle.mode_contract)
        self.assertIn("Craft an evocative title", bundle.user_prompt)

    def test_prompt_loader_ground_rule_indexing(self):
        loader = get_prompt_loader("v1")

        # overview_letter gets GR-7030 only
        gr_overview = loader.get_active_ground_rules("overview_letter")
        gr_ids_overview = [r["id"] for r in gr_overview]
        self.assertIn("GR-7030", gr_ids_overview)
        self.assertNotIn("GR-TOUR-FULLDAY", gr_ids_overview)

        # itinerary_day with activities gets GR-TOUR-FULLDAY
        gr_day_tour = loader.get_active_ground_rules("itinerary:day:1", {"activities": ["City tour"]})
        gr_ids_tour = [r["id"] for r in gr_day_tour]
        self.assertIn("GR-7030", gr_ids_tour)
        self.assertIn("GR-DAY-NAMING", gr_ids_tour)
        self.assertIn("GR-TOUR-FULLDAY", gr_ids_tour)
        self.assertNotIn("GR-CITY-INTRO", gr_ids_tour)

        # itinerary_day with city only gets GR-CITY-INTRO
        gr_day_city = loader.get_active_ground_rules("itinerary:day:1", {"destination": "Hanoi"})
        gr_ids_city = [r["id"] for r in gr_day_city]
        self.assertIn("GR-CITY-INTRO", gr_ids_city)
        self.assertNotIn("GR-TOUR-FULLDAY", gr_ids_city)

    def test_prompt_loader_brands_and_modes(self):
        loader = get_prompt_loader("v1")

        # Test Capella Travel & Detailed mode
        bundle_capella = loader.build_prompt_bundle(
            scope="overview_letter",
            brand_name="Capella Travel",
            brand_tone="editorial luxury",
            vocabulary=["bespoke"],
            avoid=["generic"],
            mode="detailed",
            effective_instruction="",
            facts_snapshot={},
            brand_id="capella_travel",
        )
        self.assertIn("cosmopolitan, polished", bundle_capella.system_prompt)
        self.assertIn("Detailed mode", bundle_capella.mode_contract)

        # Test Selvara Journeys & Storytelling mode
        bundle_selvara = loader.build_prompt_bundle(
            scope="itinerary:day:1",
            brand_name="Selvara Journeys",
            brand_tone="quiet luxury",
            vocabulary=["sanctuary"],
            avoid=["rushed"],
            mode="storytelling",
            effective_instruction="",
            facts_snapshot={},
            brand_id="selvara",
        )
        self.assertIn("nature, tranquility, wellness", bundle_selvara.system_prompt)
        self.assertIn("Storytelling mode", bundle_selvara.mode_contract)

    def test_prompt_recipes_and_dynamic_filtering(self):
        loader = get_prompt_loader("v1")

        # Test recipes reading
        recipes = loader.get_recipes()
        self.assertIn("hero", recipes)
        self.assertIn("itinerary_day", recipes)
        
        recipe_day = loader.get_recipe("itinerary:day:1")
        self.assertEqual(recipe_day.get("name"), "Itinerary Day Recipe")

        # Test disabling rules dynamically
        bundle_filtered = loader.build_prompt_bundle(
            scope="itinerary:day:1",
            brand_name="Selvara Journeys",
            brand_tone="quiet luxury",
            vocabulary=["sanctuary"],
            avoid=["rushed"],
            mode="storytelling",
            effective_instruction="",
            facts_snapshot={"activities": ["Trekking"]},
            brand_id="selvara",
            disabled_rule_ids=["GR-TOUR-FULLDAY"],
        )
        self.assertNotIn("GR-TOUR-FULLDAY", bundle_filtered.system_prompt)

    def test_sanitization_and_brand_tone_fallback(self):
        loader = get_prompt_loader("v1")

        # Test brand tone and vocabulary fallback when passed empty values
        bundle = loader.build_prompt_bundle(
            scope="itinerary",
            brand_name="Capella Travel",
            brand_tone="",
            vocabulary=[],
            avoid=[],
            mode="detailed",
            effective_instruction="Summarize itinerary",
            facts_snapshot={
                "trip_facts.itinerary": [
                    {"day_number": 1, "destination": "Hanoi", "sense_of_pace": None, "highlights": []}
                ]
            },
            brand_id="capella_travel",
        )

        # Assert no "Tone: " empty string or "Preferred vocabulary: None" in system prompt
        self.assertNotIn("Tone: \n", bundle.system_prompt)
        self.assertNotIn("Tone:\n", bundle.system_prompt)
        self.assertNotIn("Preferred vocabulary: None", bundle.system_prompt)
        self.assertIn("Editorial luxury", bundle.system_prompt)
        self.assertIn("Preferred vocabulary: elegant", bundle.system_prompt)

        # Assert no "sense_of_pace": null in user prompt JSON
        self.assertNotIn('"sense_of_pace": null', bundle.user_prompt)
        self.assertNotIn('"highlights": []', bundle.user_prompt)


if __name__ == "__main__":
    unittest.main()
