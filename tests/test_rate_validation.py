import unittest
from datetime import date

from core.rules.rate_validation import (
    BlackoutInput,
    OverlapCandidate,
    PriceLineInput,
    RateValidationContext,
    SupplementInput,
    validate_rate_for_activation,
)


def _context(**overrides):
    defaults = dict(
        valid_from=date(2026, 1, 1),
        valid_to=date(2026, 3, 31),
        rate_basis="net",
        commission_pct=None,
        lines=(PriceLineInput(amount_minor=100_000),),
    )
    defaults.update(overrides)
    return RateValidationContext(**defaults)


class NoPriceLinesTests(unittest.TestCase):
    def test_no_lines_is_a_blocking_error(self):
        result = validate_rate_for_activation(_context(lines=()))
        self.assertFalse(result.passed)
        self.assertIn("NO_PRICE_LINES", [i.code for i in result.errors])


class ZeroAmountTests(unittest.TestCase):
    def test_zero_amount_line_is_a_blocking_error(self):
        result = validate_rate_for_activation(_context(lines=(PriceLineInput(amount_minor=0),)))
        self.assertFalse(result.passed)
        self.assertIn("ZERO_AMOUNT", [i.code for i in result.errors])

    def test_positive_amount_passes(self):
        result = validate_rate_for_activation(_context())
        self.assertTrue(result.passed)


class CommissionTests(unittest.TestCase):
    def test_gross_commissionable_without_commission_pct_blocks(self):
        result = validate_rate_for_activation(_context(rate_basis="gross_commissionable", commission_pct=None))
        self.assertFalse(result.passed)
        self.assertIn("MISSING_COMMISSION_PCT", [i.code for i in result.errors])

    def test_gross_commissionable_with_commission_pct_passes(self):
        result = validate_rate_for_activation(_context(rate_basis="gross_commissionable", commission_pct=1000))
        self.assertTrue(result.passed)

    def test_net_basis_does_not_require_commission_pct(self):
        result = validate_rate_for_activation(_context(rate_basis="net", commission_pct=None))
        self.assertTrue(result.passed)


class BlackoutTests(unittest.TestCase):
    def test_blackout_outside_validity_blocks(self):
        result = validate_rate_for_activation(
            _context(blackouts=(BlackoutInput(date(2026, 4, 1), date(2026, 4, 5)),))
        )
        self.assertFalse(result.passed)
        self.assertIn("BLACKOUT_OUTSIDE_VALIDITY", [i.code for i in result.errors])

    def test_blackout_within_validity_passes(self):
        result = validate_rate_for_activation(
            _context(blackouts=(BlackoutInput(date(2026, 2, 8), date(2026, 2, 10)),))
        )
        self.assertTrue(result.passed)


class SupplementShapeTests(unittest.TestCase):
    def test_supplement_outside_validity_blocks(self):
        result = validate_rate_for_activation(
            _context(supplements=(SupplementInput(date(2025, 12, 1), date(2025, 12, 31)),))
        )
        self.assertFalse(result.passed)
        self.assertIn("POLICY_SHAPE_INVALID", [i.code for i in result.errors])

    def test_supplement_within_validity_passes(self):
        result = validate_rate_for_activation(
            _context(supplements=(SupplementInput(date(2026, 2, 8), date(2026, 2, 10)),))
        )
        self.assertTrue(result.passed)


class OverlapIsWarningNotErrorTests(unittest.TestCase):
    def test_overlap_flags_as_warning_and_still_passes(self):
        result = validate_rate_for_activation(
            _context(other_active_rates=(OverlapCandidate("rat_other", date(2026, 2, 1), date(2026, 4, 30)),))
        )
        self.assertTrue(result.passed)
        self.assertIn("OVERLAP_ACTIVE_RATE", [i.code for i in result.warnings])
        self.assertEqual(result.errors, [])

    def test_non_overlapping_sibling_produces_no_flag(self):
        result = validate_rate_for_activation(
            _context(other_active_rates=(OverlapCandidate("rat_other", date(2026, 4, 1), date(2026, 6, 30)),))
        )
        self.assertTrue(result.passed)
        self.assertEqual(result.warnings, [])


class PriceLineTierOverlapTests(unittest.TestCase):
    def test_overlapping_tiers_warn_without_blocking_activation(self):
        result = validate_rate_for_activation(
            _context(
                lines=(
                    PriceLineInput(100_000, price_for="adult", occupancy_basis="na", unit="person", tier_min_pax=1, tier_max_pax=5),
                    PriceLineInput(90_000, price_for="adult", occupancy_basis="na", unit="person", tier_min_pax=3, tier_max_pax=8),
                )
            )
        )
        self.assertTrue(result.passed)
        self.assertIn("PRICE_LINE_TIER_OVERLAP", [issue.code for issue in result.warnings])


if __name__ == "__main__":
    unittest.main()
