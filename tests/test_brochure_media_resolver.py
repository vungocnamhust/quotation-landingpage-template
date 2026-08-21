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

    def test_resolves_vietnamese_diacritics_and_aliases(self):
        catalogue = [
            Candidate("shared/media/vietnam/north/hanoi/hero.jpg", "shared/media/vietnam/north/hanoi", 1800, 900, True),
            Candidate("shared/media/vietnam/north/quang-ninh/ha-long/bay.jpg", "shared/media/vietnam/north/quang-ninh/ha-long", 1800, 900, True),
        ]
        resolver = BrochureMediaResolver(catalogue)
        document = {
            "assets": {},
            "itinerary": {
                "days": [
                    {"destination": "Hà Nội", "images": {}},
                    {"destination": "Vịnh Hạ Long", "images": {}},
                ]
            },
            "stays": {"hotels": []},
        }
        result = resolver.resolve_missing(document=document, quotation_id="quo_vn", lang="vi")
        self.assertTrue(result["hasChanges"])
        self.assertEqual(len(result["patch"]["itinerary"]["days"]), 2)
        self.assertEqual(result["patch"]["itinerary"]["days"][0]["images"]["carousel"][0]["r2Key"], "shared/media/vietnam/north/hanoi/hero.jpg")
        self.assertEqual(result["patch"]["itinerary"]["days"][1]["images"]["carousel"][0]["r2Key"], "shared/media/vietnam/north/quang-ninh/ha-long/bay.jpg")
        self.assertTrue(result["patch"]["assets"]["hero"]["r2Key"])

    def test_resolves_long_hotel_name_token_matching(self):
        catalogue = [
            Candidate("library/media/accommodations/vietnam/north/hanoi/ha-noi/metropole/exterior.jpg", "library/media/accommodations/vietnam/north/hanoi/ha-noi/metropole", 1600, 900, True),
            Candidate("library/media/accommodations/vietnam/north/hanoi/ha-noi/metropole/room.jpg", "library/media/accommodations/vietnam/north/hanoi/ha-noi/metropole", 1600, 900, True),
        ]
        resolver = BrochureMediaResolver(catalogue)
        document = {
            "assets": {},
            "itinerary": {"days": []},
            "stays": {
                "hotels": [
                    {"name": "Sofitel Legend Metropole Hanoi", "city": "Hà Nội", "hotelImage": {}, "roomImage": {}}
                ]
            },
        }
        result = resolver.resolve_missing(document=document, quotation_id="quo_hotel", lang="en")
        self.assertTrue(result["hasChanges"])
        hotel_patch = result["patch"]["stays"]["hotels"][0]
        self.assertEqual(hotel_patch["hotelImage"]["r2Key"], "library/media/accommodations/vietnam/north/hanoi/ha-noi/metropole/exterior.jpg")
        self.assertEqual(hotel_patch["roomImage"]["r2Key"], "library/media/accommodations/vietnam/north/hanoi/ha-noi/metropole/room.jpg")

    def test_reports_has_changes_false_when_already_fully_assigned(self):
        resolver = BrochureMediaResolver(self.catalogue)
        document = {
            "assets": {
                "hero": {"r2Key": "hero.jpg"},
                "itineraryDivider": {"r2Key": "divider1.jpg"},
                "hotelDivider": {"r2Key": "divider2.jpg"},
            },
            "itinerary": {
                "days": [
                    {"images": {"carousel": [{"r2Key": "day1.jpg"}]}}
                ]
            },
            "stays": {
                "hotels": [
                    {"hotelImage": {"r2Key": "h1.jpg"}, "roomImage": {"r2Key": "r1.jpg"}}
                ]
            },
        }
        result = resolver.resolve_missing(document=document, quotation_id="quo_full", lang="en")
        self.assertFalse(result["hasChanges"])
        self.assertEqual(result["appliedCount"], 0)
        self.assertEqual(result["patch"]["assets"], {})
        self.assertEqual(result["patch"]["itinerary"], {})
        self.assertEqual(result["patch"]["stays"], {})



