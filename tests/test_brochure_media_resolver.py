import unittest

from services.brochure_media_resolver import BrochureMediaResolver, Candidate, GALLERY_LIMIT, _matches_destination
from services.media_default_service import MediaDefaultService


class BrochureMediaResolverTests(unittest.TestCase):
    def setUp(self):
        self.catalogue = [
            Candidate("library/media/vietnam/north/ha-noi/hero-a.jpg", "library/media/vietnam/north/ha-noi", 1800, 900, True),
            Candidate("library/media/vietnam/north/ha-noi/generic-b.jpg", "library/media/vietnam/north/ha-noi", 1600, 900, True),
            Candidate("library/media/accommodations/vietnam/north/ha-noi/metropole-hanoi/exteriors/exterior.jpg", "library/media/accommodations/vietnam/north/ha-noi/metropole-hanoi/exteriors", 1600, 900, True),
            Candidate("library/media/accommodations/vietnam/north/ha-noi/metropole-hanoi/interiors/room.jpg", "library/media/accommodations/vietnam/north/ha-noi/metropole-hanoi/interiors", 1600, 900, True),
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
            Candidate("library/media/accommodations/vietnam/north/ha-noi/metropole-hanoi/exteriors/exterior.jpg", "library/media/accommodations/vietnam/north/ha-noi/metropole-hanoi/exteriors", 1600, 900, True),
            Candidate("library/media/accommodations/vietnam/north/ha-noi/metropole-hanoi/interiors/room.jpg", "library/media/accommodations/vietnam/north/ha-noi/metropole-hanoi/interiors", 1600, 900, True),
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
        self.assertEqual(hotel_patch["hotelImage"]["r2Key"], "library/media/accommodations/vietnam/north/ha-noi/metropole-hanoi/exteriors/exterior.jpg")
        self.assertEqual(hotel_patch["roomImage"]["r2Key"], "library/media/accommodations/vietnam/north/ha-noi/metropole-hanoi/interiors/room.jpg")

    def test_two_hotels_in_the_same_city_never_swap_images(self):
        """R3: a destination-name token embedded in a sibling hotel's slug
        (both hotels are `...-hanoi`) must never satisfy tier-1 for the
        other hotel — only the candidate's own {hotel-slug} segment can."""
        catalogue = [
            Candidate("accommodations/vietnam/north/ha-noi/metropole-hanoi/exteriors/a.jpg", "accommodations/vietnam/north/ha-noi/metropole-hanoi/exteriors", 1600, 900, True),
            Candidate("accommodations/vietnam/north/ha-noi/lotte-hanoi/exteriors/b.jpg", "accommodations/vietnam/north/ha-noi/lotte-hanoi/exteriors", 1600, 900, True),
        ]
        resolver = BrochureMediaResolver(catalogue)
        document = {
            "assets": {},
            "itinerary": {"days": []},
            "stays": {"hotels": [{"name": "Metropole Hanoi", "city": "Hà Nội", "hotelImage": {}, "roomImage": {}}]},
        }
        result = resolver.resolve_missing(document=document, quotation_id="quo_two_hotels", lang="en")
        hotel_patch = result["patch"]["stays"]["hotels"][0]
        self.assertEqual(hotel_patch["hotelImage"]["r2Key"], "accommodations/vietnam/north/ha-noi/metropole-hanoi/exteriors/a.jpg")

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

    def test_partial_gallery_is_topped_up_preserving_the_manual_image_and_its_position(self):
        document = {
            "assets": {},
            "itinerary": {"days": [{"destination": "Hanoi", "images": {"carousel": [{"r2Key": "manual.jpg", "source": "manual", "altText": "Keep me"}]}}]},
            "stays": {"hotels": []},
        }
        result = BrochureMediaResolver(self.catalogue).resolve_missing(document=document, quotation_id="quo_manual", lang="en")
        carousel = result["patch"]["itinerary"]["days"][0]["images"]["carousel"]
        self.assertLessEqual(len(carousel), GALLERY_LIMIT)
        self.assertEqual(carousel[0], {"r2Key": "manual.jpg", "source": "manual", "altText": "Keep me"})
        self.assertNotIn("manual.jpg", [item["r2Key"] for item in carousel[1:]])

    def test_full_gallery_is_never_touched_even_if_shorter_than_gallery_limit_would_prefer(self):
        document = {
            "assets": {},
            "itinerary": {"days": [{"destination": "Hanoi", "images": {"carousel": [
                {"r2Key": "one.jpg", "source": "manual"},
                {"r2Key": "two.jpg", "source": "manual"},
                {"r2Key": "three.jpg", "source": "manual"},
            ]}}]},
            "stays": {"hotels": []},
        }
        result = BrochureMediaResolver(self.catalogue).resolve_missing(document=document, quotation_id="quo_full_gallery", lang="en")
        self.assertNotIn("days", result["patch"]["itinerary"])

    def test_destination_id_exact_match_is_a_tier_0_signal_ahead_of_string_aliases(self):
        # D6: a candidate synced with structured metadata should match on
        # its real DestinationCatalog.id even when the alias set is
        # deliberately unhelpful for path-string matching.
        structured = Candidate("shared/media/random/unrelated/name/x.jpg", "shared/media/random/unrelated/name", destination_id="dst_hanoi")
        self.assertTrue(_matches_destination(structured, {"dst_hanoi"}))

    def test_destination_id_mismatch_falls_back_to_string_aliases(self):
        structured = Candidate("shared/media/vietnam/north/ha-noi/x.jpg", "shared/media/vietnam/north/ha-noi", destination_id="dst_other")
        self.assertTrue(_matches_destination(structured, {"ha-noi"}))

    def test_candidate_without_destination_id_still_matches_by_path_string(self):
        legacy = Candidate("shared/media/vietnam/north/ha-noi/x.jpg", "shared/media/vietnam/north/ha-noi")
        self.assertTrue(_matches_destination(legacy, {"ha-noi"}))

    def test_candidate_asset_category_is_derived_from_the_r2_key_not_a_stored_field(self):
        exterior = Candidate("accommodations/vietnam/north/ha-noi/metropole-hanoi/exteriors/a.jpg", "accommodations/vietnam/north/ha-noi/metropole-hanoi/exteriors")
        interior = Candidate("accommodations/vietnam/north/ha-noi/metropole-hanoi/interiors/a.jpg", "accommodations/vietnam/north/ha-noi/metropole-hanoi/interiors")
        non_accommodation = Candidate("shared/media/vietnam/hero.jpg", "shared/media/vietnam")
        self.assertEqual(exterior.asset_category, "exteriors")
        self.assertEqual(interior.asset_category, "interiors")
        self.assertIsNone(non_accommodation.asset_category)

    def test_resolver_rejects_preview_and_published_candidates_even_if_marked_active(self):
        # R5 layer 2: defense-in-depth even if a preview/published object
        # somehow reaches the resolver (layer 1 is the repository query).
        sneaky = [
            Candidate("shared/media/vietnam/north/ha-noi/preview/x.jpg", "shared/media/vietnam/north/ha-noi/preview"),
            Candidate("shared/media/vietnam/north/ha-noi/published/x.jpg", "shared/media/vietnam/north/ha-noi/published"),
            Candidate("shared/media/vietnam/north/ha-noi/legit.jpg", "shared/media/vietnam/north/ha-noi"),
        ]
        resolver = BrochureMediaResolver(sneaky)
        self.assertEqual([c.r2_key for c in resolver.candidates], ["shared/media/vietnam/north/ha-noi/legit.jpg"])

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
