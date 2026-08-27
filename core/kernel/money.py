"""K1 — money kernel: minor-unit integers, one currency, no float math.

15.3 (rates) is the first table with a money column, so the kernel lands here
instead of at repo bootstrap. ``SUPPORTED_CURRENCIES``/``currency_divisor`` stay
defined in ``core/rules/pricing_rules.py`` (quotation SSOT, unchanged) and are
re-exported here so callers only need to import from one place: the kernel.
"""
from __future__ import annotations

from core.rules.pricing_rules import SUPPORTED_CURRENCIES, currency_divisor

__all__ = ["SUPPORTED_CURRENCIES", "currency_divisor", "validate_currency", "validate_amount_minor"]


def validate_currency(currency: str) -> str:
    """Uppercase + validate against the SSOT currency list. Raises ValueError if unsupported."""
    normalized = (currency or "").upper()
    if normalized not in SUPPORTED_CURRENCIES:
        raise ValueError(f"Unsupported currency '{currency}'. Supported: {sorted(SUPPORTED_CURRENCIES)}")
    return normalized


def validate_amount_minor(amount_minor: int, *, field: str = "amount_minor") -> int:
    """Amounts are always integer minor units, always >= 0. No float ever crosses this line."""
    if not isinstance(amount_minor, int) or isinstance(amount_minor, bool):
        raise ValueError(f"{field} must be an integer minor-unit amount, got {type(amount_minor).__name__}")
    if amount_minor < 0:
        raise ValueError(f"{field} must be >= 0, got {amount_minor}")
    return amount_minor
