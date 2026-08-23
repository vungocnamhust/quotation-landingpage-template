"""Pure, deterministic change planning for immutable quotation Facts."""
from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Literal, TypedDict


Stage = Literal["content", "design"]


class Impact(TypedDict):
    stage: Stage
    scope: str
    action: str
    source_path: str
    target_path: str
    explanation: str
    status: str
    entity_key: str
    operation: str
    old_value_json: dict[str, Any] | None
    new_value_json: dict[str, Any] | None
    generation_eligible: bool


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


def _display(value: Any) -> dict[str, Any] | None:
    return None if value is None else {"value": value}


def _impact(*, stage: Stage, scope: str, source_path: str, target_path: str, explanation: str, entity_key: str = "", operation: str = "changed", old: Any = None, new: Any = None, generation_eligible: bool = False) -> Impact:
    return {"stage": stage, "scope": scope, "action": "review_content" if stage == "content" else "review_design", "source_path": source_path, "target_path": target_path, "explanation": explanation, "status": "pending", "entity_key": entity_key, "operation": operation, "old_value_json": _display(old), "new_value_json": _display(new), "generation_eligible": generation_eligible}


def _day_key(day: dict[str, Any], index: int) -> str:
    # Fact IDs are immutable identity.  A day may move in the itinerary without
    # becoming a different editorial entity; its position is only a fallback
    # for snapshots created before IDs were required.
    return f"day:{day.get('id') or day.get('day_number') or index + 1}"


def _day_fingerprint(day: dict[str, Any]) -> tuple[Any, ...]:
    return (day.get("destination_ref") or day.get("destination"), day.get("overnight"), day.get("display_date"))


def _itinerary_impacts(previous: dict[str, Any], current: dict[str, Any]) -> list[Impact]:
    old_days = list(_value_at(previous, "trip_facts.itinerary") or [])
    new_days = list(_value_at(current, "trip_facts.itinerary") or [])
    old_by_key = {_day_key(day, index): day for index, day in enumerate(old_days) if isinstance(day, dict)}
    new_by_key = {_day_key(day, index): day for index, day in enumerate(new_days) if isinstance(day, dict)}
    impacts: list[Impact] = []
    def sort_key(item: str) -> tuple[int, str]:
        day = new_by_key.get(item) or old_by_key.get(item) or {}
        return (int(day.get("day_number") or 0), item)

    for key in sorted(set(old_by_key) | set(new_by_key), key=sort_key):
        old_day, new_day = old_by_key.get(key), new_by_key.get(key)
        number = str((new_day or old_day or {}).get("day_number") or "?")
        scope, target = f"itinerary:day:{number}", f"/itinerary/days/{int(number) - 1}"
        if old_day is None:
            impacts += [_impact(stage="content", scope=scope, source_path="trip_facts.itinerary", target_path=target, explanation=f"Day {number} is new; create its narrative from the new Facts.", entity_key=key, operation="added", new=new_day, generation_eligible=True), _impact(stage="design", scope=f"itinerary-day-media:{number}", source_path="trip_facts.itinerary", target_path=f"{target}/images", explanation=f"Day {number} is new; resolve its destination media and layout without changing existing days.", entity_key=key, operation="added", new=new_day, generation_eligible=True)]
        elif new_day is None:
            impacts.append(_impact(stage="content", scope=scope, source_path="trip_facts.itinerary", target_path=target, explanation=f"Day {number} was removed; its inherited narrative and media are retired.", entity_key=key, operation="removed", old=old_day))
        elif _day_fingerprint(old_day) != _day_fingerprint(new_day):
            impacts += [_impact(stage="content", scope=scope, source_path="trip_facts.itinerary", target_path=target, explanation=f"Day {number} changed destination, overnight, or date; do not carry its old narrative forward.", entity_key=key, old=old_day, new=new_day, generation_eligible=True), _impact(stage="design", scope=f"itinerary-day-media:{number}", source_path="trip_facts.itinerary", target_path=f"{target}/images", explanation=f"Day {number} destination media and layout must be reviewed against the new route.", entity_key=key, old=old_day, new=new_day, generation_eligible=True)]
        elif old_day.get("day_number") != new_day.get("day_number"):
            impacts.append(_impact(stage="design", scope="route-map", source_path="trip_facts.itinerary", target_path="/route/staySegments", explanation=f"Day {number} moved in the route. Narrative and media stay with the same Fact day identity; route sequence is rebuilt.", entity_key=key, operation="reordered", old=old_day.get("day_number"), new=new_day.get("day_number")))
        elif old_day != new_day:
            impacts.append(_impact(stage="content", scope=scope, source_path="trip_facts.itinerary", target_path=target, explanation=f"Day {number} facts changed; review only Day {number} narrative.", entity_key=key, old=old_day, new=new_day, generation_eligible=True))
    if old_days != new_days:
        impacts += [_impact(stage="content", scope="route", source_path="trip_facts.itinerary", target_path="/route", explanation="Route sequence changed; review route copy and map-segment descriptions.", old=old_days, new=new_days, generation_eligible=True), _impact(stage="content", scope="itinerary", source_path="trip_facts.itinerary", target_path="/itinerary", explanation="Itinerary composition changed; review its introduction without regenerating unchanged day narratives.", old=old_days, new=new_days, generation_eligible=True), _impact(stage="design", scope="route-map", source_path="trip_facts.itinerary", target_path="/route/staySegments", explanation="Route markers and map geometry are rebuilt from the changed itinerary.", old=old_days, new=new_days)]
    return impacts


