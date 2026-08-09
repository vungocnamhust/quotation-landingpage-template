"""Compatibility boundary for historical V2 Fact snapshots.

Legacy drafts stored editorial fields alongside Facts.  The current Facts
schema deliberately rejects those fields, so read paths must remove them before
validating a historical snapshot.  This adapter never restores editorial copy
to Facts and never mutates the stored snapshot.
"""
from __future__ import annotations

import copy
import html
import re
from typing import Any

from services.pricing_contract import normalize_legacy_pricing_facts


_TAG_RE = re.compile(r"<[^>]+>")
_TRIP_FACT_KEYS = {
    "destinations", "start_date", "end_date", "duration_days", "duration_nights",
    "itinerary", "special_requirements", "display_route_text", "display_travel_dates",
}
_DAY_FACT_KEYS = {
    "day_number", "destination", "summary", "overnight", "meals", "highlights",
    "notes", "sense_of_pace", "display_date",
}
_BOOKING_ITEM_KEYS = {"key", "label", "body"}


def _plain_text(value: Any) -> str | None:
    if value is None:
        return None
    # Decode entities only after tags are removed: legacy cancellation terms
    # often use &lt; / &gt; as comparison prose, which must remain valid plain
    # text under the current booking Facts contract.
    text = html.unescape(_TAG_RE.sub(" ", str(value)))
    text = text.replace(">", "more than ").replace("<", "less than ")
    return " ".join(text.split())


def normalize_legacy_facts_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a current Facts payload from a non-mutating historical snapshot."""
    normalized = normalize_legacy_pricing_facts(copy.deepcopy(payload))
    trip = normalized.get("trip_facts")
    if isinstance(trip, dict):
        normalized_trip = {key: value for key, value in trip.items() if key in _TRIP_FACT_KEYS}
        itinerary = normalized_trip.get("itinerary")
        if isinstance(itinerary, list):
            normalized_trip["itinerary"] = [
                {key: value for key, value in day.items() if key in _DAY_FACT_KEYS}
                for day in itinerary if isinstance(day, dict)
            ]
        normalized["trip_facts"] = normalized_trip

    booking = normalized.get("booking_facts")
    if isinstance(booking, dict):
        items = booking.get("items")
        normalized["booking_facts"] = {
            "title": _plain_text(booking.get("title")),
            "description": _plain_text(booking.get("description")),
            "items": [
                {key: _plain_text(value) for key, value in item.items() if key in _BOOKING_ITEM_KEYS}
                for item in items if isinstance(item, dict)
            ] if isinstance(items, list) else [],
        }
    return normalized
