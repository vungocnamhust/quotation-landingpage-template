import unittest
from services.travel_style_service import TravelStyleService, CATEGORY_METADATA


class TravelStyleContractTests(unittest.TestCase):
    def test_category_metadata_completeness(self):
        """Verify the 4 standard professional tourism categories exist in CATEGORY_METADATA."""
        expected_categories = {"group_composition", "tour_type", "purpose", "interest_experience"}
        self.assertEqual(set(CATEGORY_METADATA.keys()), expected_categories)

        for cat_key, meta in CATEGORY_METADATA.items():
            self.assertIn("title_en", meta)
            self.assertIn("title_vi", meta)
            self.assertIn("display_order", meta)

    def test_sync_travel_style_facts(self):
        """Verify bidirectional sync between travel_style and guest_profile in customer_facts."""
        facts = {
            "customer_name": "Test Customer",
            "travel_style": "Couple, Private Tour",
        }
        synced = TravelStyleService.sync_travel_style_facts(facts)
        self.assertEqual(synced["travel_style"], "Couple, Private Tour")
        self.assertEqual(synced["guest_profile"], "Couple, Private Tour")

        legacy_facts = {
            "customer_name": "Legacy Customer",
            "guest_profile": "Solo Traveler",
        }
        synced_legacy = TravelStyleService.sync_travel_style_facts(legacy_facts)
        self.assertEqual(synced_legacy["travel_style"], "Solo Traveler")
        self.assertEqual(synced_legacy["guest_profile"], "Solo Traveler")


if __name__ == "__main__":
    unittest.main()
