import unittest

from services.content_value_service import (
    ContentAclDeniedError,
    ContentTargetMissingError,
    ContentValueBudgetError,
    ContentValueMutationInput,
    ContentValueService,
)


def _document():
    return {
        "trip": {"title": "Old title", "lede": "Old lede"},
        "narrative": {"letterIntro": "Old intro"},
        "itinerary": {"days": [
            {"sourceFactId": "day-1", "dayNumber": 1, "title": "Day 1", "description": ["old desc"], "activities": "old"},
            {"sourceFactId": "day-2", "dayNumber": 2, "title": "Day 2", "description": ["old desc 2"], "activities": "old 2"},
        ]},
        "stays": {"hotels": [{"sourceFactId": "hotel-1", "editorialIntroduction": "old hotel copy"}]},
        "route": {"staySegments": [{"id": "seg-1", "mapSegmentDesc": "old segment"}]},
        "pricing": {"kicker": "old kicker"},
    }


class ContentValueServiceTests(unittest.TestCase):
    def test_apply_writes_a_static_content_source(self):
        result = ContentValueService.apply(_document(), [ContentValueMutationInput("/trip/title", "New title")])
        self.assertEqual(result.document["trip"]["title"], "New title")
        self.assertEqual(result.touched_scopes, ("hero",))
        self.assertEqual(result.updated_sources, ("/trip/title",))

    def test_apply_writes_an_id_keyed_itinerary_day_source(self):
        result = ContentValueService.apply(_document(), [ContentValueMutationInput("/itinerary/days/day-2/description/0", "New day 2 copy")])
        self.assertEqual(result.document["itinerary"]["days"][1]["description"][0], "New day 2 copy")
        self.assertEqual(result.document["itinerary"]["days"][0]["description"][0], "old desc")
        self.assertEqual(result.touched_scopes, ("itinerary:day:day-2",))

    def test_apply_writes_hotel_and_route_segment_sources(self):
        result = ContentValueService.apply(_document(), [
            ContentValueMutationInput("/stays/hotels/hotel-1/editorialIntroduction", "New hotel copy"),
            ContentValueMutationInput("/route/staySegments/seg-1/mapSegmentDesc", "New segment copy"),
        ])
        self.assertEqual(result.document["stays"]["hotels"][0]["editorialIntroduction"], "New hotel copy")
        self.assertEqual(result.document["route"]["staySegments"][0]["mapSegmentDesc"], "New segment copy")
        self.assertEqual(set(result.touched_scopes), {"hotel_plan", "route"})

    def test_apply_does_not_mutate_the_input_document(self):
        original = _document()
        ContentValueService.apply(original, [ContentValueMutationInput("/trip/title", "New title")])
        self.assertEqual(original["trip"]["title"], "Old title")

    def test_apply_rejects_a_source_outside_the_content_acl(self):
        with self.assertRaises(ContentAclDeniedError):
            ContentValueService.apply(_document(), [ContentValueMutationInput("/trip/startDate", "2026-01-01")])
        with self.assertRaises(ContentAclDeniedError):
            ContentValueService.apply(_document(), [ContentValueMutationInput("/pricing_facts/options", "x")])

    def test_apply_rejects_a_deleted_or_unknown_entity(self):
        with self.assertRaises(ContentTargetMissingError):
            ContentValueService.apply(_document(), [ContentValueMutationInput("/itinerary/days/day-9/title", "x")])
        with self.assertRaises(ContentTargetMissingError):
            ContentValueService.apply(_document(), [ContentValueMutationInput("/stays/hotels/hotel-9/editorialIntroduction", "x")])

    def test_apply_rejects_a_value_over_its_content_budget(self):
        with self.assertRaises(ContentValueBudgetError):
            ContentValueService.apply(_document(), [ContentValueMutationInput("/pricing/kicker", "x" * 200)])

    def test_apply_processes_multiple_mutations_atomically_within_the_batch(self):
        result = ContentValueService.apply(_document(), [
            ContentValueMutationInput("/trip/title", "New title"),
            ContentValueMutationInput("/trip/lede", "New lede"),
            ContentValueMutationInput("/itinerary/days/day-1/title", "New day 1 title"),
        ])
        self.assertEqual(result.document["trip"]["title"], "New title")
        self.assertEqual(result.document["trip"]["lede"], "New lede")
        self.assertEqual(result.document["itinerary"]["days"][0]["title"], "New day 1 title")
        self.assertEqual(set(result.touched_scopes), {"hero", "itinerary:day:day-1"})

    def test_apply_raises_before_any_write_when_one_mutation_in_the_batch_is_invalid(self):
        document = _document()
        with self.assertRaises(ContentAclDeniedError):
            ContentValueService.apply(document, [
                ContentValueMutationInput("/trip/title", "New title"),
                ContentValueMutationInput("/pricing_facts/options", "x"),
            ])


if __name__ == "__main__":
    unittest.main()
