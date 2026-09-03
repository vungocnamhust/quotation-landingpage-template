"""Shared ORM-to-pure-rule adapter for rate selection.

The selection engine intentionally knows no SQLAlchemy models. Every server
consumer crosses this adapter instead of re-implementing blackout and
price-line mapping with subtly different semantics.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Iterable

from core.rules.rate_selection import BlackoutWindow, RateCandidate, RatePriceLineCandidate


def rate_candidates_from_rows(rates: Iterable[Any]) -> list[RateCandidate]:
    candidates: list[RateCandidate] = []
    for rate in rates:
        blackouts = tuple(
            BlackoutWindow(
                from_date=date.fromisoformat(window["from"]),
                to_date=date.fromisoformat(window["to"]),
                reason=window.get("reason", ""),
            )
            for window in (rate.blackout_json or [])
        )
        lines = tuple(
            RatePriceLineCandidate(
                price_for=line.price_for,
                occupancy_basis=line.occupancy_basis,
                unit=line.unit,
                amount_minor=line.amount_minor,
                tier_min_pax=line.tier_min_pax,
                tier_max_pax=line.tier_max_pax,
            )
            for line in rate.lines
        )
        candidates.append(
            RateCandidate(
                rate_id=rate.id,
                lifecycle_status=rate.lifecycle_status,
                valid_from=rate.valid_from,
                valid_to=rate.valid_to,
                min_pax=rate.min_pax,
                max_pax=rate.max_pax,
                blackouts=blackouts,
                lines=lines,
            )
        )
    return candidates
