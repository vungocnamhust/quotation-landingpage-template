import unittest

from services.brochure_media_resolver import BrochureMediaResolver, Candidate, GALLERY_LIMIT


class BrochureMediaResolverTests(unittest.TestCase):
    def setUp(self):
        self.catalogue = [
            Candidate("library/media/vietnam/north/hanoi/ha-noi/hero-a.jpg", "library/media/vietnam/north/hanoi/ha-noi", 1800, 900, True),
            Candidate("library/media/vietnam/north/hanoi/ha-noi/generic-b.jpg", "library/media/vietnam/north/hanoi/ha-noi", 1600, 900, True),
            Candidate("library/media/accommodations/vietnam/north/hanoi/ha-noi/metropole/exterior.jpg", "library/media/accommodations/vietnam/north/hanoi/ha-noi/metropole", 1600, 900, True),
            Candidate("library/media/accommodations/vietnam/north/hanoi/ha-noi/metropole/room.jpg", "library/media/accommodations/vietnam/north/hanoi/ha-noi/metropole", 1600, 900, True),
        ]
        self.document = {"assets": {}, "itinerary": {"days": [{"destinationRef": {"id": "dst_hanoi", "slug": "ha-noi"}, "images": {}}]}, "stays": {"hotels": [{"destinationRef": {"id": "dst_hanoi", "slug": "ha-noi"}, "name": "metropole"}]}}

    def test_resolves_deterministically_without_overwriting_existing_media(self):
        resolver = BrochureMediaResolver(self.catalogue)
        first = resolver.resolve_missing(document=self.document, quotation_id="quo_1", lang="en")
        second = resolver.resolve_missing(document=self.document, quotation_id="quo_1", lang="en")
        self.assertEqual(first["patch"], second["patch"])
        self.assertLessEqual(len(first["patch"]["itinerary"]["days"][0]["images"]["carousel"]), GALLERY_LIMIT)
        self.assertTrue(first["patch"]["assets"]["hero"]["r2Key"])
        self.assertIn("roomImage", first["patch"]["stays"]["hotels"][0])

    def test_existing_slots_are_not_replaced(self):
        document = {**self.document, "assets": {"hero": {"r2Key": "manual.jpg", "status": "ready"}}}
        result = BrochureMediaResolver(self.catalogue).resolve_missing(document=document, quotation_id="quo_1", lang="en")
        self.assertNotIn("hero", result["patch"]["assets"])

    def test_resolves_via_segment_city_fallback(self):
        document = {"assets": {}, "itinerary": {"days": [{"segmentCity": "Hanoi", "images": {}}]}, "stays": {"hotels": []}}
        result = BrochureMediaResolver(self.catalogue).resolve_missing(document=document, quotation_id="quo_1", lang="en")
        self.assertIn("days", result["patch"]["itinerary"])
        self.assertIn("carousel", result["patch"]["itinerary"]["days"][0]["images"])
        self.assertGreater(len(result["patch"]["itinerary"]["days"][0]["images"]["carousel"]), 0)


