"""Pure activation-gate for a rate — 15.3 §1.7.

No I/O, no session. The service layer builds a ``RateValidationContext`` from
the rate header + its price lines + sibling active rates on the same product,
then calls ``validate_rate_for_activation``. Overlap with another active rate
is a WARNING, never an error (T6) — pure code never blocks on it, it only flags.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from core.rules.base import GateIssue, GateResult, Severity


@dataclass(frozen=True)
class PriceLineInput:
    amount_minor: int
    price_for: str = "unit"
    occupancy_basis: str = "na"
    unit: str = "unit"
    tier_min_pax: int | None = None
    tier_max_pax: int | None = None


@dataclass(frozen=True)
class BlackoutInput:
    from_date: date
    to_date: date


@dataclass(frozen=True)
class SupplementInput:
    applies_from: date
    applies_to: date


@dataclass(frozen=True)
class OverlapCandidate:
    rate_id: str
    valid_from: date
    valid_to: date


@dataclass(frozen=True)
class RateValidationContext:
    valid_from: date
    valid_to: date
    rate_basis: str
    commission_pct: int | None
    lines: tuple[PriceLineInput, ...]
    blackouts: tuple[BlackoutInput, ...] = field(default_factory=tuple)
    supplements: tuple[SupplementInput, ...] = field(default_factory=tuple)
    other_active_rates: tuple[OverlapCandidate, ...] = field(default_factory=tuple)


def _windows_overlap(a_from: date, a_to: date, b_from: date, b_to: date) -> bool:
    return a_from <= b_to and b_from <= a_to


def validate_rate_for_activation(context: RateValidationContext) -> GateResult:
    issues: list[GateIssue] = []

    if not context.lines:
        issues.append(
            GateIssue(
                field="lines",
                code="NO_PRICE_LINES",
                message="A rate must have at least one price line before it can be activated.",
            )
        )
    else:
        for index, line in enumerate(context.lines):
            if line.amount_minor <= 0:
                issues.append(
                    GateIssue(
                        field=f"lines[{index}].amount_minor",
                        code="ZERO_AMOUNT",
                        message="Price line amount must be greater than 0.",
                    )
                )

    if context.rate_basis == "gross_commissionable" and context.commission_pct is None:
        issues.append(
            GateIssue(
                field="commission_pct",
                code="MISSING_COMMISSION_PCT",
                message="commission_pct is required when rate_basis is 'gross_commissionable'.",
            )
        )

    for index, blackout in enumerate(context.blackouts):
        if not (context.valid_from <= blackout.from_date and blackout.to_date <= context.valid_to):
            issues.append(
                GateIssue(
                    field=f"blackout_json[{index}]",
                    code="BLACKOUT_OUTSIDE_VALIDITY",
                    message="Blackout window must be within [valid_from, valid_to].",
                )
            )
        if blackout.from_date > blackout.to_date:
            issues.append(
                GateIssue(
                    field=f"blackout_json[{index}]",
                    code="BLACKOUT_OUTSIDE_VALIDITY",
                    message="Blackout 'from' must be <= 'to'.",
                )
            )

    for index, supplement in enumerate(context.supplements):
        shape_ok = supplement.applies_from <= supplement.applies_to
        within_validity = context.valid_from <= supplement.applies_from and supplement.applies_to <= context.valid_to
        if not shape_ok or not within_validity:
            issues.append(
                GateIssue(
                    field=f"supplements_json[{index}]",
                    code="POLICY_SHAPE_INVALID",
                    message="Supplement applies_from/applies_to must be ordered and within rate validity.",
                )
            )

    for candidate in context.other_active_rates:
        if _windows_overlap(context.valid_from, context.valid_to, candidate.valid_from, candidate.valid_to):
            issues.append(
                GateIssue(
                    field="valid_from",
                    code="OVERLAP_ACTIVE_RATE",
                    message=f"Validity overlaps with active rate '{candidate.rate_id}'.",
                    severity=Severity.WARNING,
                )
            )

    for index, line in enumerate(context.lines):
        for other in context.lines[index + 1 :]:
            if (line.price_for, line.occupancy_basis, line.unit) != (
                other.price_for,
                other.occupancy_basis,
                other.unit,
            ):
                continue
            line_from, line_to = line.tier_min_pax or 1, line.tier_max_pax or 10**9
            other_from, other_to = other.tier_min_pax or 1, other.tier_max_pax or 10**9
            if _windows_overlap(line_from, line_to, other_from, other_to):
                issues.append(
                    GateIssue(
                        field="lines",
                        code="PRICE_LINE_TIER_OVERLAP",
                        message="Price-line tiers overlap for the same price_for, occupancy_basis and unit.",
                        severity=Severity.WARNING,
                    )
                )
                break

    result = GateResult(passed=True, issues=issues)
    return GateResult(passed=not result.errors, issues=issues)
