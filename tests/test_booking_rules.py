import ast
import inspect
import unittest
from datetime import date

from core.rules import booking_rules
from core.rules.booking_rules import (
    CashFlowLine,
    cancellation_penalty_minor,
    cash_flow_check,
    compute_deadlines,
    default_request_by,
    validate_transition,
)

GRADUATED_POLICY = {
    "tiers": [
        {"days_before_service_min": 30, "penalty_percent": 0},
        {"days_before_service_min": 14, "penalty_percent": 25},
        {"days_before_service_min": 7, "penalty_percent": 50},
        {"days_before_service_min": 0, "penalty_percent": 100},
    ],
    "no_show_penalty_percent": 100,
}

FLAT_NON_REFUNDABLE_POLICY = {
    "tiers": [{"days_before_service_min": 0, "penalty_percent": 100}],
    "no_show_penalty_percent": 100,
}


class TzPurityTests(unittest.TestCase):
    """G1 (15.2b), reused for 15.6: booking_rules must never ask 'what day is it'."""

    def test_module_does_not_import_zoneinfo_or_now_or_today(self):
        source = inspect.getsource(booking_rules)
        tree = ast.parse(source)
        forbidden_names = {"zoneinfo"}
        forbidden_calls = {"now", "today"}

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = getattr(node, "module", None) or ""
                names = [alias.name for alias in node.names]
                self.assertFalse(
                    "zoneinfo" in module or any(name in forbidden_names for name in names),
                    "booking_rules must not import zoneinfo",
                )
            if isinstance(node, ast.Attribute) and node.attr in forbidden_calls:
                self.fail(f"booking_rules must not call .{node.attr}()")


class ComputeDeadlinesTests(unittest.TestCase):
    def test_graduated_policy_free_until_is_one_day_before_the_smallest_positive_tier(self):
        deadlines = compute_deadlines(
            cancellation_policy=GRADUATED_POLICY,
            payment_terms={"balance_due_days_before_service": 21, "deposit_due_days_after_confirm": 3},
            service_date=date(2026, 6, 30),
        )
        # smallest positive-penalty tier is 14 days -> free until service_date - 15
        self.assertEqual(deadlines.penalty_free_until, date(2026, 6, 15))
        self.assertEqual(deadlines.balance_due_date, date(2026, 6, 9))
        self.assertIsNone(deadlines.deposit_due_date)

    def test_flat_non_refundable_policy_has_no_free_window(self):
        deadlines = compute_deadlines(
            cancellation_policy=FLAT_NON_REFUNDABLE_POLICY, payment_terms=None, service_date=date(2026, 6, 30)
        )
        self.assertIsNone(deadlines.penalty_free_until)

    def test_empty_policy_has_no_free_window(self):
        deadlines = compute_deadlines(cancellation_policy=None, payment_terms=None, service_date=date(2026, 6, 30))
        self.assertIsNone(deadlines.penalty_free_until)
        self.assertIsNone(deadlines.balance_due_date)

    def test_deposit_due_date_only_computed_once_confirmed(self):
        deadlines = compute_deadlines(
            cancellation_policy=None,
            payment_terms={"deposit_due_days_after_confirm": 3},
            service_date=date(2026, 6, 30),
            confirmed_at=date(2026, 5, 1),
        )
        self.assertEqual(deadlines.deposit_due_date, date(2026, 5, 4))


class DefaultRequestByTests(unittest.TestCase):
    def test_uses_buffer_before_penalty_free_until_when_present(self):
        result = default_request_by(date(2026, 6, 15), date(2026, 6, 30))
        self.assertEqual(result, date(2026, 6, 8))

    def test_falls_back_to_lead_days_before_service_when_no_free_window(self):
        result = default_request_by(None, date(2026, 6, 30))
        self.assertEqual(result, date(2026, 6, 16))


