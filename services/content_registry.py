"""Single ownership, editing, and generation-brief contract for Content Studio."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Literal


Owner = Literal["fact", "fact-derived", "content", "design"]
EditorControl = Literal["input", "textarea", "string-list"]


@dataclass(frozen=True)
class EditorField:
    id: str
    label: str
    path: tuple[str | int, ...]
    control: EditorControl = "input"
    required: bool = True
    min_length: int = 1
    max_length: int = 1600

    def public_payload(self) -> dict[str, object]:
        return {"id": self.id, "label": self.label, "path": list(self.path), "control": self.control, "required": self.required, "minLength": self.min_length, "maxLength": self.max_length}


@dataclass(frozen=True)
class FactInput:
    id: str
    label: str
    path: tuple[str | int, ...]
    required: bool = False

    def public_payload(self) -> dict[str, object]:
        return {"id": self.id, "label": self.label, "path": list(self.path), "required": self.required}


@dataclass(frozen=True)
class DefaultInstructions:
    storytelling: str
    detailed: str

    def for_mode(self, mode: str) -> str:
        return self.detailed if mode == "detailed" else self.storytelling

    def public_payload(self) -> dict[str, str]:
        return {"storytelling": self.storytelling, "detailed": self.detailed}


@dataclass(frozen=True)
class ContentSectionSpec:
    scope: str
    owner: Owner
    canonical_targets: tuple[str, ...]
    fact_allowlist: tuple[str, ...]
    required_facts: tuple[str, ...]
    editor: Literal["narrative", "fact-preview", "checklist"]
    block_allowlist: tuple[str, ...] = ()
    generation: bool = False
    recipe_version: str = "v1"
    schema_version: str = "v1"
    editor_fields: tuple[EditorField, ...] = ()
    fact_inputs: tuple[FactInput, ...] = ()
    default_instructions: DefaultInstructions | None = None


from core.rules.content_budgets import get_content_budget_registry


def _field(id: str, label: str, *path: str | int, control: EditorControl = "input", required: bool = True, min_length: int = 1, max_length: int = 1600) -> EditorField:
    return EditorField(id=id, label=label, path=path, control=control, required=required, min_length=min_length, max_length=max_length)


def _budget_field(scope: str, field_key: str) -> EditorField:
    spec = get_content_budget_registry("v1").get_spec(scope, field_key)
    if spec:
        return EditorField(
            id=spec.field_id,
            label=spec.label,
            path=spec.path,
            control=spec.control,  # type: ignore
            required=spec.required,
            min_length=spec.min_chars,
            max_length=spec.max_chars,
        )
    raise ValueError(f"Unknown budget field: {scope}.{field_key}")


def _fact(id: str, label: str, *path: str | int, required: bool = False) -> FactInput:
    return FactInput(id=id, label=label, path=path, required=required)


def _brief(scope: str) -> DefaultInstructions:
    from prompts.loader import get_prompt_loader
    loader = get_prompt_loader()
    return DefaultInstructions(
        storytelling=loader.get_default_instruction(scope, "storytelling"),
        detailed=loader.get_default_instruction(scope, "detailed"),
    )



CONTENT_SECTION_REGISTRY: dict[str, ContentSectionSpec] = {
    "hero": ContentSectionSpec(
        "hero", "content", ("trip.title", "trip.lede", "narrative.coverKicker", "narrative.heroMeta1", "narrative.heroMeta2", "narrative.footerText"),
        ("trip_facts.destinations", "trip_facts.start_date", "trip_facts.end_date", "trip_facts.duration_days", "trip_facts.duration_nights", "customer_facts.customer_name"),
        ("trip_facts.destinations",), "narrative", generation=True, recipe_version="v4", schema_version="v1",
        editor_fields=(
            _budget_field("hero", "trip_title"),
            _budget_field("hero", "trip_lede"),
            _budget_field("hero", "cover_kicker"),
            _budget_field("hero", "hero_meta_1"),
            _budget_field("hero", "hero_meta_2"),
            _budget_field("hero", "footer_text"),
        ),
        fact_inputs=(
            _fact("destinations", "Destinations", "trip_facts", "destinations", required=True),
            _fact("guest-name", "Guest name", "customer_facts", "customer_name"),
            _fact("start-date", "Start date", "trip_facts", "start_date"),
            _fact("end-date", "End date", "trip_facts", "end_date"),
            _fact("duration", "Duration", "trip_facts", "duration_days"),
        ),
        default_instructions=_brief("hero"),
    ),
    "overview_letter": ContentSectionSpec(
        "overview_letter", "content", ("narrative.journeyOverviewTitle", "narrative.letterHighlight", "narrative.letterGreeting", "narrative.letterIntro", "narrative.letterBody2", "narrative.letterOutro", "narrative.letterSignOff", "narrative.letterSender"),
        ("trip_facts.destinations", "trip_facts.start_date", "trip_facts.end_date", "trip_facts.duration_days", "trip_facts.duration_nights", "customer_facts.customer_name"),
        ("trip_facts.destinations",), "narrative", generation=True, recipe_version="v4", schema_version="v1",
        editor_fields=(
            _budget_field("overview_letter", "overview_title"),
            _budget_field("overview_letter", "letter_highlight"),
            _budget_field("overview_letter", "letter_greeting"),
            _budget_field("overview_letter", "letter_intro"),
            _budget_field("overview_letter", "letter_body"),
            _budget_field("overview_letter", "letter_outro"),
            _budget_field("overview_letter", "letter_signoff"),
            _budget_field("overview_letter", "letter_sender"),
        ),
        fact_inputs=(
            _fact("destinations", "Destinations", "trip_facts", "destinations", required=True),
            _fact("guest-name", "Guest name", "customer_facts", "customer_name"),
            _fact("start-date", "Start date", "trip_facts", "start_date"),
            _fact("end-date", "End date", "trip_facts", "end_date"),
            _fact("duration", "Duration", "trip_facts", "duration_days"),
        ),
        default_instructions=_brief("overview_letter"),
    ),
    "route": ContentSectionSpec(
        "route", "content", ("route.title", "route.description", "route.staySegments.*.mapSegmentDesc"),
        ("trip_facts.destinations", "trip_facts.itinerary"), ("trip_facts.destinations",), "narrative",
        generation=True, recipe_version="v5", schema_version="v2",
        editor_fields=(
            _budget_field("route", "route_title"),
            _budget_field("route", "route_description"),
            _budget_field("route", "map_segment_descriptions"),
        ),
        fact_inputs=(
            _fact("destinations", "Destinations", "trip_facts", "destinations", required=True),
            _fact("itinerary", "Itinerary days", "trip_facts", "itinerary"),
        ),
        default_instructions=_brief("route"),
    ),
    "itinerary": ContentSectionSpec(
        "itinerary", "content", ("itinerary.title", "itinerary.description"),
        ("trip_facts.itinerary",), ("trip_facts.itinerary",), "narrative",
        generation=True, recipe_version="v4", schema_version="v1",
        editor_fields=(
            _budget_field("itinerary", "itinerary_title"),
            _budget_field("itinerary", "itinerary_description"),
        ),
        fact_inputs=(_fact("itinerary", "Itinerary days", "trip_facts", "itinerary", required=True),),
        default_instructions=_brief("itinerary"),
    ),
    "hotel_plan": ContentSectionSpec("hotel_plan", "fact", ("stays.hotels", "stays.roomNotes"), ("service_facts.hotels",), ("service_facts.hotels",), "fact-preview"),
    "pricing": ContentSectionSpec("pricing", "fact", ("pricing.options", "pricing.conditions"), ("pricing_facts.options",), ("pricing_facts.options",), "fact-preview"),
    "inclusions_exclusions": ContentSectionSpec("inclusions_exclusions", "fact", ("content.sections.inclusions_exclusions",), ("service_facts.inclusions", "service_facts.exclusions"), ("service_facts.inclusions", "service_facts.exclusions"), "fact-preview", ("twoColumnList",)),
    "booking_terms": ContentSectionSpec("booking_terms", "fact", ("content.sections.booking_terms",), ("booking_facts",), ("booking_facts",), "fact-preview", ("paragraph", "termList", "paymentSchedule")),
    "designer": ContentSectionSpec("designer", "fact", ("designer",), ("designer_facts",), ("designer_facts",), "fact-preview"),
    "finalization": ContentSectionSpec("finalization", "content", ("content.sections.finalization",), ("finalization_facts.required_items", "finalization_facts.after_confirmation_items"), ("finalization_facts.required_items", "finalization_facts.after_confirmation_items"), "checklist", ("checklistGroups",), generation=False, recipe_version="v4", schema_version="v1", fact_inputs=(_fact("required-items", "Final details required", "finalization_facts", "required_items", required=True), _fact("after-confirmation", "After confirmation", "finalization_facts", "after_confirmation_items", required=True))),
}


ITINERARY_DAY_CANONICAL_TARGETS: tuple[str, ...] = (
    "itinerary.days.*.title",
    "itinerary.days.*.description",
    "itinerary.days.*.activities",
    "trip.priceBasis",
)


def content_owned_targets() -> tuple[str, ...]:
    registry_targets = [target for spec in CONTENT_SECTION_REGISTRY.values() if spec.owner == "content" for target in spec.canonical_targets]
    return tuple(registry_targets + list(ITINERARY_DAY_CANONICAL_TARGETS))



def scope_spec(scope: str) -> ContentSectionSpec:
    if scope.startswith("itinerary:day:") and scope.rsplit(":", 1)[-1].isdigit():
        return ContentSectionSpec(
            scope, "content", ("itinerary.days.*.title", "itinerary.days.*.description", "itinerary.days.*.activities"),
            ("trip_facts.itinerary",), ("trip_facts.itinerary",), "narrative", generation=True, recipe_version="v4", schema_version="v1",
            editor_fields=(
                _budget_field("itinerary_day", "title"),
                _budget_field("itinerary_day", "description"),
                _budget_field("itinerary_day", "activities"),
            ),
            fact_inputs=(
                _fact("day-destination", "Destination", "itineraryDay", "destination", required=True),
                _fact("day-summary", "Day summary", "itineraryDay", "summary", required=True),
                _fact("day-highlights", "Highlights", "itineraryDay", "highlights"),
            ),
            default_instructions=_brief("itinerary_day"),
        )

    try:
        return CONTENT_SECTION_REGISTRY[scope]
    except KeyError as exc:
        raise ValueError(f"Unsupported content scope: {scope}") from exc


def content_registry_payload(scope: str | None = None) -> dict[str, dict[str, object]]:
    specs = {scope: scope_spec(scope)} if scope else CONTENT_SECTION_REGISTRY
    return {key: {"owner": spec.owner, "generation": spec.generation, "editor": spec.editor, "recipeVersion": spec.recipe_version, "schemaVersion": spec.schema_version, "fields": [field.public_payload() for field in spec.editor_fields], "factInputs": [field.public_payload() for field in spec.fact_inputs], "defaultInstructions": spec.default_instructions.public_payload() if spec.default_instructions else None} for key, spec in specs.items()}


def _read_path(value: dict[str, Any], path: tuple[str | int, ...]) -> Any:
    current: Any = value
    for part in path:
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and isinstance(part, int) and 0 <= part < len(current):
            current = current[part]
        else:
            return None
    return current


def _write_path(value: dict[str, Any], path: tuple[str | int, ...], item: Any) -> None:
    current: dict[str, Any] = value
    for part in path[:-1]:
        if not isinstance(part, str):
            raise ValueError("Editor field paths may only contain object keys.")
        current = current.setdefault(part, {})
    current[path[-1]] = copy.deepcopy(item)


def project_candidate_from_document(document: dict[str, Any], scope: str) -> dict[str, Any]:
    """Return exactly the editable candidate shape for a canonical document."""
    spec = scope_spec(scope)
    if spec.owner != "content":
        raise ValueError(f"{scope} is Fact-owned and has no Content candidate.")
    if scope == "finalization":
        section = _read_path(document, ("content", "sections", "finalization")) or {"blocks": []}
        return {"content": {"sections": {"finalization": copy.deepcopy(section)}}}
    candidate: dict[str, Any] = {}
    if scope.startswith("itinerary:day:"):
        number = int(scope.rsplit(":", 1)[-1])
        day = next((item for item in ((document.get("itinerary") or {}).get("days") or []) if item.get("dayNumber") == number), None)
        if day is None:
            raise ValueError("Itinerary day no longer exists.")
        candidate["dayNumber"] = number
        for field in spec.editor_fields:
            candidate[field.path[0]] = copy.deepcopy(day.get(field.path[0], [] if field.control == "string-list" else ""))
        return candidate
    if scope == "route":
        route = copy.deepcopy(document.get("route") or {})
        return {"route": {
            "title": route.get("title") or "",
            "description": route.get("description") or "",
            "mapSegmentDescriptions": [str(segment.get("mapSegmentDesc") or "") for segment in route.get("staySegments") or []],
        }}
    for field in spec.editor_fields:
        item = _read_path(document, field.path)
        _write_path(candidate, field.path, item if item is not None else ([] if field.control == "string-list" else ""))
    return candidate


def content_editor_state_payload(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    scopes = [scope for scope, spec in CONTENT_SECTION_REGISTRY.items() if spec.owner == "content"]
    scopes.extend(f"itinerary:day:{day.get('dayNumber')}" for day in ((document.get("itinerary") or {}).get("days") or []) if day.get("dayNumber"))
    return {scope: project_candidate_from_document(document, scope) for scope in scopes}


def content_registry_for_document_payload(document: dict[str, Any]) -> dict[str, dict[str, object]]:
    payload = content_registry_payload()
    for day in ((document.get("itinerary") or {}).get("days") or []):
        if day.get("dayNumber"):
            scope = f"itinerary:day:{day['dayNumber']}"
            payload.update(content_registry_payload(scope))
    return payload
