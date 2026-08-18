"""Compatibility helpers for the typed V2 pricing facts contract."""
from __future__ import annotations

import copy
import re
from typing import Any


from core.rules import (
    SUPPORTED_CURRENCIES,
    currency_divisor,
    parse_legacy_amount_minor,
)

_SUPPORTED_CURRENCIES = SUPPORTED_CURRENCIES
_CURRENCY_RE = re.compile(r"\b(USD|VND|EUR|GBP|AUD)\b", re.IGNORECASE)
_AMOUNT_RE = re.compile(r"([0-9][0-9,]*(?:\.[0-9]+)?)")
_LEGACY_KEYS = {
    "currency", "total_budget", "price_basis", "option_label", "kicker",
    "display_title", "display_subtitle", "cta_label",
}


def normalize_legacy_pricing_facts(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a typed V2 request payload without mutating a legacy snapshot.

    Only the common, safely parseable legacy money format is migrated.  The
    canonical document remains the compatibility source for any option whose
    historical display text cannot be converted to a numeric amount.
    """
    normalized = copy.deepcopy(payload)
    pricing = normalized.get("pricing_facts")
    if not isinstance(pricing, dict):
        return normalized
    options = pricing.get("options")
    has_legacy = bool(_LEGACY_KEYS.intersection(pricing)) or any(
        isinstance(option, dict) and {"category", "name", "per_person_text", "total_text"}.intersection(option)
        for option in (options if isinstance(options, list) else [])
    )
    if not has_legacy:
        return normalized

    inherited_currency = str(pricing.get("currency") or "").upper()
    typed_options: list[dict[str, Any]] = []
    for index, option in enumerate(options if isinstance(options, list) else [], 1):
        if not isinstance(option, dict):
            continue
        per_text = option.get("per_person_text") or ""
        total_text = option.get("total_text") or ""
        match = _CURRENCY_RE.search(f"{per_text} {total_text}")
        currency = (match.group(1).upper() if match else inherited_currency)
        if currency not in _SUPPORTED_CURRENCIES:
            continue
        per_traveler_amount_minor = parse_legacy_amount_minor(per_text, currency)
        group_total_amount_minor = parse_legacy_amount_minor(total_text, currency)
        if per_traveler_amount_minor is None or group_total_amount_minor is None:
            continue
        typed_options.append({
            "id": str(option.get("id") or f"pricing-option-legacy-{index}"),
            "label": str(option.get("name") or option.get("category") or f"Option {index:02d}").strip(),
            "currency": currency,
            "per_traveler_amount_minor": per_traveler_amount_minor,
            "group_total_amount_minor": group_total_amount_minor,
        })
    normalized["pricing_facts"] = {
        "conditions": pricing.get("conditions") if isinstance(pricing.get("conditions"), list) else [],
        "options": typed_options,
    }
    return normalized
