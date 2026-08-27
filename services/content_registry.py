"""Single ownership, editing, and generation-brief contract for Content Studio."""
from __future__ import annotations

import copy
from dataclasses import dataclass, replace
from typing import Any, Callable, Literal


Owner = Literal["fact", "fact-derived", "content", "design"]
EditorControl = Literal["input", "textarea", "string-list"]
ContentAutomationPolicy = Literal["manual", "auto", "bypass"]
FactDependencyRole = Literal["semantic_identity", "content_input", "derived_context"]
ImpactPolicy = Literal["invalidate_content", "review_or_generate", "preserve_content_rebuild_labels"]


@dataclass(frozen=True)
class FactDependency:
    """Executable fact_used contract shared by generation and Impact Analysis."""

    path: str
    role: FactDependencyRole
    impact_policy: ImpactPolicy
    target_paths: tuple[str, ...]
    deep_link: str
    entity_binding: Literal["quotation", "itinerary_day"] = "quotation"


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
    fact_used: tuple[FactDependency, ...] = ()
    # New Actionable Content Plan contract. `fact_used` remains a temporary
    # compatibility adapter until the old Impact API is removed in Sprint 3.
    automation_policy: ContentAutomationPolicy = "manual"
    entity_binding: Literal["quotation", "itinerary_day", "hotel"] = "quotation"
    prompt_context_builder: Callable[[Any, str, dict[str, Any] | None], dict[str, Any]] | None = None


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


def _read_fact_path(payload: Any, path: str) -> Any:
    value: Any = payload
    for part in path.split("."):
        value = getattr(value, part, None)
        if value is None:
            return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, list):
        return [item.model_dump(mode="json", exclude_none=True) if hasattr(item, "model_dump") else item for item in value]
    return value


def _default_prompt_context(payload: Any, scope: str, request_brief: dict[str, Any] | None) -> dict[str, Any]:
    spec = scope_spec(scope)
    if scope.startswith("itinerary:day:"):
        token = scope.rsplit(":", 1)[-1]
        day = next((item for item in payload.trip_facts.itinerary if str(item.id or item.day_number) == token), None)
        context = {"itineraryDay": {
            "sourceFactId": day.id if day else token,
            "dayNumber": day.day_number if day else None,
            "destination": day.destination if day else "",
            "summary": day.summary if day else "",
            "highlights": list(day.highlights) if day else [],
            "meals": list(day.meals) if day else [],
            "overnight": day.overnight if day else "",
        }}
    else:
        context = {"facts": {path: _read_fact_path(payload, path) for path in spec.fact_allowlist}}
    if request_brief:
        context["request_brief"] = copy.deepcopy(request_brief)
    return context


