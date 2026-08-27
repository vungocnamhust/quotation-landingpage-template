from __future__ import annotations

from core.rules.costing_rules import ServiceLineInput, line_cost_minor, line_sell_minor, summarize


def _line(**overrides):
    defaults = dict(
        line_id="l1",
        day_number=1,
        category="accommodation",
        unit_cost_minor=100,
        qty_unit=1,
        qty_time=1,
        fx_rate_ppm=None,
        sell_override_minor=None,
    )
    defaults.update(overrides)
    return ServiceLineInput(**defaults)


def test_line_cost_minor_multiplies_unit_qty_time():
    line = _line(unit_cost_minor=500_000, qty_unit=2, qty_time=3)
    assert line_cost_minor(line) == 3_000_000


def test_line_cost_minor_applies_fx_rate_ppm_round_half_up():
    # 100 * 1 * 1 = 100 minor units cost currency; fx 333_333 ppm -> 33.3333 -> rounds to 33
    line = _line(unit_cost_minor=100, fx_rate_ppm=333_333)
    assert line_cost_minor(line) == 33

    # 100 * 335_000 ppm = 33.5 -> half-up rounds to 34
    line2 = _line(unit_cost_minor=100, fx_rate_ppm=335_000)
    assert line_cost_minor(line2) == 34


def test_line_cost_minor_no_fx_is_identity():
    line = _line(unit_cost_minor=12_345, qty_unit=1, qty_time=1, fx_rate_ppm=None)
    assert line_cost_minor(line) == 12_345


def test_line_sell_minor_override_wins_and_is_not_rerounded():
    line = _line(sell_override_minor=999)
    sell = line_sell_minor(line, cost_minor=1_000_000, markup_rate_bps=2_000, rounding_increment_minor=10_000)
    assert sell == 999


def test_line_sell_minor_applies_markup_and_rounds_up_to_increment_vnd():
    # VND: divisor 1, rounding increment 10_000
    line = _line(unit_cost_minor=1_000_000, qty_unit=1, qty_time=1)
    cost = line_cost_minor(line)
    sell = line_sell_minor(line, cost_minor=cost, markup_rate_bps=1_500, rounding_increment_minor=10_000)
    # raw = 1_000_000 * 1.15 = 1_150_000 -> already a multiple of 10_000
    assert sell == 1_150_000


def test_line_sell_minor_rounds_up_when_not_exact_multiple():
    line = _line(unit_cost_minor=333, qty_unit=1, qty_time=1)
    cost = line_cost_minor(line)  # 333
    sell = line_sell_minor(line, cost_minor=cost, markup_rate_bps=1_000, rounding_increment_minor=10_000)
    # raw = ceil(333 * 11000 / 10000) = ceil(366.3) = 367 -> round up to 10_000
    assert sell == 10_000


def test_line_sell_minor_no_rounding_increment_zero_means_no_op():
    line = _line(unit_cost_minor=100, qty_unit=1, qty_time=1)
    cost = line_cost_minor(line)
    sell = line_sell_minor(line, cost_minor=cost, markup_rate_bps=2_500, rounding_increment_minor=0)
    # raw = ceil(100 * 12500 / 10000) = ceil(125) = 125
    assert sell == 125


def test_summarize_usd_cents_golden():
    # USD: divisor 100 (cents). Two lines, no fx.
    lines = [
        _line(line_id="a", day_number=1, category="accommodation", unit_cost_minor=10_000, qty_unit=2, qty_time=2),
        _line(line_id="b", day_number=2, category="transport", unit_cost_minor=5_000, qty_unit=1, qty_time=1),
    ]
    summary = summarize(lines, markup_rate_bps=2_000, rounding_increment_minor=100)
    assert summary.cost_total_minor == 40_000 + 5_000
    # sell: line a raw = ceil(40000*12000/10000)=48000 -> already multiple of 100
    # line b raw = ceil(5000*12000/10000)=6000
    assert summary.sell_total_minor == 48_000 + 6_000
    assert summary.margin_minor == summary.sell_total_minor - summary.cost_total_minor
    assert len(summary.by_day) == 2
    assert len(summary.by_category) == 2


def test_summarize_with_fx_rate_ppm_uneven_conversion():
    lines = [
        _line(line_id="a", unit_cost_minor=777, fx_rate_ppm=123_456, qty_unit=3, qty_time=1),
    ]
    summary = summarize(lines, markup_rate_bps=0, rounding_increment_minor=1)
    expected_cost = line_cost_minor(lines[0])
    assert summary.cost_total_minor == expected_cost
    assert summary.sell_total_minor == expected_cost  # 0 bps markup, increment 1 -> identity
    assert summary.margin_minor == 0
    assert summary.margin_bps == 0


def test_summarize_zero_lines_returns_zeroed_summary():
    summary = summarize([], markup_rate_bps=1_000, rounding_increment_minor=10_000)
    assert summary.cost_total_minor == 0
    assert summary.sell_total_minor == 0
    assert summary.margin_minor == 0
    assert summary.margin_bps == 0
    assert summary.lines == ()
    assert summary.by_day == ()
    assert summary.by_category == ()


def test_summarize_groups_multiple_lines_same_day_and_category():
    lines = [
        _line(line_id="a", day_number=1, category="accommodation", unit_cost_minor=1_000),
        _line(line_id="b", day_number=1, category="accommodation", unit_cost_minor=2_000),
        _line(line_id="c", day_number=None, category="visa", unit_cost_minor=500),
    ]
    summary = summarize(lines, markup_rate_bps=0, rounding_increment_minor=0)
    by_day = {d.day_number: d for d in summary.by_day}
    assert by_day[1].cost_minor == 3_000
    assert by_day[None].cost_minor == 500
    by_cat = {c.category: c for c in summary.by_category}
    assert by_cat["accommodation"].cost_minor == 3_000
    assert by_cat["visa"].cost_minor == 500
