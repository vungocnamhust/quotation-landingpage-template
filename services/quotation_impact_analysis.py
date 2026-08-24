"""Content-only, registry-driven immutable Facts change planning."""
from __future__ import annotations

import json
from hashlib import sha256
from typing import Any

from services.content_registry import CONTENT_SECTION_REGISTRY, FactDependency, scope_spec


def facts_hash(facts: dict[str, Any]) -> str:
    return sha256(json.dumps(facts, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _at(value: dict[str, Any], path: str) -> Any:
    current: Any = value
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _summary(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return {"label": value.get("destination") or value.get("name") or value.get("id") or "Changed item", "value": value}
    return {"value": value}


def _target(*, scope: str, dependency: FactDependency, treatment: str, entity_key: str, old: Any, new: Any) -> dict[str, Any]:
    return {
        "stage": "content", "scope": scope,
        "target_path": dependency.target_paths[0] if dependency.target_paths else "/",
        "treatment": treatment,
        "affected_fields_json": [{"path": path, "label": path.rsplit(".", 1)[-1]} for path in dependency.target_paths],
        "generation_eligible": treatment == "generation_candidate",
        "deep_link_json": {"stage": "content", "section": scope, "focus": scope.rsplit(":", 1)[-1]},
    }


def _global_impacts(previous: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for scope, spec in CONTENT_SECTION_REGISTRY.items():
        if spec.owner != "content":
            continue
        for dependency in spec.fact_used:
            old, new = _at(previous, dependency.path), _at(current, dependency.path)
            if old == new:
                continue
            treatment = "derived_rebuilt" if dependency.impact_policy == "preserve_content_rebuild_labels" else "generation_candidate"
            results.append({
                "stage": "content", "scope": scope, "action": "review_content", "source_path": dependency.path,
                "target_path": dependency.target_paths[0] if dependency.target_paths else None,
                "explanation": f"{scope.replace('_', ' ').title()} uses {dependency.path}; review the affected content.",
                "status": "pending", "entity_key": scope, "operation": "changed",
                "old_value_json": _summary(old), "new_value_json": _summary(new), "generation_eligible": treatment == "generation_candidate",
                "targets": [_target(scope=scope, dependency=dependency, treatment=treatment, entity_key=scope, old=old, new=new)],
            })
    return results


def _itinerary_impacts(previous: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    old_days = [day for day in _at(previous, "trip_facts.itinerary") or [] if isinstance(day, dict)]
    new_days = [day for day in _at(current, "trip_facts.itinerary") or [] if isinstance(day, dict)]
    # Numeric identity is retained only for historical snapshots that have no
    # immutable Fact ID. New business versions always use the Facts `id`.
    old_by_id = {str(day.get("id") or day.get("day_number")): day for day in old_days}
    new_by_id = {str(day.get("id") or day.get("day_number")): day for day in new_days}
    results: list[dict[str, Any]] = []
    for fact_id in sorted(set(old_by_id) | set(new_by_id)):
        old, new = old_by_id.get(fact_id), new_by_id.get(fact_id)
        ref = new or old or {}
        number = ref.get("day_number") or "?"
        scope, entity_key = f"itinerary:day:{fact_id}", f"day:{fact_id}"
        spec = scope_spec(scope)
        identity = next(item for item in spec.fact_used if item.role == "semantic_identity")
        if old is None:
            targets = [_target(scope=scope, dependency=identity, treatment="generation_candidate", entity_key=entity_key, old=None, new=new)]
            operation, explanation = "added", f"Day {number} is new; no narrative is inherited."
        elif new is None:
            targets = [_target(scope=scope, dependency=identity, treatment="retired", entity_key=entity_key, old=old, new=None)]
            operation, explanation = "removed", f"Day {number} was removed; its narrative is retired."
        else:
            changed = [item for item in spec.fact_used if old.get(item.path.rsplit(".", 1)[-1]) != new.get(item.path.rsplit(".", 1)[-1])]
            if not changed and old.get("day_number") != new.get("day_number"):
                position = next(item for item in spec.fact_used if item.path.endswith("display_date"))
                targets = [_target(scope=scope, dependency=position, treatment="derived_rebuilt", entity_key=entity_key, old=old, new=new)]
                operation, explanation = "reordered", f"Day {number} was reordered; content remains bound to this Fact identity."
                results.append({"stage": "content", "scope": scope, "action": "preserve_content", "source_path": "trip_facts.itinerary[].day_number", "target_path": "/itinerary/days", "explanation": explanation, "status": "pending", "entity_key": entity_key, "operation": operation, "old_value_json": _summary(old), "new_value_json": _summary(new), "generation_eligible": False, "targets": targets})
                continue
            if not changed:
                continue
            targets = [_target(scope=scope, dependency=item, treatment="generation_candidate" if item.impact_policy != "preserve_content_rebuild_labels" else "derived_rebuilt", entity_key=entity_key, old=old, new=new) for item in changed]
            operation, explanation = "changed", f"Day {number} changed; content stays bound to this Fact identity."
        results.append({"stage": "content", "scope": scope, "action": "review_content", "source_path": "trip_facts.itinerary", "target_path": "/itinerary/days", "explanation": explanation, "status": "pending", "entity_key": entity_key, "operation": operation, "old_value_json": _summary(old), "new_value_json": _summary(new), "generation_eligible": any(item["generation_eligible"] for item in targets), "targets": targets})
    # If one day changes, the remaining stable entities are deliberately
    # recorded as preserved. This gives Impact Center an auditable explanation
    # for why their prose was not regenerated or overwritten.
    if results:
        for fact_id in sorted(set(old_by_id) & set(new_by_id)):
            old, new = old_by_id[fact_id], new_by_id[fact_id]
            if old != new:
                continue
            scope = f"itinerary:day:{fact_id}"
            dependency = next(item for item in scope_spec(scope).fact_used if item.role == "semantic_identity")
            results.append({
                "stage": "content", "scope": scope, "action": "preserve_content", "source_path": "trip_facts.itinerary",
                "target_path": "/itinerary/days", "explanation": f"Day {new.get('day_number') or '?'} did not change; inherited content is preserved.",
                "status": "pending", "entity_key": f"day:{fact_id}", "operation": "unchanged",
                "old_value_json": _summary(old), "new_value_json": _summary(new), "generation_eligible": False,
                "targets": [_target(scope=scope, dependency=dependency, treatment="preserved_unchanged", entity_key=f"day:{fact_id}", old=old, new=new)],
            })
    return results


class ContentImpactAnalysisService:
    @staticmethod
    def analyze(previous: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
        return sorted(_itinerary_impacts(previous, current) + _global_impacts(previous, current), key=lambda row: (row["scope"], row["source_path"], row["entity_key"]))


ImpactAnalysisService = ContentImpactAnalysisService
