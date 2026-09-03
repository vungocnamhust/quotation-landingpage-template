import ast
import inspect
import unittest
from datetime import date

from core.rules import rate_selection
from core.rules.rate_selection import (
    BlackoutWindow,
    RateCandidate,
    RatePriceLineCandidate,
    pick_price_line,
    select_rates,
)


def _rate(rate_id, valid_from, valid_to, *, status="active", min_pax=None, max_pax=None, blackouts=()):
    return RateCandidate(
        rate_id=rate_id,
        lifecycle_status=status,
        valid_from=valid_from,
        valid_to=valid_to,
        min_pax=min_pax,
        max_pax=max_pax,
        blackouts=blackouts,
    )


class TzPurityTests(unittest.TestCase):
    """G1 (15.2b): rate_selection must never ask 'what day is it'."""

    def test_module_does_not_import_zoneinfo_or_now_or_today(self):
        source = inspect.getsource(rate_selection)
        tree = ast.parse(source)
        forbidden_names = {"zoneinfo"}
        forbidden_calls = {"now", "today"}

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = getattr(node, "module", None) or ""
                names = [alias.name for alias in node.names]
                self.assertFalse(
                    "zoneinfo" in module or any(name in forbidden_names for name in names),
                    "rate_selection must not import zoneinfo",
                )
            if isinstance(node, ast.Attribute) and node.attr in forbidden_calls:
                self.fail(f"rate_selection must not call .{node.attr}()")


class SelectRatesTests(unittest.TestCase):
    def test_date_within_validity_matches(self):
        rate = _rate("rat_1", date(2026, 1, 1), date(2026, 3, 31))
        result = select_rates([rate], date(2026, 2, 1), pax=2)
        self.assertEqual([c.rate_id for c in result.candidates], ["rat_1"])
        self.assertFalse(result.has_conflict)

    def test_date_outside_validity_excluded(self):
        rate = _rate("rat_1", date(2026, 1, 1), date(2026, 3, 31))
        result = select_rates([rate], date(2026, 4, 1), pax=2)
        self.assertEqual(result.candidates, ())

    def test_blackout_date_excluded(self):
        rate = _rate(
            "rat_1",
            date(2026, 1, 1),
            date(2026, 3, 31),
            blackouts=(BlackoutWindow(date(2026, 2, 8), date(2026, 2, 10), "Tet"),),
        )
        result = select_rates([rate], date(2026, 2, 9), pax=2)
        self.assertEqual(result.candidates, ())

    def test_pax_outside_min_max_excluded(self):
        rate = _rate("rat_1", date(2026, 1, 1), date(2026, 3, 31), min_pax=2, max_pax=4)
        self.assertEqual(select_rates([rate], date(2026, 2, 1), pax=1).candidates, ())
        self.assertEqual(select_rates([rate], date(2026, 2, 1), pax=5).candidates, ())
        self.assertEqual(len(select_rates([rate], date(2026, 2, 1), pax=2).candidates), 1)

    def test_draft_rate_is_never_selected(self):
        rate = _rate("rat_1", date(2026, 1, 1), date(2026, 3, 31), status="draft")
        result = select_rates([rate], date(2026, 2, 1), pax=2)
        self.assertEqual(result.candidates, ())

    def test_two_overlapping_active_rates_returns_both_with_conflict_flag(self):
        rate_a = _rate("rat_1", date(2026, 1, 1), date(2026, 3, 31))
        rate_b = _rate("rat_2", date(2026, 2, 1), date(2026, 4, 30))
        result = select_rates([rate_a, rate_b], date(2026, 2, 15), pax=2)
        self.assertEqual({c.rate_id for c in result.candidates}, {"rat_1", "rat_2"})
        self.assertTrue(result.has_conflict)
        # never auto-picks a winner
        self.assertEqual(len(result.candidates), 2)


class PickPriceLineTests(unittest.TestCase):
    def test_resolves_tier_at_inclusive_boundary(self):
        lines = [
            RatePriceLineCandidate("adult", "na", "person", 100_000, tier_min_pax=1, tier_max_pax=2),
            RatePriceLineCandidate("adult", "na", "person", 80_000, tier_min_pax=3, tier_max_pax=6),
        ]
        self.assertEqual(pick_price_line(lines, "adult", "na", 2).candidates[0].amount_minor, 100_000)
        self.assertEqual(pick_price_line(lines, "adult", "na", 3).candidates[0].amount_minor, 80_000)

    def test_no_match_returns_none(self):
        lines = [RatePriceLineCandidate("adult", "na", "person", 100_000)]
        self.assertEqual(pick_price_line(lines, "child", "na", 2).candidates, ())

    def test_respects_unit_and_flags_overlapping_tiers(self):
        lines = [
            RatePriceLineCandidate("adult", "na", "person", 100_000, tier_min_pax=1, tier_max_pax=5),
            RatePriceLineCandidate("adult", "na", "room", 200_000, tier_min_pax=1, tier_max_pax=5),
            RatePriceLineCandidate("adult", "na", "person", 90_000, tier_min_pax=3, tier_max_pax=8),
        ]
        person = pick_price_line(lines, "adult", "na", 4, unit="person")
        self.assertTrue(person.has_conflict)
        self.assertEqual(len(person.candidates), 2)
        room = pick_price_line(lines, "adult", "na", 4, unit="room")
        self.assertFalse(room.has_conflict)
        self.assertEqual(room.candidates[0].amount_minor, 200_000)


if __name__ == "__main__":
    unittest.main()
