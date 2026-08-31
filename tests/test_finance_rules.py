from __future__ import annotations

import ast
import pathlib

from core.rules.finance_rules import (
    AllocationInput,
    decompose_variance,
    derive_invoice_status,
    expected_cost_minor_for_booking_line,
    is_within_tolerance,
    suggest_penalty_expected,
    to_sheet_minor,
    validate_invoice_transition,
    validate_payment_allocations,
)


# --------------------------------------------------------------------- purity


def test_module_has_no_io_or_clock_imports():
    """tz-purity + io-purity grep (§7) — no zoneinfo/date.today/session imports."""
    source = pathlib.Path("core/rules/finance_rules.py").read_text()
    tree = ast.parse(source)
    banned_modules = {"zoneinfo", "sqlalchemy", "datetime"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in banned_modules, alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in banned_modules, node.module
    assert "date.today(" not in source
    assert ".session" not in source


# ------------------------------------------------------------------- to_sheet_minor / identity ppm


def test_to_sheet_minor_identity_when_ppm_none():
    assert to_sheet_minor(1_000, None) == 1_000


def test_to_sheet_minor_converts_and_rounds_half_up():
    assert to_sheet_minor(100, 333_333) == 33
    assert to_sheet_minor(100, 335_000) == 34


# ------------------------------------------------------------- expected cost (booking line, pre-FX)


def test_expected_cost_minor_for_booking_line_multiplies_raw_qty():
    assert expected_cost_minor_for_booking_line(unit_cost_minor_snapshot=500_000, qty_unit=2, qty_time=3) == 3_000_000


# --------------------------------------------------------------- variance decomposition (F1, §1.2)


def test_decompose_variance_null_ppm_uses_identity():
    result = decompose_variance(expected_cost_minor=1_000, actual_amount_minor=1_200, snapshot_fx_rate_ppm=None)
    assert result.expected_sheet_minor == 1_000
    assert result.actual_sheet_minor == 1_200
    assert result.price_variance_sheet_minor == 200


def test_decompose_variance_applies_fx_snapshot():
    # 1000 cost-currency minor * 500_000 ppm (0.5x) = 500 sheet minor
    result = decompose_variance(expected_cost_minor=1_000, actual_amount_minor=1_100, snapshot_fx_rate_ppm=500_000)
    assert result.expected_sheet_minor == 500
    assert result.actual_sheet_minor == 550
    assert result.price_variance_sheet_minor == 50


def test_decompose_variance_no_expected_cost_yields_zero_expected():
    result = decompose_variance(expected_cost_minor=None, actual_amount_minor=900, snapshot_fx_rate_ppm=None)
    assert result.expected_sheet_minor == 0
    assert result.actual_sheet_minor == 900
    assert result.price_variance_sheet_minor == 900


def test_decompose_variance_fx_leg_only_when_allocation_given():
    result = decompose_variance(expected_cost_minor=1_000, actual_amount_minor=1_000, snapshot_fx_rate_ppm=None)
    assert result.paid_sheet_minor is None
    assert result.fx_variance_sheet_minor is None

    result_with_payment = decompose_variance(
        expected_cost_minor=1_000,
        actual_amount_minor=1_000,
        snapshot_fx_rate_ppm=None,
        allocation_amount_minor=1_000,
        payment_fx_rate_ppm=1_050_000,
    )
    assert result_with_payment.paid_sheet_minor == 1_050
    assert result_with_payment.fx_variance_sheet_minor == 50


# ---------------------------------------------------------------------- tolerance


def test_tolerance_zero_requires_exact_match():
    assert is_within_tolerance(0, 1_000, tolerance_bps=0) is True
    assert is_within_tolerance(1, 1_000, tolerance_bps=0) is False
    assert is_within_tolerance(-1, 1_000, tolerance_bps=0) is False


def test_tolerance_positive_bps_allows_a_band():
    # 100 bps of 10_000 = 100
    assert is_within_tolerance(100, 10_000, tolerance_bps=100) is True
    assert is_within_tolerance(101, 10_000, tolerance_bps=100) is False
    assert is_within_tolerance(-100, 10_000, tolerance_bps=100) is True


def test_tolerance_zero_expected_requires_zero_variance():
    assert is_within_tolerance(0, 0, tolerance_bps=500) is True
    assert is_within_tolerance(1, 0, tolerance_bps=500) is False


# ------------------------------------------------------------------- penalty guard (F2, §1.3)


def test_penalty_guard_suggests_when_currencies_match():
    expected, issue = suggest_penalty_expected(cancel_penalty_minor=50_000, sheet_currency="USD", invoice_currency="USD")
    assert expected == 50_000
    assert issue is None


def test_penalty_guard_blocks_when_currencies_differ():
    expected, issue = suggest_penalty_expected(cancel_penalty_minor=50_000, sheet_currency="USD", invoice_currency="VND")
    assert expected is None
    assert issue == "PENALTY_CURRENCY_UNCOMPARABLE"


def test_penalty_guard_no_penalty_amount_is_a_noop():
    expected, issue = suggest_penalty_expected(cancel_penalty_minor=None, sheet_currency="USD", invoice_currency="USD")
    assert expected is None
    assert issue is None


# --------------------------------------------------------------------- state machine


def test_invoice_transition_matrix():
    allowed = {
        "draft": {"received", "void"},
        "received": {"matched", "disputed", "void"},
        "matched": {"received", "disputed", "approved"},
        "disputed": {"received", "matched"},
        "approved": {"paid"},
        "paid": set(),
        "void": set(),
    }
    all_statuses = ("draft", "received", "matched", "disputed", "approved", "paid", "void")
    for current in all_statuses:
        for target in all_statuses:
            result = validate_invoice_transition(current, target)
            expected_passed = target in allowed[current]
            assert result.passed is expected_passed, f"{current} -> {target}"


def test_derive_invoice_status_all_matched_or_waived_is_matched():
    assert derive_invoice_status(current_status="received", line_match_statuses=["auto_matched", "waived"]) == "matched"


def test_derive_invoice_status_any_disputed_wins():
    assert derive_invoice_status(current_status="matched", line_match_statuses=["auto_matched", "disputed"]) == "disputed"


def test_derive_invoice_status_partial_stays_received():
    assert derive_invoice_status(current_status="received", line_match_statuses=["auto_matched", "unmatched"]) == "received"


def test_derive_invoice_status_no_lines_stays_received():
    assert derive_invoice_status(current_status="received", line_match_statuses=[]) == "received"


def test_derive_invoice_status_resolved_dispute_falls_back():
    assert derive_invoice_status(current_status="disputed", line_match_statuses=["auto_matched", "waived"]) == "matched"
    assert derive_invoice_status(current_status="disputed", line_match_statuses=["auto_matched", "unmatched"]) == "received"


def test_derive_invoice_status_noop_once_approved():
    assert derive_invoice_status(current_status="approved", line_match_statuses=["disputed"]) == "approved"


# --------------------------------------------------------------------- allocation sums


def test_validate_payment_allocations_passes_within_budget():
    result = validate_payment_allocations(
        payment_amount_minor=1_000,
        allocations=[AllocationInput(invoice_id="inv_1", amount_minor=600), AllocationInput(invoice_id="inv_2", amount_minor=400)],
        invoice_balance_minor={"inv_1": 600, "inv_2": 500},
    )
    assert result.passed is True


def test_validate_payment_allocations_flags_sum_over_payment():
    result = validate_payment_allocations(
        payment_amount_minor=900,
        allocations=[AllocationInput(invoice_id="inv_1", amount_minor=600), AllocationInput(invoice_id="inv_2", amount_minor=400)],
        invoice_balance_minor={"inv_1": 600, "inv_2": 500},
    )
    assert result.passed is False
    assert any(issue.code == "sum_exceeds_payment" for issue in result.issues)


def test_validate_payment_allocations_flags_exceeding_invoice_balance():
    result = validate_payment_allocations(
        payment_amount_minor=1_000,
        allocations=[AllocationInput(invoice_id="inv_1", amount_minor=800)],
        invoice_balance_minor={"inv_1": 500},
    )
    assert result.passed is False
    assert any(issue.code == "exceeds_invoice_balance" for issue in result.issues)


def test_validate_payment_allocations_sums_repeated_invoice_id():
    result = validate_payment_allocations(
        payment_amount_minor=1_000,
        allocations=[AllocationInput(invoice_id="inv_1", amount_minor=300), AllocationInput(invoice_id="inv_1", amount_minor=300)],
        invoice_balance_minor={"inv_1": 500},
    )
    assert result.passed is False
    assert any(issue.code == "exceeds_invoice_balance" for issue in result.issues)
