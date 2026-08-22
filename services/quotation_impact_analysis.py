"""Pure impact analysis for immutable quotation Fact snapshots."""
from __future__ import annotations

import json
from hashlib import sha256
from typing import Any


_DEPENDENCIES: tuple[tuple[str, str, str, str], ...] = (
    ("trip_facts.destinations", "content", "hero", "Destination changes require editorial review."),
    ("trip_facts.destinations", "content", "overview_letter", "Destination changes require editorial review."),
    ("trip_facts.destinations", "content", "route", "Destination changes require route copy review."),
    ("trip_facts.destinations", "design", "route-map", "Destination changes require map and route-media review."),
    ("trip_facts.start_date", "content", "hero", "Travel-date changes require editorial review."),
    ("trip_facts.end_date", "content", "hero", "Travel-date changes require editorial review."),
    ("trip_facts.itinerary", "content", "itinerary", "Itinerary changes require itinerary review."),
    ("trip_facts.itinerary", "design", "itinerary-layout", "Itinerary changes require layout and media review."),
    ("customer_facts", "content", "hero", "Guest profile changes require editorial review."),
    ("customer_facts", "content", "overview_letter", "Guest profile changes require editorial review."),
    ("service_facts.hotels", "design", "hotel-media", "Hotel changes require hotel media review."),
    ("pricing_facts", "design", "pricing-layout", "Pricing changes require commercial presentation review."),
)


def facts_hash(facts: dict[str, Any]) -> str:
    payload = json.dumps(facts, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(payload.encode("utf-8")).hexdigest()


def _value_at(payload: dict[str, Any], path: str) -> Any:
    value: Any = payload
    for key in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _changed_paths(previous: dict[str, Any], current: dict[str, Any]) -> set[str]:
    paths = {source for source, *_rest in _DEPENDENCIES}
    return {path for path in paths if _value_at(previous, path) != _value_at(current, path)}


class ImpactAnalysisService:
    """Maps Fact deltas to persisted, review-required Content/Design work."""

    @staticmethod
    def analyze(previous: dict[str, Any], current: dict[str, Any]) -> list[dict[str, str]]:
        changed = _changed_paths(previous, current)
        results: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        for source_path, stage, scope, explanation in _DEPENDENCIES:
            if source_path not in changed:
                continue
            key = (stage, scope, source_path)
            if key in seen:
                continue
            seen.add(key)
            results.append({
                "stage": stage,
                "scope": scope,
                "action": "review_content" if stage == "content" else "review_design",
                "source_path": source_path,
                "target_path": None,
                "explanation": explanation,
                "status": "pending",
            })
        return results
