"""Carry Content safely across immutable quotation business versions."""
from __future__ import annotations

import copy
from typing import Any


class SemanticContentCarryForwardService:
    """Content-only copier; Facts and Design remain outside this boundary."""

    _DAY_CONTENT_KEYS = ("title", "description", "activities", "labelHighlights", "labelNotes")
    _SEMANTIC_KEYS = ("destinationRef", "segmentCity", "overnight")

    @classmethod
    def carry_forward(cls, predecessor: dict[str, Any], successor: dict[str, Any]) -> dict[str, Any]:
        result = copy.deepcopy(successor)
        previous_days = ((predecessor.get("itinerary") or {}).get("days") or [])
        next_days = ((result.get("itinerary") or {}).get("days") or [])
        previous_by_fact_id = {str(day.get("sourceFactId")): day for day in previous_days if day.get("sourceFactId")}

        for day in next_days:
            previous_day = previous_by_fact_id.get(str(day.get("sourceFactId")))
            if previous_day is None or any(previous_day.get(key) != day.get(key) for key in cls._SEMANTIC_KEYS):
                continue
            for key in cls._DAY_CONTENT_KEYS:
                day[key] = copy.deepcopy(previous_day.get(key, day.get(key)))

        cls._carry_safe_media_overrides(predecessor, result)
        return result

    @classmethod
    def _carry_safe_media_overrides(cls, predecessor: dict[str, Any], successor: dict[str, Any]) -> None:
        old_days = ((predecessor.get("itinerary") or {}).get("days") or [])
        new_days = ((successor.get("itinerary") or {}).get("days") or [])
        old_by_id = {str(day.get("sourceFactId")): (index, day) for index, day in enumerate(old_days) if day.get("sourceFactId")}
        old_overrides = ((predecessor.get("presentation") or {}).get("mediaOverrides") or {})
        overrides: dict[str, Any] = {}
        for new_index, day in enumerate(new_days):
            pair = old_by_id.get(str(day.get("sourceFactId")))
            if pair is None:
                continue
            old_index, old_day = pair
            if any(old_day.get(key) != day.get(key) for key in cls._SEMANTIC_KEYS):
                continue
            prefix = f"itinerary.days.{old_index}."
            for key, value in old_overrides.items():
                if key.startswith(prefix):
                    overrides[f"itinerary.days.{new_index}.{key[len(prefix):]}"] = copy.deepcopy(value)
        presentation = successor.setdefault("presentation", {})
        if overrides:
            presentation["mediaOverrides"] = overrides
        else:
            presentation.pop("mediaOverrides", None)
