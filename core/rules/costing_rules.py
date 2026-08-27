"""Pure costing math — 15.4 §1.5. No I/O, no session, integer math only.

``core/rules/costing_rules.py`` is the single engine for line cost/sell math and
sheet-level summaries. The FE reconciler (``lib/rules/costingReconciler.ts``) may
render a preview from the same inputs, but the numbers that get persisted and
displayed after a round-trip always come from this module (chốt #4).
"""
from __future__ import annotations

from dataclasses import dataclass

_PPM_DIVISOR = 1_000_000
_BPS_DIVISOR = 10_000


@dataclass(frozen=True)
class ServiceLineInput:
    line_id: str
    day_number: int | None
    category: str
    unit_cost_minor: int
    qty_unit: int
    qty_time: int
    fx_rate_ppm: int | None = None
    sell_override_minor: int | None = None


@dataclass(frozen=True)
class LineTotal:
    line_id: str
    day_number: int | None
    category: str
    cost_minor: int
    sell_minor: int


@dataclass(frozen=True)
class DayTotal:
    day_number: int | None
    cost_minor: int
    sell_minor: int


@dataclass(frozen=True)
class CategoryTotal:
    category: str
    cost_minor: int
    sell_minor: int


@dataclass(frozen=True)
class CostingSummary:
    cost_total_minor: int
    sell_total_minor: int
    margin_minor: int
    margin_bps: int
    lines: tuple[LineTotal, ...]
    by_day: tuple[DayTotal, ...]
    by_category: tuple[CategoryTotal, ...]


def _round_half_up_div(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        raise ValueError("denominator must be > 0")
    half = denominator // 2
    if numerator >= 0:
        return (numerator + half) // denominator
    return -((-numerator + half) // denominator)


def _ceil_div(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        raise ValueError("denominator must be > 0")
    quotient, remainder = divmod(numerator, denominator)
    return quotient if remainder == 0 else quotient + 1


def _round_up_to_increment(amount_minor: int, increment_minor: int) -> int:
    if increment_minor <= 0:
        return amount_minor
    remainder = amount_minor % increment_minor
    if remainder == 0:
        return amount_minor
    return amount_minor + (increment_minor - remainder)


def line_cost_minor(line: ServiceLineInput) -> int:
    """cost = unit_cost × qty_unit × qty_time, converted to sheet currency via fx_rate_ppm.

    ``fx_rate_ppm`` is parts-per-million (1_000_000 == 1:1); rounded half-up when present.
    """
    base = line.unit_cost_minor * line.qty_unit * line.qty_time
    if line.fx_rate_ppm is None:
        return base
    return _round_half_up_div(base * line.fx_rate_ppm, _PPM_DIVISOR)


def line_sell_minor(
    line: ServiceLineInput,
    *,
    cost_minor: int,
    markup_rate_bps: int,
    rounding_increment_minor: int,
) -> int:
    """sell = sell_override ?? cost × (1 + markup_bps / 10_000), rounded up to the increment.

    An explicit ``sell_override_minor`` wins outright and is never re-rounded —
    it is the sale's own typed number.
    """
    if line.sell_override_minor is not None:
        return line.sell_override_minor
    raw_sell = _ceil_div(cost_minor * (_BPS_DIVISOR + markup_rate_bps), _BPS_DIVISOR)
    return _round_up_to_increment(raw_sell, rounding_increment_minor)


def summarize(
    lines: list[ServiceLineInput],
    *,
    markup_rate_bps: int,
    rounding_increment_minor: int,
) -> CostingSummary:
    """Compute every line's cost/sell plus sheet-level and grouped totals.

    Server returns this whole block; the FE grid never re-derives totals from
    raw lines on its own (chốt #4) — it renders exactly what this returns.
    """
    line_totals: list[LineTotal] = []
    for line in lines:
        cost = line_cost_minor(line)
        sell = line_sell_minor(
            line, cost_minor=cost, markup_rate_bps=markup_rate_bps, rounding_increment_minor=rounding_increment_minor
        )
        line_totals.append(
            LineTotal(line_id=line.line_id, day_number=line.day_number, category=line.category, cost_minor=cost, sell_minor=sell)
        )

    cost_total = sum(item.cost_minor for item in line_totals)
    sell_total = sum(item.sell_minor for item in line_totals)
    margin_minor = sell_total - cost_total
    margin_bps = _round_half_up_div(margin_minor * _BPS_DIVISOR, sell_total) if sell_total else 0

    by_day: dict[int | None, list[int]] = {}
    by_category: dict[str, list[int]] = {}
    for item in line_totals:
        day_bucket = by_day.setdefault(item.day_number, [0, 0])
        day_bucket[0] += item.cost_minor
        day_bucket[1] += item.sell_minor
        cat_bucket = by_category.setdefault(item.category, [0, 0])
        cat_bucket[0] += item.cost_minor
        cat_bucket[1] += item.sell_minor

    return CostingSummary(
        cost_total_minor=cost_total,
        sell_total_minor=sell_total,
        margin_minor=margin_minor,
        margin_bps=margin_bps,
        lines=tuple(line_totals),
        by_day=tuple(DayTotal(day_number=day, cost_minor=v[0], sell_minor=v[1]) for day, v in by_day.items()),
        by_category=tuple(CategoryTotal(category=cat, cost_minor=v[0], sell_minor=v[1]) for cat, v in by_category.items()),
    )
