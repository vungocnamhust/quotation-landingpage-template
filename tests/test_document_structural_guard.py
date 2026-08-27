import unittest

from services.content_value_service import DocumentStructuralDiffError, assert_no_structural_diff, is_structurally_mutable_pointer


def _document():
    return {
        "meta": {"revision": 1},
        "brand": {},
        "trip": {"title": "Old title"},
        "traveler": {"adults": 2, "children": 0, "kidAges": []},
        "itinerary": {"days": [
            {"id": "day-1", "dayNumber": 1, "title": "Day 1", "description": ["old"], "activities": []},
        ]},
        "stays": {"hotels": [{"id": "hotel-1", "sourceFactId": "hotel-1", "roomType": "Deluxe", "editorialIntroduction": "old copy"}]},
        "pricing": {"options": [{"id": "price-1", "groupTotalAmountMinor": 1000000, "currency": "USD"}]},
        "assets": {"hero": {"r2Key": "library/media/old.jpg"}},
        "presentation": {"copyOverrides": {}},
    }


class DocumentStructuralGuardTests(unittest.TestCase):
    def test_content_and_presentation_only_changes_pass(self):
        submitted = _document()
        submitted["trip"]["title"] = "New title"
        submitted["itinerary"]["days"][0]["title"] = "New day title"
        submitted["stays"]["hotels"][0]["editorialIntroduction"] = "New editorial copy"
        submitted["presentation"]["copyOverrides"] = {"hero.primaryCta": "Explore"}
        assert_no_structural_diff(_document(), submitted)

    def test_media_slot_asset_changes_pass(self):
        submitted = _document()
        submitted["assets"]["hero"] = {"r2Key": "library/media/new.jpg"}
        assert_no_structural_diff(_document(), submitted)

    def test_itinerary_day_count_change_is_rejected(self):
        submitted = _document()
        submitted["itinerary"]["days"].append({"id": "day-2", "dayNumber": 2, "title": "", "description": [], "activities": []})
        with self.assertRaises(DocumentStructuralDiffError) as ctx:
            assert_no_structural_diff(_document(), submitted)
        self.assertIn("/itinerary/days", ctx.exception.paths)

    def test_pricing_amount_change_is_rejected(self):
        submitted = _document()
        submitted["pricing"]["options"][0]["groupTotalAmountMinor"] = 2000000
        with self.assertRaises(DocumentStructuralDiffError) as ctx:
            assert_no_structural_diff(_document(), submitted)
        self.assertIn("/pricing/options/0/groupTotalAmountMinor", ctx.exception.paths)

    def test_party_change_is_rejected(self):
        submitted = _document()
        submitted["traveler"]["adults"] = 4
        with self.assertRaises(DocumentStructuralDiffError) as ctx:
            assert_no_structural_diff(_document(), submitted)
        self.assertIn("/traveler/adults", ctx.exception.paths)

    def test_hotel_identity_change_is_rejected(self):
        submitted = _document()
        submitted["stays"]["hotels"][0]["roomType"] = "Suite"
        with self.assertRaises(DocumentStructuralDiffError) as ctx:
            assert_no_structural_diff(_document(), submitted)
        self.assertIn("/stays/hotels/0/roomType", ctx.exception.paths)

    def test_lists_every_offending_path_in_one_pass(self):
        submitted = _document()
        submitted["traveler"]["adults"] = 4
        submitted["pricing"]["options"][0]["currency"] = "VND"
        with self.assertRaises(DocumentStructuralDiffError) as ctx:
            assert_no_structural_diff(_document(), submitted)
        self.assertEqual(set(ctx.exception.paths), {"/traveler/adults", "/pricing/options/0/currency"})

    def test_is_structurally_mutable_pointer_covers_content_presentation_and_media(self):
        self.assertTrue(is_structurally_mutable_pointer("/trip/title"))
        self.assertTrue(is_structurally_mutable_pointer("/presentation/copyOverrides"))
        self.assertTrue(is_structurally_mutable_pointer("/assets/hero"))
        self.assertTrue(is_structurally_mutable_pointer("/assets/hero/r2Key"))
        self.assertTrue(is_structurally_mutable_pointer("/meta/revision"))
        self.assertFalse(is_structurally_mutable_pointer("/traveler/adults"))
        self.assertFalse(is_structurally_mutable_pointer("/pricing/options/0/groupTotalAmountMinor"))


if __name__ == "__main__":
    unittest.main()
