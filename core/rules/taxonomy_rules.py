"""Pure domain rules for multilingual taxonomy defaults, travel styles sync, and market currencies."""

from __future__ import annotations

from typing import Any

MULTILINGUAL_DEFAULT_MEALS: dict[str, list[str]] = {
    "en": ["Breakfast"],
    "vi": ["Bữa sáng"],
    "ar": ["الإفطار"],
}


def get_default_meals_for_lang(lang: str | None) -> list[str]:
    """Return localized default meal items based on selected quotation language."""
    clean_lang = (lang or "en").strip().lower()
    return list(MULTILINGUAL_DEFAULT_MEALS.get(clean_lang, MULTILINGUAL_DEFAULT_MEALS["en"]))


def sync_travel_style_facts(customer_facts: dict[str, Any]) -> dict[str, Any]:
    """Bidirectional sync helper between travel_style and guest_profile in customer_facts."""
    if not isinstance(customer_facts, dict):
        return customer_facts

    travel_style = customer_facts.get("travel_style") or customer_facts.get("guest_profile") or ""
    customer_facts["travel_style"] = travel_style
    customer_facts["guest_profile"] = travel_style
    return customer_facts


def infer_default_currency(brand_id: str | None, market: str | None) -> str:
    """Infer the default 3-letter ISO currency code based on customer market or brand preference."""
    market_lower = (market or "").strip().lower()

    if "vietnam" in market_lower or "vn" in market_lower:
        return "VND"
    if "europe" in market_lower or "eu" in market_lower or "germany" in market_lower or "france" in market_lower:
        return "EUR"
    if "uk" in market_lower or "britain" in market_lower or "united kingdom" in market_lower:
        return "GBP"
    if "australia" in market_lower or "au" in market_lower:
        return "AUD"

    return "USD"
