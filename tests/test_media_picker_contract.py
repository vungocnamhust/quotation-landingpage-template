import unittest

from core.config import settings
from quote_document import QuoteDocumentV1, build_default_sections


class MediaPickerContractTests(unittest.TestCase):
    def test_library_roots_are_unique_and_cover_taxonomy_roots(self):
        self.assertEqual(len(settings.media_library_roots), len(set(settings.media_library_roots)))
        self.assertTrue({"accommodations", "team"}.issubset(settings.media_library_roots))

    def test_quote_asset_ref_preserves_r2_key(self):
        document = QuoteDocumentV1.model_validate(
            {
                "meta": {"quotationId": "quo_test", "contentSchemaVersion": 1},
                "content": {"sections": {}},
                "layout": {"sections": [section.model_dump(mode="json") for section in build_default_sections()]},
                "itinerary": {"days": [{"id": "day-1", "dayNumber": 1, "images": {"hero": {"r2Key": "vietnam/north/hanoi/hero.jpg"}}}]},
            }
        )
        self.assertEqual(document.itinerary.days[0].images.hero.r2Key, "vietnam/north/hanoi/hero.jpg")
