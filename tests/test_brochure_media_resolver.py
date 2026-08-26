import unittest

from services.brochure_media_resolver import BrochureMediaResolver, Candidate, GALLERY_LIMIT
from services.media_default_service import MediaDefaultService


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
        self.assertTrue(first["patch"]["assets"]["staysDivider"]["r2Key"])
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
                "staysDivider": {"r2Key": "divider-stays.jpg"},
                "hotelDivider": {"r2Key": "divider2.jpg"},
            },
            "itinerary": {
                "days": [
                    {"images": {"carousel": [{"r2Key": "day1.jpg"}, {"r2Key": "day2.jpg"}, {"r2Key": "day3.jpg"}]}}
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

    def test_catalogue_shortfall_keeps_distinct_partial_gallery(self):
        catalogue = [
            Candidate("library/media/vietnam/north/hanoi/only.jpg", "library/media/vietnam/north/hanoi", 1600, 900, True),
        ]
        document = {
            "assets": {},
            "itinerary": {"days": [{"destination": "Hanoi", "images": {}}]},
            "stays": {"hotels": []},
        }
        result = BrochureMediaResolver(catalogue).resolve_missing(document=document, quotation_id="quo_short", lang="en")
        carousel = result["patch"]["itinerary"]["days"][0]["images"]["carousel"]
        self.assertEqual([asset["r2Key"] for asset in carousel], [catalogue[0].r2_key])
        self.assertEqual(
            next(item for item in result["rationale"] if item["fieldId"] == "itinerary.days.0.gallery")["reason"],
            "insufficient_catalogue_media",
        )

    def test_manual_carousel_is_not_overwritten(self):
        document = {
            "assets": {},
            "itinerary": {"days": [{"destination": "Hanoi", "images": {"carousel": [{"r2Key": "manual.jpg", "source": "manual"}]}}]},
            "stays": {"hotels": []},
        }
        result = BrochureMediaResolver(self.catalogue).resolve_missing(document=document, quotation_id="quo_manual", lang="en")
        self.assertNotIn("days", result["patch"]["itinerary"])

    def test_required_missing_slots_enforces_exact_gallery_cardinality_and_hotel_media(self):
        document = {
            "assets": {"hero": {"r2Key": "hero.jpg"}},
            "itinerary": {"days": [{"images": {"carousel": [{"r2Key": "one.jpg"}, {"r2Key": "two.jpg"}]}}]},
            "stays": {"hotels": [{"hotelImage": {"r2Key": "hotel.jpg"}, "roomImage": {}}]},
        }
        self.assertEqual(
            MediaDefaultService.required_missing_slots(document),
            ["itinerary.days.0.gallery", "stays.hotels.0.roomImage"],
        )

    def test_route_hotel_image_sync_uses_source_fact_identity(self):
        first_image = {"r2Key": "hotel-a.jpg"}
        second_image = {"r2Key": "hotel-b.jpg"}
        document = {
            "stays": {
                "hotels": [
                    {"sourceFactId": "fact-a", "name": "Same Name", "city": "Hanoi"},
                    {"sourceFactId": "fact-b", "name": "Same Name", "city": "Hanoi"},
                ]
            },
            "route": {
                "staySegments": [
                    {"hotelSourceFactId": "fact-a", "hotelImage": first_image},
                    {"hotelSourceFactId": "fact-b", "hotelImage": {"r2Key": "old-b.jpg"}},
                ]
            },
        }
        MediaDefaultService.apply_patch(document, {"stays": {"hotels": {"1": {"hotelImage": second_image}}}})
        self.assertEqual(document["route"]["staySegments"][0]["hotelImage"], first_image)
        self.assertEqual(document["route"]["staySegments"][1]["hotelImage"], second_image)
