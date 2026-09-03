"""Pure booking math — 15.6 §1.5. No I/O, no session, no clock (tz-purity, K3).

Deadlines are computed, never typed by an operator: this module turns a
FROZEN cancellation-policy / payment-terms snapshot plus a ``service_date``
into ``penalty_free_until`` / ``balance_due_date`` / ``deposit_due_date``.
Callers pass "today" in explicitly (destination-tz aware, per 15.3 §0.1) —
this module never calls ``date.today()`` or touches ``zoneinfo``.

Cancellation-policy tiers are the shape resolved from Phụ lục A.2
(``schemas/v2/supplier.py::SupplierCancellationPolicySchema``), read here as
plain dicts so this module stays decoupled from Pydantic: ``{"tiers": [...],
"no_show_penalty_percent": int}`` where each tier is ``{"days_before_service_min":
int, "penalty_percent": int}``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from core.rules.base import GateIssue, GateResult, Severity

REQUEST_BUFFER_DAYS = 7
DEFAULT_REQUEST_LEAD_DAYS = 14

BOOKING_LINE_STATUSES = ("to_request", "requested", "confirmed", "delivered", "cancelled")

_VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    "to_request": frozenset({"requested", "cancelled"}),
    "requested": frozenset({"confirmed", "cancelled"}),
    "confirmed": frozenset({"delivered", "cancelled"}),
    "delivered": frozenset(),
    "cancelled": frozenset(),
}


@dataclass(frozen=True)
class BookingDeadlines:
    penalty_free_until: date | None
    balance_due_date: date | None
    deposit_due_date: date | None


@dataclass(frozen=True)
class CashFlowLine:
    line_id: str
    balance_due_date: date | None


def _round_half_up_div(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        raise ValueError("denominator must be > 0")
    half = denominator // 2
    if numerator >= 0:
        return (numerator + half) // denominator
    return -((-numerator + half) // denominator)


def _penalized_tiers(cancellation_policy: dict[str, Any] | None) -> list[dict[str, Any]]:
    tiers = (cancellation_policy or {}).get("tiers") or []
    return [tier for tier in tiers if int(tier.get("penalty_percent", 0)) > 0]


def compute_deadlines(
    *,
    cancellation_policy: dict[str, Any] | None,
    payment_terms: dict[str, Any] | None,
    service_date: date,
    confirmed_at: date | None = None,
) -> BookingDeadlines:
    """Derive the 3 booking-line deadlines from FROZEN terms snapshots.

    ``penalty_free_until`` = ``service_date`` minus (the ``days_before_service_min``
    of the tier with the smallest positive ``penalty_percent`` — by the tier
    monotonicity invariant [Phụ lục A.2], this is also the tier with the
    *largest* ``days_before_service_min`` among penalized tiers) minus 1 day.
    ``None`` when the policy has no penalized tier, or when that tier's
    threshold is 0 days (penalty applies from the moment of booking — no free
    window to report).
    """
    penalized = _penalized_tiers(cancellation_policy)
    if not penalized:
        penalty_free_until = None
    else:
        threshold_days = max(int(tier["days_before_service_min"]) for tier in penalized)
        penalty_free_until = None if threshold_days == 0 else service_date - timedelta(days=threshold_days + 1)

    balance_days = (payment_terms or {}).get("balance_due_days_before_service")
    balance_due_date = service_date - timedelta(days=int(balance_days)) if balance_days is not None else None

    deposit_days = (payment_terms or {}).get("deposit_due_days_after_confirm")
    deposit_due_date = (
        confirmed_at + timedelta(days=int(deposit_days))
        if confirmed_at is not None and deposit_days is not None
        else None
    )

    return BookingDeadlines(
        penalty_free_until=penalty_free_until, balance_due_date=balance_due_date, deposit_due_date=deposit_due_date
    )


def default_request_by(penalty_free_until: date | None, service_date: date) -> date:
    """Default ``request_by_date`` — sửa được sau, đây chỉ là gợi ý ban đầu."""
    if penalty_free_until is not None:
        return penalty_free_until - timedelta(days=REQUEST_BUFFER_DAYS)
    return service_date - timedelta(days=DEFAULT_REQUEST_LEAD_DAYS)


def cancellation_penalty_minor(
    cancellation_policy: dict[str, Any] | None,
    cost_minor: int,
    service_date: date,
    on_date: date,
) -> int:
    """Penalty owed if cancelled on ``on_date`` — tier lookup + no-show fallback.

    The applicable tier is the one with the *smallest* ``days_before_service_min``
    among tiers whose threshold is still ``>= days_remaining`` (the tightest
    bracket not yet exceeded). No qualifying tier (cancelling further out than
    every declared threshold) means free — 0 penalty. Cancelling on/after
    ``service_date`` (``days_remaining <= 0``) uses ``no_show_penalty_percent``.
    """
    tiers = (cancellation_policy or {}).get("tiers") or []
    no_show_percent = int((cancellation_policy or {}).get("no_show_penalty_percent", 100))
    days_remaining = (service_date - on_date).days

    if days_remaining <= 0:
        percent = no_show_percent
    else:
        qualifying = [tier for tier in tiers if days_remaining <= int(tier["days_before_service_min"])]
        percent = (
            min(qualifying, key=lambda tier: int(tier["days_before_service_min"]))["penalty_percent"]
            if qualifying
            else 0
        )

    return _round_half_up_div(cost_minor * int(percent), 100)


def validate_transition(
    current: str,
    target: str,
    *,
    confirmed_at: date | None = None,
    cancel_reason: str | None = None,
) -> GateResult:
    """State machine chốt #5: ``to_request -> requested -> confirmed -> delivered | cancelled``."""
    issues: list[GateIssue] = []
    allowed = _VALID_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        issues.append(
            GateIssue(
                field="status",
                code="invalid_transition",
                message=f"Cannot transition booking line from '{current}' to '{target}'.",
            )
        )
    if target == "confirmed" and confirmed_at is None:
        issues.append(
            GateIssue(field="confirmed_at", code="required", message="confirmed_at is required to confirm a booking line.")
        )
    if target == "cancelled" and not cancel_reason:
        issues.append(
            GateIssue(field="cancel_reason", code="required", message="cancel_reason is required to cancel a booking line.")
        )
    return GateResult(passed=not any(issue.severity == Severity.ERROR for issue in issues), issues=issues)


def cash_flow_check(customer_balance_due_date: date | None, lines: list[CashFlowLine]) -> list[str]:
    """T9 guardrail — line ids where the supplier is owed before the customer pays."""
    if customer_balance_due_date is None:
        return []
    return [
        line.line_id
        for line in lines
        if line.balance_due_date is not None and line.balance_due_date < customer_balance_due_date
    ]
