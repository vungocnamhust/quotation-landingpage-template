"""Pure AP reconciliation math — 15.9 §1.2/§1.3/§5.4. No I/O, no session, no clock.

Single reference frame: every variance is expressed in the booking's
``sheet_currency`` (chốt #5, F1). ``fx_rate_ppm_snapshot``/``fx_rate_ppm``
``None`` means the two currencies are identical — callers never special-case
``None`` themselves, this module substitutes the identity rate.
"""
from __future__ import annotations

from dataclasses import dataclass

from core.rules.base import GateIssue, GateResult, Severity

_PPM_IDENTITY = 1_000_000
_BPS_DIVISOR = 10_000

LINE_TYPES = ("service", "adjustment", "penalty", "fee")
MATCH_STATUSES = ("unmatched", "auto_matched", "manual_matched", "waived", "disputed")
INVOICE_STATUSES = ("draft", "received", "matched", "disputed", "approved", "paid", "void")
PAYMENT_METHODS = ("bank_transfer", "cash", "card", "other")

MATCH_ISSUES = (
    "CURRENCY_MISMATCH",
    "QTY_MISMATCH",
    "TOLERANCE_EXCEEDED",
    "DUPLICATE_VOUCHER",
    "PENALTY_CURRENCY_UNCOMPARABLE",
    "FX_MULTI_SHEET_CURRENCY",
    "SHEET_CURRENCY_UNRESOLVED",
)

_MATCHED_LIKE = frozenset({"auto_matched", "manual_matched", "waived"})

_VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"received", "void"}),
    "received": frozenset({"matched", "disputed", "void"}),
    "matched": frozenset({"received", "disputed", "approved"}),
    "disputed": frozenset({"received", "matched"}),
    "approved": frozenset({"paid"}),
    "paid": frozenset(),
    "void": frozenset(),
}