def build_prompt_context(payload: Any, scope: str, request_brief: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return the sole Facts snapshot contract used by Content generation."""
    spec = scope_spec(scope)
    builder = spec.prompt_context_builder or _default_prompt_context
    return builder(payload, scope, request_brief)



CONTENT_SECTION_REGISTRY: dict[str, ContentSectionSpec] = {
    "hero": ContentSectionSpec(
        "hero", "content", ("trip.title", "trip.lede", "narrative.coverKicker", "narrative.heroMeta1", "narrative.heroMeta2", "narrative.footerText"),
        ("trip_facts.destinations", "trip_facts.start_date", "trip_facts.end_date", "trip_facts.duration_days", "trip_facts.duration_nights", "customer_facts.customer_name", "customer_facts.adults", "customer_facts.children", "customer_facts.kid_ages", "brand_id", "lang"),
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
        default_instructions=_brief("hero"), automation_policy="bypass",
    ),
    "overview_letter": ContentSectionSpec(
        "overview_letter", "content", ("narrative.journeyOverviewTitle", "narrative.letterHighlight", "narrative.letterGreeting", "narrative.letterIntro", "narrative.letterBody2", "narrative.letterOutro", "narrative.letterSignOff", "narrative.letterSender"),
        ("trip_facts.destinations", "trip_facts.start_date", "trip_facts.end_date", "trip_facts.duration_days", "trip_facts.duration_nights", "customer_facts.customer_name", "customer_facts.adults", "customer_facts.children", "customer_facts.kid_ages", "customer_facts.advisor_name", "customer_facts.advisor_agency", "brand_id", "lang"),
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
        default_instructions=_brief("overview_letter"), automation_policy="bypass",
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
        default_instructions=_brief("route"), automation_policy="bypass",
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
        default_instructions=_brief("itinerary"), automation_policy="bypass",
    ),
    # The authoritative values remain Facts. These scopes become manual
    # editorial hand-offs in Sprint 4; they are not LLM-writable yet.
    "hotel_plan": ContentSectionSpec("hotel_plan", "content", ("stays.hotels.*.editorialIntroduction", "stays.roomNotes"), ("service_facts.hotels",), ("service_facts.hotels",), "narrative", automation_policy="manual"),
    "pricing": ContentSectionSpec("pricing", "content", ("pricing.kicker", "pricing.title", "pricing.description", "pricing.ctaLabel"), ("pricing_facts.options", "pricing_facts.conditions"), ("pricing_facts.options",), "narrative", automation_policy="manual"),
    "inclusions_exclusions": ContentSectionSpec("inclusions_exclusions", "content", ("content.sections.inclusions_exclusions",), ("service_facts.inclusions", "service_facts.exclusions"), ("service_facts.inclusions", "service_facts.exclusions"), "narrative", ("twoColumnList",), automation_policy="manual"),
    "booking_terms": ContentSectionSpec("booking_terms", "fact", ("content.sections.booking_terms",), ("booking_facts",), ("booking_facts",), "fact-preview", ("paragraph", "termList", "paymentSchedule")),
    "designer": ContentSectionSpec("designer", "fact", ("designer",), ("designer_facts",), ("designer_facts",), "fact-preview"),
}


_CONTENT_FACT_USED: dict[str, tuple[FactDependency, ...]] = {
    "hero": (
        FactDependency("trip_facts.destinations", "content_input", "review_or_generate", ("trip.title", "trip.lede", "narrative.coverKicker"), "content:hero"),
        FactDependency("trip_facts.start_date", "derived_context", "preserve_content_rebuild_labels", ("narrative.heroMeta1",), "content:hero"),
        FactDependency("trip_facts.end_date", "derived_context", "preserve_content_rebuild_labels", ("narrative.heroMeta1",), "content:hero"),
        FactDependency("customer_facts.adults", "content_input", "review_or_generate", ("narrative.heroMeta2",), "content:hero"),
        FactDependency("customer_facts.children", "content_input", "review_or_generate", ("narrative.heroMeta2",), "content:hero"),
        FactDependency("customer_facts.kid_ages", "content_input", "review_or_generate", ("narrative.heroMeta2",), "content:hero"),
        FactDependency("brand_id", "content_input", "review_or_generate", ("trip.title", "trip.lede"), "content:hero"),
        FactDependency("lang", "content_input", "review_or_generate", ("trip.title", "trip.lede"), "content:hero"),
    ),
    "overview_letter": (
        FactDependency("trip_facts.destinations", "content_input", "review_or_generate", ("narrative.journeyOverviewTitle", "narrative.letterIntro"), "content:overview_letter"),
        FactDependency("customer_facts.adults", "content_input", "review_or_generate", ("narrative.letterGreeting",), "content:overview_letter"),
        FactDependency("customer_facts.children", "content_input", "review_or_generate", ("narrative.letterGreeting",), "content:overview_letter"),
        FactDependency("customer_facts.kid_ages", "content_input", "review_or_generate", ("narrative.letterIntro",), "content:overview_letter"),
        FactDependency("customer_facts.advisor_name", "content_input", "review_or_generate", ("narrative.letterSender", "narrative.letterSignOff"), "content:overview_letter"),
        FactDependency("customer_facts.advisor_agency", "content_input", "review_or_generate", ("narrative.letterSender",), "content:overview_letter"),
        FactDependency("brand_id", "content_input", "review_or_generate", ("narrative.journeyOverviewTitle",), "content:overview_letter"),
        FactDependency("lang", "content_input", "review_or_generate", ("narrative.journeyOverviewTitle", "narrative.letterIntro"), "content:overview_letter"),
    ),
    "route": (
        FactDependency("trip_facts.itinerary", "content_input", "review_or_generate", ("route.title", "route.description", "route.staySegments.*.mapSegmentDesc"), "content:route"),
        FactDependency("lang", "content_input", "review_or_generate", ("route.title", "route.description"), "content:route"),
    ),
    "itinerary": (
        FactDependency("trip_facts.itinerary", "content_input", "review_or_generate", ("itinerary.title", "itinerary.description"), "content:itinerary"),
        FactDependency("lang", "content_input", "review_or_generate", ("itinerary.title", "itinerary.description"), "content:itinerary"),
    ),
}

for _scope, _spec in tuple(CONTENT_SECTION_REGISTRY.items()):
    CONTENT_SECTION_REGISTRY[_scope] = replace(
        _spec,
        fact_used=_CONTENT_FACT_USED.get(_scope, ()),
    )


ITINERARY_DAY_CANONICAL_TARGETS: tuple[str, ...] = (
    "itinerary.days.*.title",
    "itinerary.days.*.description",
    "itinerary.days.*.activities",
)


def content_owned_targets() -> tuple[str, ...]:
    registry_targets = [target for spec in CONTENT_SECTION_REGISTRY.values() if spec.owner == "content" for target in spec.canonical_targets]
    return tuple(registry_targets + list(ITINERARY_DAY_CANONICAL_TARGETS))



def scope_spec(scope: str) -> ContentSectionSpec:
    if scope.startswith("itinerary:day:"):
        entity_key = scope.rsplit(":", 1)[-1]
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
            fact_used=(
                FactDependency("trip_facts.itinerary[].destination", "semantic_identity", "invalidate_content", ("itinerary.days.*.title", "itinerary.days.*.description", "itinerary.days.*.activities"), f"content:{scope}", "itinerary_day"),
                FactDependency("trip_facts.itinerary[].overnight", "semantic_identity", "invalidate_content", ("itinerary.days.*.title", "itinerary.days.*.description", "itinerary.days.*.activities"), f"content:{scope}", "itinerary_day"),
                FactDependency("trip_facts.itinerary[].summary", "content_input", "review_or_generate", ("itinerary.days.*.description",), f"content:{scope}", "itinerary_day"),
                FactDependency("trip_facts.itinerary[].highlights", "content_input", "review_or_generate", ("itinerary.days.*.activities",), f"content:{scope}", "itinerary_day"),
                FactDependency("trip_facts.itinerary[].display_date", "derived_context", "preserve_content_rebuild_labels", (), f"content:{scope}", "itinerary_day"),
            ),
            automation_policy="bypass",
            entity_binding="itinerary_day",
        )

    try:
        return CONTENT_SECTION_REGISTRY[scope]
    except KeyError as exc:
        raise ValueError(f"Unsupported content scope: {scope}") from exc


def content_registry_payload(scope: str | None = None) -> dict[str, dict[str, object]]:
    specs = {scope: scope_spec(scope)} if scope else CONTENT_SECTION_REGISTRY
    return {key: {"owner": spec.owner, "generation": spec.generation, "automationPolicy": spec.automation_policy, "editor": spec.editor, "recipeVersion": spec.recipe_version, "schemaVersion": spec.schema_version, "fields": [field.public_payload() for field in spec.editor_fields], "factInputs": [field.public_payload() for field in spec.fact_inputs], "defaultInstructions": spec.default_instructions.public_payload() if spec.default_instructions else None} for key, spec in specs.items()}


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
    candidate: dict[str, Any] = {}
    if scope.startswith("itinerary:day:"):
        source_fact_id = scope.rsplit(":", 1)[-1]
        day = next((item for item in ((document.get("itinerary") or {}).get("days") or []) if str(item.get("sourceFactId") or item.get("dayNumber")) == source_fact_id), None)
        if day is None:
            raise ValueError("Itinerary day no longer exists.")
        candidate["dayNumber"] = day.get("dayNumber")
        candidate["sourceFactId"] = source_fact_id
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
    scopes.extend(f"itinerary:day:{day.get('sourceFactId') or day.get('dayNumber')}" for day in ((document.get("itinerary") or {}).get("days") or []) if day.get("sourceFactId") or day.get("dayNumber"))
    return {scope: project_candidate_from_document(document, scope) for scope in scopes}


def content_registry_for_document_payload(document: dict[str, Any]) -> dict[str, dict[str, object]]:
    payload = content_registry_payload()
    for day in ((document.get("itinerary") or {}).get("days") or []):
        if day.get("sourceFactId") or day.get("dayNumber"):
            scope = f"itinerary:day:{day.get('sourceFactId') or day.get('dayNumber')}"
            payload.update(content_registry_payload(scope))
    return payload
