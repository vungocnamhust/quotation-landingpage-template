"""Server-owned readiness, derived from the Content ownership registry."""
from __future__ import annotations

from typing import Any

from quote_document import QuoteDocumentV1, SECTION_REGISTRY, validate_quote_document_sections
from services.content_registry import ContentSectionSpec, scope_spec


SECTION_SCOPE = {
    "hero": "hero",
    "overview_letter": "overview_letter",
    "route_map": "route",
    "itinerary": "itinerary",
    "hotel_plan": "hotel_plan",
    "pricing": "pricing",
    "inclusions_exclusions": "inclusions_exclusions",
    "booking_terms": "booking_terms",
    "designer": "designer",
}


def _add(store: dict[str, list[dict[str, str]]], section_id: str, path: str, message: str, owner: str) -> None:
    items = store.setdefault(section_id, [])
    if not any(item["path"] == path for item in items):
        items.append({"path": path, "message": message, "owner": owner})


def _content_missing(document: QuoteDocumentV1, section_type: str, section_id: str, store: dict[str, list[dict[str, str]]]) -> None:
    if section_type == "hero":
        if not document.trip.title.strip(): _add(store, section_id, "trip.title", "Trip title is required.", "content")
        if not document.trip.lede.strip(): _add(store, section_id, "trip.lede", "Hero introduction is required.", "content")
    elif section_type == "overview_letter":
        for path, value, label in (("narrative.letterIntro", document.narrative.letterIntro, "Opening paragraph"), ("narrative.letterBody2", document.narrative.letterBody2, "Letter body")):
            if not value.strip(): _add(store, section_id, path, f"{label} is required.", "content")
    elif section_type == "route_map":
        for path, value, label in (("route.title", document.route.title, "Route title"), ("route.description", document.route.description, "Route introduction")):
            if not value.strip(): _add(store, section_id, path, f"{label} is required.", "content")
    elif section_type == "itinerary":
        if not document.itinerary.title.strip(): _add(store, section_id, "itinerary.title", "Itinerary title is required.", "content")
        if not document.itinerary.description.strip(): _add(store, section_id, "itinerary.description", "Itinerary introduction is required.", "content")
        for index, day in enumerate(document.itinerary.days):
            if not day.title.strip(): _add(store, section_id, f"itinerary.days.{index}.title", f"Day {day.dayNumber} title is required.", "content")
            if not day.description: _add(store, section_id, f"itinerary.days.{index}.description", f"Day {day.dayNumber} narrative is required.", "content")


def _fact_requirement_is_missing(fact_missing_inputs: list[str], required_path: str) -> bool:
    return any(path == required_path or path.startswith(f"{required_path}.") or required_path.startswith(f"{path}.") for path in fact_missing_inputs)


def resolve_content_readiness(document_json: dict[str, Any], fact_missing_inputs: list[str]) -> list[dict[str, Any]]:
    document = QuoteDocumentV1.model_validate(document_json)
    missing_by_section: dict[str, list[dict[str, str]]] = {}
    for error in validate_quote_document_sections(document):
        if error.code == "missing_required_document_data":
            _add(missing_by_section, error.sectionId, error.path, error.message, "content")

    for section in document.layout.sections:
        if section.enabled:
            _content_missing(document, section.type, section.id, missing_by_section)

    result: list[dict[str, Any]] = []
    for section in document.layout.sections:
        if not section.enabled:
            continue
        scope_name = SECTION_SCOPE.get(section.type)
        spec: ContentSectionSpec | None = None
        if scope_name:
            spec = scope_spec(scope_name)
        missing = missing_by_section.get(section.id, [])
        fact_blockers = []
        if spec:
            fact_blockers = [path for path in spec.required_facts if _fact_requirement_is_missing(fact_missing_inputs, path)]
        elif fact_missing_inputs:
            fact_blockers = list(fact_missing_inputs)
        if fact_blockers:
            missing = [{"path": path, "message": "Required quotation fact is missing.", "owner": "fact"} for path in fact_blockers]
        elif spec and spec.owner == "fact" and missing:
            # Structured blocks are a deterministic view of commercial/legal
            # sources. Empty blocks therefore hand off to Facts, not an editor.
            missing = [{**item, "owner": "fact"} for item in missing]
        owner = "fact" if any(item.get("owner") == "fact" for item in missing) else "content"
        status = None if not missing else "can_thong_tin" if owner == "fact" else "chua_du_noi_dung"
        result.append({
            "sectionId": section.id,
            "sectionType": section.type,
            "label": SECTION_REGISTRY[section.type].label,
            "status": status,
            "missing": [{"path": item["path"], "message": item["message"]} for item in missing],
            "targetStage": "facts" if status == "can_thong_tin" else "content" if status == "chua_du_noi_dung" else None,
            "generator": bool(spec and spec.generation),
            "scope": scope_name,
            "automationPolicy": spec.automation_policy if spec else None,
        })
    return result