_SIMPLE_DEPENDENCIES: tuple[tuple[str, tuple[tuple[Stage, str, str, str, bool], ...]], ...] = (
    ("trip_facts.destinations", (("content", "hero", "/hero", "Destination changes require Hero review.", True), ("content", "overview_letter", "/narrative", "Destination changes require overview review.", True), ("content", "route", "/route", "Destination changes require route review.", True), ("design", "route-map", "/route/staySegments", "Destination changes require map review.", False))),
    ("trip_facts.start_date", (("content", "hero", "/hero", "Travel dates changed; review Hero metadata.", True),)),
    ("trip_facts.end_date", (("content", "hero", "/hero", "Travel dates changed; review Hero metadata.", True),)),
    ("customer_facts.adults", (("content", "hero", "/hero", "Guest party changed; review guest-facing Hero copy.", True), ("content", "overview_letter", "/narrative", "Guest party changed; review overview copy.", True), ("design", "pricing-layout", "/pricing", "Guest-party pricing presentation changed.", False))),
    ("customer_facts.children", (("content", "hero", "/hero", "Guest party changed; review guest-facing Hero copy.", True), ("content", "overview_letter", "/narrative", "Guest party changed; review overview copy.", True), ("design", "pricing-layout", "/pricing", "Guest-party pricing presentation changed.", False))),
    ("customer_facts.kid_ages", (("content", "hero", "/hero", "Children ages changed; review family-oriented copy.", True), ("design", "pricing-layout", "/pricing", "Children pricing breakdown changed.", False))),
    ("customer_facts.advisor_name", (("content", "overview_letter", "/narrative/letterSender", "B2B advisor attribution changed.", True),)),
    ("customer_facts.advisor_agency", (("content", "overview_letter", "/narrative/letterSender", "B2B advisor agency attribution changed.", True),)),
    ("brand_id", (("content", "hero", "/hero", "Brand voice changed; create a reviewed Hero draft.", True), ("content", "overview_letter", "/narrative", "Brand voice changed; create a reviewed overview draft.", True), ("design", "brand-presentation", "/presentation", "Brand presentation, logo, and defaults require review.", False))),
    ("lang", (("content", "hero", "/hero", "Language changed; existing editorial copy is not auto-translated.", True), ("content", "overview_letter", "/narrative", "Language changed; existing editorial copy is not auto-translated.", True), ("content", "route", "/route", "Language changed; route narrative needs a reviewed draft.", True), ("content", "itinerary", "/itinerary", "Language changed; itinerary introduction needs a reviewed draft.", True))),
    ("presentation_options.template_id", (("design", "template-layout", "/presentation", "Template selection changed; compatible presentation overrides are retained and must be reviewed.", False),)),
)


def _pricing_impacts(previous: dict[str, Any], current: dict[str, Any]) -> list[Impact]:
    fields = ("label", "currency", "per_traveler_amount_minor", "group_total_amount_minor", "per_adult_amount_minor", "per_child_amount_minor")
    old_options = {str(item.get("id") or index): item for index, item in enumerate(_value_at(previous, "pricing_facts.options") or []) if isinstance(item, dict)}
    new_options = {str(item.get("id") or index): item for index, item in enumerate(_value_at(current, "pricing_facts.options") or []) if isinstance(item, dict)}
    impacts: list[Impact] = []
    for key in sorted(set(old_options) | set(new_options)):
        old, new = old_options.get(key), new_options.get(key)
        for field in fields:
            old_value, new_value = (old or {}).get(field), (new or {}).get(field)
            if old_value != new_value:
                impacts.append(_impact(stage="design", scope=f"pricing-option:{key}", source_path=f"pricing_facts.options.{key}.{field}", target_path=f"/pricing/options/{key}/{field}", explanation=f"Pricing option {key} {field.replace('_', ' ')} changed; rebuild the price display and review its card layout.", entity_key=f"pricing:{key}", operation="added" if old is None else "removed" if new is None else "changed", old=old_value, new=new_value))
    return impacts


class ImpactAnalysisService:
    """Maps leaf-level Fact deltas to an auditable, user-visible change plan."""

    @staticmethod
    def analyze(previous: dict[str, Any], current: dict[str, Any]) -> list[Impact]:
        results = _itinerary_impacts(previous, current) + _pricing_impacts(previous, current)
        for source_path, dependencies in _SIMPLE_DEPENDENCIES:
            old, new = _value_at(previous, source_path), _value_at(current, source_path)
            if old != new:
                for stage, scope, target_path, explanation, generation_eligible in dependencies:
                    results.append(_impact(stage=stage, scope=scope, source_path=source_path, target_path=target_path, explanation=explanation, old=old, new=new, generation_eligible=generation_eligible))
        return sorted(results, key=lambda item: (item["stage"], item["scope"], item["source_path"], item["entity_key"]))
