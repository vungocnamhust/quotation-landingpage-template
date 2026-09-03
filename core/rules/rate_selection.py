"""Pure rate selection for a (product, date, pax) triple — 15.3 §1.7.

No I/O, no session, no timezone awareness. The caller (15.4 service layer) is
responsible for loading candidate rates via the repository and for resolving
``service_date`` to a local date using the destination's timezone (G1, 15.2b)
*before* calling into this module. This module never asks "what day is it" —
it only compares dates it was handed.

T6: when more than one active rate covers the same (date, pax), this module
never picks a winner. It returns every candidate plus a conflict flag; a
human (15.4 UI) or an AI agent (15.7) makes the call.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class BlackoutWindow:
    from_date: date
    to_date: date
    reason: str = ""


@dataclass(frozen=True)
class RatePriceLineCandidate:
    price_for: str
    occupancy_basis: str
    unit: str
    amount_minor: int
    tier_min_pax: int | None = None
    tier_max_pax: int | None = None


@dataclass(frozen=True)
class RateCandidate:
    rate_id: str
    lifecycle_status: str
    valid_from: date
    valid_to: date
    min_pax: int | None = None
    max_pax: int | None = None
    blackouts: tuple[BlackoutWindow, ...] = field(default_factory=tuple)
    lines: tuple[RatePriceLineCandidate, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SelectionResult:
    candidates: tuple[RateCandidate, ...]
    has_conflict: bool


@dataclass(frozen=True)
class PriceLineSelection:
    """All price lines matching one commercial selection.

    Just like rate selection, this deliberately never picks a winner when more
    than one tier covers the same party.  Callers must surface that conflict to
    a staff user (or flag it for AI review).
    """

    candidates: tuple[RatePriceLineCandidate, ...]
    has_conflict: bool


def _covers_date(rate: RateCandidate, service_date: date) -> bool:
    if not (rate.valid_from <= service_date <= rate.valid_to):
        return False
    for blackout in rate.blackouts:
        if blackout.from_date <= service_date <= blackout.to_date:
            return False
    return True


def _covers_pax(rate: RateCandidate, pax: int) -> bool:
    if rate.min_pax is not None and pax < rate.min_pax:
        return False
    if rate.max_pax is not None and pax > rate.max_pax:
        return False
    return True


def is_rate_available_on_date(rate: RateCandidate, service_date: date) -> bool:
    """Lifecycle/date/blackout predicate for rate list surfaces without pax context."""
    return rate.lifecycle_status == "active" and covers_service_date(rate, service_date)


def covers_service_date(rate: RateCandidate, service_date: date) -> bool:
    """Date/blackout predicate that intentionally does not make a lifecycle decision."""
    return _covers_date(rate, service_date)


def select_rates(rates: list[RateCandidate], service_date: date, pax: int) -> SelectionResult:
    """Filter to active rates covering ``service_date`` (outside blackout) and ``pax``.

    ``service_date`` MUST already be a local date resolved by the caller (K3) —
    this function performs date-vs-date comparisons only.
    """
    matches = tuple(
        rate
        for rate in rates
        if is_rate_available_on_date(rate, service_date) and _covers_pax(rate, pax)
    )
    return SelectionResult(candidates=matches, has_conflict=len(matches) > 1)


def pick_price_line(
    lines: list[RatePriceLineCandidate],
    price_for: str,
    occupancy_basis: str,
    pax_count: int,
    unit: str | None = None,
) -> PriceLineSelection:
    """Return every matching price line for the given party and optional unit.

    Tier bounds are inclusive. A line with no tier bounds matches any pax_count.
    """
    matches = tuple(
        line
        for line in lines
        if line.price_for == price_for
        and line.occupancy_basis == occupancy_basis
        and (unit is None or line.unit == unit)
        and (line.tier_min_pax is None or pax_count >= line.tier_min_pax)
        and (line.tier_max_pax is None or pax_count <= line.tier_max_pax)
    )
    return PriceLineSelection(candidates=matches, has_conflict=len(matches) > 1)