class CancellationPenaltyMinorTests(unittest.TestCase):
    SELL = 10_000_000

    def test_far_out_cancellation_is_free(self):
        penalty = cancellation_penalty_minor(GRADUATED_POLICY, self.SELL, date(2026, 6, 30), date(2026, 5, 1))
        self.assertEqual(penalty, 0)

    def test_bracket_between_8_and_14_days_charges_25_percent(self):
        # service_date - on_date = 10 days remaining -> qualifies for the 14-day tier only.
        penalty = cancellation_penalty_minor(GRADUATED_POLICY, self.SELL, date(2026, 6, 30), date(2026, 6, 20))
        self.assertEqual(penalty, 2_500_000)

    def test_bracket_between_1_and_7_days_charges_50_percent(self):
        # 5 days remaining -> qualifies for the 7-day tier only.
        penalty = cancellation_penalty_minor(GRADUATED_POLICY, self.SELL, date(2026, 6, 30), date(2026, 6, 25))
        self.assertEqual(penalty, 5_000_000)

    def test_zero_days_left_charges_100_percent(self):
        penalty = cancellation_penalty_minor(GRADUATED_POLICY, self.SELL, date(2026, 6, 30), date(2026, 6, 30))
        self.assertEqual(penalty, 10_000_000)

    def test_no_show_after_service_date_uses_no_show_percent(self):
        penalty = cancellation_penalty_minor(GRADUATED_POLICY, self.SELL, date(2026, 6, 30), date(2026, 7, 2))
        self.assertEqual(penalty, 10_000_000)

    def test_cancellation_on_service_date_uses_no_show_percent(self):
        policy = {**GRADUATED_POLICY, "no_show_penalty_percent": 75}
        penalty = cancellation_penalty_minor(policy, self.SELL, date(2026, 6, 30), date(2026, 6, 30))
        self.assertEqual(penalty, 7_500_000)

    def test_empty_tiers_on_service_date_uses_default_no_show_penalty(self):
        penalty = cancellation_penalty_minor({"tiers": []}, self.SELL, date(2026, 6, 30), date(2026, 6, 30))
        self.assertEqual(penalty, self.SELL)


class ValidateTransitionTests(unittest.TestCase):
    ALL_STATUSES = ("to_request", "requested", "confirmed", "delivered", "cancelled")

    def test_full_transition_matrix(self):
        allowed = {
            ("to_request", "requested"),
            ("to_request", "cancelled"),
            ("requested", "confirmed"),
            ("requested", "cancelled"),
            ("confirmed", "delivered"),
            ("confirmed", "cancelled"),
        }
        for current in self.ALL_STATUSES:
            for target in self.ALL_STATUSES:
                gate = validate_transition(
                    current, target, confirmed_at=date(2026, 1, 1) if target == "confirmed" else None,
                    cancel_reason="customer changed mind" if target == "cancelled" else None,
                )
                if (current, target) in allowed:
                    self.assertTrue(gate.passed, f"{current} -> {target} should be allowed")
                else:
                    self.assertFalse(gate.passed, f"{current} -> {target} should be rejected")

    def test_confirm_without_confirmed_at_fails(self):
        gate = validate_transition("requested", "confirmed", confirmed_at=None)
        self.assertFalse(gate.passed)
        self.assertTrue(any(issue.field == "confirmed_at" for issue in gate.errors))

    def test_cancel_without_reason_fails(self):
        gate = validate_transition("requested", "cancelled", cancel_reason=None)
        self.assertFalse(gate.passed)
        self.assertTrue(any(issue.field == "cancel_reason" for issue in gate.errors))


class CashFlowCheckTests(unittest.TestCase):
    def test_flags_lines_where_supplier_is_owed_before_customer_pays(self):
        lines = [
            CashFlowLine(line_id="a", balance_due_date=date(2026, 6, 1)),
            CashFlowLine(line_id="b", balance_due_date=date(2026, 6, 20)),
            CashFlowLine(line_id="c", balance_due_date=None),
        ]
        flagged = cash_flow_check(date(2026, 6, 10), lines)
        self.assertEqual(flagged, ["a"])

    def test_no_customer_due_date_means_no_warnings(self):
        lines = [CashFlowLine(line_id="a", balance_due_date=date(2026, 6, 1))]
        self.assertEqual(cash_flow_check(None, lines), [])


if __name__ == "__main__":
    unittest.main()