def _round_half_up_div(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        raise ValueError("denominator must be > 0")
    half = denominator // 2
    if numerator >= 0:
        return (numerator + half) // denominator
    return -((-numerator + half) // denominator)


def _identity_ppm(ppm: int | None) -> int:
    return ppm if ppm is not None else _PPM_IDENTITY


def to_sheet_minor(amount_minor: int, ppm: int | None) -> int:
    """Convert an amount from its own currency to sheet currency via ``ppm`` (rounded half-up)."""
    return _round_half_up_div(amount_minor * _identity_ppm(ppm), _PPM_IDENTITY)


def scale_actual_sheet_minor(
    *, actual_sheet_minor_total: int, allocation_amount_minor: int, invoice_gross_total_minor: int
) -> int:
    """Proportional share of an invoice's matched-lines actual cost (sheet currency) that one
    payment allocation represents (§12.5 H4).

    Payment allocations in this module are invoice-level, not line-level, so a single
    allocation has no direct claim on any one matched line's actual cost. This scales the
    invoice's aggregate actual-cost-in-sheet-currency by the allocation's share of the
    invoice's ``gross_total_minor`` — the same currency the allocation itself is denominated
    in (chốt: allocation amounts are invoice-currency, matching the balance/Σ checks below).
    """
    if invoice_gross_total_minor == 0:
        return 0
    return _round_half_up_div(actual_sheet_minor_total * allocation_amount_minor, invoice_gross_total_minor)


def expected_cost_minor_for_booking_line(*, unit_cost_minor_snapshot: int, qty_unit: int, qty_time: int) -> int:
    """Raw cost in the booking line's ``cost_currency_snapshot`` — pre-FX (chốt #10 comparand)."""
    return unit_cost_minor_snapshot * qty_unit * qty_time


@dataclass(frozen=True)
class VarianceDecomposition:
    expected_sheet_minor: int
    actual_sheet_minor: int
    price_variance_sheet_minor: int
    paid_sheet_minor: int | None
    fx_variance_sheet_minor: int | None


def decompose_variance(
    *,
    expected_cost_minor: int | None,
    actual_amount_minor: int,
    snapshot_fx_rate_ppm: int | None,
    allocation_amount_minor: int | None = None,
    payment_fx_rate_ppm: int | None = None,
) -> VarianceDecomposition:
    """§1.2 — price variance chốt lúc match, fx variance chốt lúc payment (both optional)."""
    snap_ppm = _identity_ppm(snapshot_fx_rate_ppm)
    actual_sheet = to_sheet_minor(actual_amount_minor, snap_ppm)
    expected_sheet = to_sheet_minor(expected_cost_minor, snap_ppm) if expected_cost_minor is not None else 0
    price_variance = actual_sheet - expected_sheet

    paid_sheet: int | None = None
    fx_variance: int | None = None
    if allocation_amount_minor is not None:
        pay_ppm = _identity_ppm(payment_fx_rate_ppm)
        paid_sheet = to_sheet_minor(allocation_amount_minor, pay_ppm)
        fx_variance = paid_sheet - actual_sheet

    return VarianceDecomposition(
        expected_sheet_minor=expected_sheet,
        actual_sheet_minor=actual_sheet,
        price_variance_sheet_minor=price_variance,
        paid_sheet_minor=paid_sheet,
        fx_variance_sheet_minor=fx_variance,
    )


def is_within_tolerance(variance_sheet_minor: int, expected_sheet_minor: int, tolerance_bps: int) -> bool:
    """tolerance_bps default 0 ⇒ any non-zero variance requires a human decision."""
    if tolerance_bps <= 0:
        return variance_sheet_minor == 0
    if expected_sheet_minor == 0:
        return variance_sheet_minor == 0
    allowed = _round_half_up_div(abs(expected_sheet_minor) * tolerance_bps, _BPS_DIVISOR)
    return abs(variance_sheet_minor) <= allowed


def suggest_penalty_expected(
    *, cancel_penalty_minor: int | None, sheet_currency: str, invoice_currency: str
) -> tuple[int | None, str | None]:
    """§1.3 (F2) — penalty auto-suggest only when sheet and invoice currency match.

    Returns ``(expected_cost_minor, issue_code)`` — issue is
    ``PENALTY_CURRENCY_UNCOMPARABLE`` when currencies differ (no silent FX).
    """
    if cancel_penalty_minor is None:
        return None, None
    if sheet_currency != invoice_currency:
        return None, "PENALTY_CURRENCY_UNCOMPARABLE"
    return cancel_penalty_minor, None


def validate_invoice_transition(current: str, target: str) -> GateResult:
    issues: list[GateIssue] = []
    allowed = _VALID_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        issues.append(
            GateIssue(
                field="status",
                code="invalid_transition",
                message=f"Cannot transition supplier invoice from '{current}' to '{target}'.",
            )
        )
    return GateResult(passed=not any(i.severity == Severity.ERROR for i in issues), issues=issues)


def derive_invoice_status(*, current_status: str, line_match_statuses: list[str]) -> str:
    """F5 — dispute is 2-level derived; 'matched'/'disputed' are never set by direct action.

    Only meaningful while the invoice is in ``received``/``matched``/``disputed``
    (pre-approval). Callers must not call this once the invoice is ``approved``/
    ``paid``/``void`` — those states are terminal-ish and line mutation is blocked
    upstream by the service.
    """
    if current_status not in ("received", "matched", "disputed"):
        return current_status
    if any(status == "disputed" for status in line_match_statuses):
        return "disputed"
    if line_match_statuses and all(status in _MATCHED_LIKE for status in line_match_statuses):
        return "matched"
    return "received"


@dataclass(frozen=True)
class AllocationInput:
    invoice_id: str
    amount_minor: int


def validate_payment_allocations(
    *, payment_amount_minor: int, allocations: list[AllocationInput], invoice_balance_minor: dict[str, int]
) -> GateResult:
    """Positive-payment gate: Σ per payment ≤ payment amount; Σ per invoice ≤ remaining balance;
    every allocation must itself be positive (§12.3 H2 — a payment's sign governs its
    allocations' sign; the negative half of this rule lives in ``validate_reversal_allocations``).
    """
    issues: list[GateIssue] = []
    for alloc in allocations:
        if alloc.amount_minor <= 0:
            issues.append(
                GateIssue(
                    field="allocations",
                    code="invalid_sign",
                    message=f"Allocation to invoice '{alloc.invoice_id}' must be positive for a positive payment (got {alloc.amount_minor}).",
                )
            )
    total = sum(a.amount_minor for a in allocations)
    if total > payment_amount_minor:
        issues.append(
            GateIssue(
                field="allocations",
                code="sum_exceeds_payment",
                message=f"Allocations sum to {total} but payment is only {payment_amount_minor}.",
            )
        )
    per_invoice: dict[str, int] = {}
    for alloc in allocations:
        per_invoice[alloc.invoice_id] = per_invoice.get(alloc.invoice_id, 0) + alloc.amount_minor
    for invoice_id, amount in per_invoice.items():
        remaining = invoice_balance_minor.get(invoice_id, 0)
        if amount > remaining:
            issues.append(
                GateIssue(
                    field="allocations",
                    code="exceeds_invoice_balance",
                    message=f"Allocation of {amount} to invoice '{invoice_id}' exceeds remaining balance {remaining}.",
                )
            )
    return GateResult(passed=not any(i.severity == Severity.ERROR for i in issues), issues=issues)


def validate_reversal_allocations(
    *, payment_amount_minor: int, allocations: list[AllocationInput], invoice_paid_minor: dict[str, int]
) -> GateResult:
    """Negative-payment (reversal) gate (§12.2 H1, §12.3 H2) — a reversal is not exempt from
    validation, it has its own mirrored rules instead of the positive-payment ones:

    1. The payment amount itself must be negative (callers route here only for that case).
    2. Every allocation must itself be negative — same sign as the payment (H2).
    3. Σ allocations must equal the payment amount exactly (a reversal is a precise undo,
       never a partial-sum-under-budget like a forward payment can be).
    4. Each invoice's reversed total may not exceed what was actually paid on it before this
       reversal (``invoice_paid_minor`` — net Σ prior allocations, i.e. ``get_balances_for_invoices``)
       — a reversal can undo a payment, never manufacture a negative balance.
    """
    issues: list[GateIssue] = []
    if payment_amount_minor >= 0:
        issues.append(
            GateIssue(field="amount_minor", code="not_negative", message="Reversal validation requires a negative payment amount.")
        )
        return GateResult(passed=False, issues=issues)

    for alloc in allocations:
        if alloc.amount_minor >= 0:
            issues.append(
                GateIssue(
                    field="allocations",
                    code="invalid_sign",
                    message=f"Reversal allocation to invoice '{alloc.invoice_id}' must be negative (got {alloc.amount_minor}).",
                )
            )

    total = sum(a.amount_minor for a in allocations)
    if total != payment_amount_minor:
        issues.append(
            GateIssue(
                field="allocations",
                code="sum_mismatch",
                message=f"Reversal allocations sum to {total} but the payment is {payment_amount_minor}.",
            )
        )

    per_invoice: dict[str, int] = {}
    for alloc in allocations:
        per_invoice[alloc.invoice_id] = per_invoice.get(alloc.invoice_id, 0) + alloc.amount_minor
    for invoice_id, amount in per_invoice.items():
        already_paid = invoice_paid_minor.get(invoice_id, 0)
        if already_paid <= 0:
            issues.append(
                GateIssue(
                    field="allocations",
                    code="no_prior_payment",
                    message=f"Invoice '{invoice_id}' has no prior payment to reverse.",
                )
            )
        elif already_paid + amount < 0:
            issues.append(
                GateIssue(
                    field="allocations",
                    code="exceeds_paid_amount",
                    message=f"Reversal of {amount} on invoice '{invoice_id}' exceeds the {already_paid} already paid.",
                )
            )

    return GateResult(passed=not any(i.severity == Severity.ERROR for i in issues), issues=issues)
