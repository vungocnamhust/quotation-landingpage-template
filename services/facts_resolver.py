"""Pure-ish fact resolution for the V2 canonical quotation boundary.

This service never mutates the caller's payload.  Catalog lookup is injected so
the deterministic result can be unit-tested without FastAPI or rendering.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any, Awaitable, Callable

from quote_document import CreateQuoteRequestV1

DestinationLookup = Callable[[str], Awaitable[Any | None]]


class FactsResolutionError(ValueError):
    def __init__(self, missing_inputs: list[str]) -> None:
        super().__init__("Destination not found in catalog.")
        self.missing_inputs = missing_inputs


def _as_ref(item: Any) -> dict[str, str]:
    return {"id": item.id, "name": item.canonical_name, "slug": item.slug}


def _date_label(start: str | None, end: str | None) -> tuple[str, int | None, int | None]:
    if not start or not end:
        return "", None, None
    try:
        start_date, end_date = date.fromisoformat(start), date.fromisoformat(end)
    except ValueError:
        return "", None, None
    if end_date < start_date:
        return "", None, None
    days = (end_date - start_date).days + 1
    return f"{start_date:%d %b %Y} – {end_date:%d %b %Y}", days, max(days - 1, 0)


class FactsResolver:
    async def resolve(self, payload: CreateQuoteRequestV1, lookup: DestinationLookup) -> tuple[CreateQuoteRequestV1, dict[str, Any]]:
        canonical = payload.model_copy(deep=True)
        missing: list[str] = []
        refs: dict[str, Any] = {"routeDestinationRefs": [], "itinerary": [], "hotels": []}

        async def resolve_destination(value: str | None, path: str) -> dict[str, str] | None:
            if value in (None, ""):
                return None
            item = await lookup(value)
            if item is None:
                missing.append(path)
                return None
            return _as_ref(item)

        route: list[str] = []
        for index, value in enumerate(canonical.trip_facts.destinations):
            ref = await resolve_destination(value, f"trip_facts.destinations[{index}]")
            if ref:
                route.append(ref["name"])
                refs["routeDestinationRefs"].append(ref)
        canonical.trip_facts.destinations = route

        for index, day in enumerate(canonical.trip_facts.itinerary):
            ref = await resolve_destination(day.destination, f"trip_facts.itinerary[{index}].destination")
            if ref:
                day.destination = ref["name"]
            overnight_ref = await resolve_destination(day.overnight, f"trip_facts.itinerary[{index}].overnight")
            if overnight_ref:
                day.overnight = overnight_ref["name"]
            refs["itinerary"].append({"dayNumber": day.day_number, "destinationRef": ref})
        for index, hotel in enumerate(canonical.service_facts.hotels):
            ref = await resolve_destination(hotel.destination, f"service_facts.hotels[{index}].destination")
            if ref:
                hotel.destination = ref["name"]
            refs["hotels"].append({"index": index, "destinationRef": ref})
        if missing:
            raise FactsResolutionError(missing)

        travel_dates, date_days, date_nights = _date_label(canonical.trip_facts.start_date, canonical.trip_facts.end_date)
        itinerary_days = len(canonical.trip_facts.itinerary)
        duration_days = date_days or canonical.trip_facts.duration_days or (itinerary_days or None)
        duration_nights = date_nights if date_nights is not None else (max(duration_days - 1, 0) if duration_days else None)
        adults, children = canonical.customer_facts.adults, canonical.customer_facts.children
        guests = [f"{adults} adult{'s' if adults != 1 else ''}" if adults is not None else "", f"{children} child{'ren' if children != 1 else ''}" if children else ""]
        party_label = ", ".join(value for value in guests if value)
        route_label = " · ".join(route)
        resolved = {
            **refs,
            "duration": {"days": duration_days, "nights": duration_nights, "label": f"{duration_days} days / {duration_nights} nights" if duration_days is not None and duration_nights is not None else ""},
            "travelDateLabel": travel_dates,
            "routeLabel": route_label,
            "partyLabel": party_label,
            "pricing": {"optionCount": len(canonical.pricing_facts.options)},
            "missingInputs": self.missing_inputs(canonical),
        }
        # Keep the UI contract flat while retaining the richer deterministic
        # preview object used by the API contract.
        resolved["durationDays"] = duration_days
        resolved["durationNights"] = duration_nights
        resolved["travelDatesLabel"] = travel_dates
        resolved["defaults"] = {"legalCopy": True}
        snapshot = canonical.model_dump(mode="json")
        resolved["factsHash"] = hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return canonical, resolved

    @staticmethod
    def missing_inputs(payload: CreateQuoteRequestV1) -> list[str]:
        missing: list[str] = []
        if not payload.brand_id:
            missing.append("brand_id")
        if not payload.lang:
            missing.append("lang")
        return missing
