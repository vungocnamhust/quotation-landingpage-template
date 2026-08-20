from __future__ import annotations

import unittest
from services.rooming_heuristic_service import (
    DEFAULT_ROOMING_RULES,
    calculate_min_rooms,
    format_suggestion_template,
    RoomingHeuristicService,
)
from db.models.rooming_heuristic import RoomingHeuristicRule


class DummySession:
    """Mock async session for testing service evaluation logic without database connection."""

    def __init__(self, rules: list[RoomingHeuristicRule]) -> None:
        self._rules = rules

    async def get(self, model, entity_id):
        for r in self._rules:
            if r.id == entity_id:
                return r
        return None

    def add(self, entity):
        self._rules.append(entity)

    async def flush(self):
        pass


class RoomingHeuristicsTests(unittest.IsolatedAsyncioTestCase):
    def test_default_rules_completeness(self):
        """Verify all 7 standard industry rules are present in DEFAULT_ROOMING_RULES."""
        rule_ids = {r["id"] for r in DEFAULT_ROOMING_RULES}
        expected_ids = {
            "rule_solo_traveler",
            "rule_couple_no_kids",
            "rule_family_young_kids",
            "rule_family_teen_kids",
            "rule_three_adults",
            "rule_quad_adults",
            "rule_large_family_multigen",
        }
        self.assertTrue(expected_ids.issubset(rule_ids))

        for r in DEFAULT_ROOMING_RULES:
            self.assertIn("name", r)
            self.assertIn("min_adults", r)
            self.assertIn("suggestions", r)
            self.assertIn("priority", r)
            self.assertTrue(len(r["suggestions"]) > 0)
            for s in r["suggestions"]:
                self.assertIn("en", s)
                self.assertIn("vi", s)
                self.assertIn("ar", s)

    def test_calculate_min_rooms(self):
        """Verify minimum required rooms calculation."""
        self.assertEqual(calculate_min_rooms(1, 0, "1"), 1)
        self.assertEqual(calculate_min_rooms(2, 0, "1"), 1)
        self.assertEqual(calculate_min_rooms(3, 0, "2"), 2)
        self.assertEqual(calculate_min_rooms(4, 0, "ceil(adults / 2)"), 2)
        self.assertEqual(calculate_min_rooms(5, 0, "ceil(adults / 2)"), 3)
        self.assertEqual(calculate_min_rooms(2, 2, "ceil(adults / 2) + ceil(children / 2)"), 2)
        self.assertEqual(calculate_min_rooms(4, 2, "ceil(adults / 2) + ceil(children / 2)"), 3)

    def test_format_suggestion_template(self):
        """Verify variable interpolation in template strings."""
        template = "{rooms} Double Rooms for {adults} Adults and {children} Children"
        res = format_suggestion_template(template, adults=4, children=2, rooms=3)
        self.assertEqual(res, "3 Double Rooms for 4 Adults and 2 Children")

    async def test_evaluate_solo_traveler(self):
        """Verify 1 adult -> Solo traveler rule."""
        rules = [
            RoomingHeuristicRule(
                id=r["id"],
                name=r["name"],
                description=r["description"],
                min_adults=r["min_adults"],
                max_adults=r["max_adults"],
                min_children=r["min_children"],
                max_children=r["max_children"],
                min_infants=r["min_infants"],
                max_infants=r["max_infants"],
                kid_age_condition=r["kid_age_condition"],
                suggestions=r["suggestions"],
                min_rooms_formula=r["min_rooms_formula"],
                priority=r["priority"],
                is_active=r["is_active"],
            )
            for r in DEFAULT_ROOMING_RULES
        ]

        async def mock_get_rules():
            return rules

        service = RoomingHeuristicService(DummySession(rules))
        service.get_active_rules = mock_get_rules  # type: ignore

        eval_res = await service.evaluate(adults=1, children=0, lang="en")
        self.assertEqual(eval_res["matched_rule_id"], "rule_solo_traveler")
        self.assertEqual(eval_res["min_estimated_rooms"], 1)
        self.assertIn("1 Single Room", eval_res["suggestions"])

    async def test_evaluate_family_young_kids_vs_teens(self):
        """Verify young kids (<12) match young kids rule and teens (>=12) match teen rule."""
        rules = [
            RoomingHeuristicRule(
                id=r["id"],
                name=r["name"],
                description=r["description"],
                min_adults=r["min_adults"],
                max_adults=r["max_adults"],
                min_children=r["min_children"],
                max_children=r["max_children"],
                min_infants=r["min_infants"],
                max_infants=r["max_infants"],
                kid_age_condition=r["kid_age_condition"],
                suggestions=r["suggestions"],
                min_rooms_formula=r["min_rooms_formula"],
                priority=r["priority"],
                is_active=r["is_active"],
            )
            for r in DEFAULT_ROOMING_RULES
        ]

        async def mock_get_rules():
            return rules

        service = RoomingHeuristicService(DummySession(rules))
        service.get_active_rules = mock_get_rules  # type: ignore

        # 2 adults + 2 young kids (ages 6 and 8)
        young_res = await service.evaluate(adults=2, children=2, kid_ages=[6, 8], lang="en")
        self.assertEqual(young_res["matched_rule_id"], "rule_family_young_kids")
        self.assertIn("1 Double Room + Extra Bed", young_res["suggestions"])

        # 2 adults + 1 teen kid (age 14)
        teen_res = await service.evaluate(adults=2, children=1, kid_ages=[14], lang="en")
        self.assertEqual(teen_res["matched_rule_id"], "rule_family_teen_kids")
        self.assertIn("2 Interconnecting Rooms", teen_res["suggestions"])

    async def test_evaluate_multilingual_suggestions(self):
        """Verify Vietnamese and Arabic localizations."""
        rules = [
            RoomingHeuristicRule(
                id=r["id"],
                name=r["name"],
                description=r["description"],
                min_adults=r["min_adults"],
                max_adults=r["max_adults"],
                min_children=r["min_children"],
                max_children=r["max_children"],
                min_infants=r["min_infants"],
                max_infants=r["max_infants"],
                kid_age_condition=r["kid_age_condition"],
                suggestions=r["suggestions"],
                min_rooms_formula=r["min_rooms_formula"],
                priority=r["priority"],
                is_active=r["is_active"],
            )
            for r in DEFAULT_ROOMING_RULES
        ]

        async def mock_get_rules():
            return rules

        service = RoomingHeuristicService(DummySession(rules))
        service.get_active_rules = mock_get_rules  # type: ignore

        # Vietnamese
        vi_res = await service.evaluate(adults=2, children=0, lang="vi")
        self.assertEqual(vi_res["matched_rule_id"], "rule_couple_no_kids")
        self.assertIn("1 Phòng Double (Giường King)", vi_res["suggestions"])

        # Arabic
        ar_res = await service.evaluate(adults=2, children=0, lang="ar")
        self.assertEqual(ar_res["matched_rule_id"], "rule_couple_no_kids")
        self.assertIn("غرفة مزدوجة (سرير كينج)", ar_res["suggestions"])


if __name__ == "__main__":
    unittest.main()
