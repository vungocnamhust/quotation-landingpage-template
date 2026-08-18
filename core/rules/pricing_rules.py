"""Pure domain rules for commercial pricing, child rate presets, and multi-currency math."""

from __future__ import annotations

import re
from typing import Any

SUPPORTED_CURRENCIES: frozenset[str] = frozenset({"USD", "EUR", "GBP", "AUD", "VND"})
_AMOUNT_RE = re.compile(r"([0-9][0-9,]*(?:\.[0-9]+)?)")


def currency_divisor(currency: str | None) -> int:
    """Returns the minor unit divisor (e.g. 100 for cents in USD/EUR/GBP, 1 for VND)."""
    return 1 if (currency or "").upper() == "VND" else 100


def parse_legacy_amount_minor(value: Any, currency: str) -> int | None:
    """Extract numeric money amount from legacy string and convert to minor unit integer."""
    if value is None:
        return None
    match = _AMOUNT_RE.search(str(value))
    if match is None:
        return None
    try:
        amount = float(match.group(1).replace(",", ""))
    except ValueError:
        return None
    if amount <= 0:
        return None
    return round(amount * currency_divisor(currency))


def calculate_tri_pricing(
    per_adult_minor: int | None,
    per_child_minor: int | None,
    adults: int = 2,
    children: int = 0,
) -> int | None:
    """Calculate Group Total Minor Price from 3-parameter pricing equation:

    Total = (adults * per_adult) + (children * per_child)
    """
    safe_adults = max(0, adults)
    safe_kids = max(0, children)

    if per_adult_minor is None or per_adult_minor <= 0:
        return None

    adult_subtotal = safe_adults * per_adult_minor
    child_subtotal = safe_kids * (per_child_minor if per_child_minor is not None and per_child_minor >= 0 else 0)

    return adult_subtotal + child_subtotal


def apply_child_preset_ratio(per_adult_minor: int | None, ratio: float) -> int | None:
    """Calculate per-child minor amount based on percentage preset (e.g. 0.5, 0.75, 1.0, 0.0)."""
    if per_adult_minor is None or per_adult_minor <= 0:
        return None
    if ratio <= 0:
        return 0
    return round(per_adult_minor * ratio)


def infer_rates_from_group_total(
    group_total_minor: int | None,
    adults: int = 2,
    children: int = 0,
    child_ratio: float = 0.75,
) -> tuple[int | None, int | None]:
    """Given a Group Total Price, deduce per_adult and per_child amounts using child ratio.

    Equation: Total = Adults * P_adult + Kids * (child_ratio * P_adult)
              P_adult = Total / (Adults + Kids * child_ratio)
    """
    if group_total_minor is None or group_total_minor <= 0:
        return None, None

    safe_adults = max(1, adults)
    safe_kids = max(0, children)

    weighted_units = safe_adults + (safe_kids * child_ratio)
    if weighted_units <= 0:
        return None, None

    per_adult = round(group_total_minor / weighted_units)
    per_child = round(per_adult * child_ratio) if safe_kids > 0 else None

    return per_adult, per_child
