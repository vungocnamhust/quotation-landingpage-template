"""Pure reconciliation primitives for Actionable Content Plans."""
from __future__ import annotations

import json
from hashlib import sha256
from typing import Any

from core.rules.semantic_identity import SemanticEntityChange, itinerary_semantic_signature


def content_input_fingerprint(value: dict[str, Any]) -> str:
    """Hash a canonical prompt-input projection deterministically."""
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(serialized.encode("utf-8")).hexdigest()


def reconcile_itinerary_entities(
    previous_days: list[dict[str, Any]],
    current_days: list[dict[str, Any]],
) -> list[SemanticEntityChange]:
    """Compare itinerary Facts by sourceFactId, never by day number."""
    old_by_id = {str(day["id"]): day for day in previous_days if day.get("id")}
    new_by_id = {str(day["id"]): day for day in current_days if day.get("id")}
    changes: list[SemanticEntityChange] = []

    for fact_id in sorted(set(old_by_id) | set(new_by_id)):
        old = old_by_id.get(fact_id)
        new = new_by_id.get(fact_id)
        if old is None:
            changes.append(SemanticEntityChange(f"day:{fact_id}", "added", None, new, False))
            continue
        if new is None:
            changes.append(SemanticEntityChange(f"day:{fact_id}", "removed", old, None, False))
            continue
        if itinerary_semantic_signature(old) != itinerary_semantic_signature(new):
            changes.append(SemanticEntityChange(f"day:{fact_id}", "semantic_replaced", old, new, False))
            continue
        if old.get("day_number") != new.get("day_number"):
            changes.append(SemanticEntityChange(f"day:{fact_id}", "reordered", old, new, True))
            continue
        if old != new:
            changes.append(SemanticEntityChange(f"day:{fact_id}", "changed", old, new, True))
            continue
        changes.append(SemanticEntityChange(f"day:{fact_id}", "unchanged", old, new, True))
    return changes
