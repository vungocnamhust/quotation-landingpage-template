"""Server-enforced, path-scoped content writes from the Design canvas.

Plan 16 §C.1 (docs/plans/refactor-tech-stack/16-design-tab-editable-content-audit.md).
This is the sole write path `PATCH /content-values` uses: every mutation's
`source` is checked against the ACL (`editable_brochure_contract.content_write_allowlist`),
resolved against the *persisted* document (never a client-submitted one), and
budget-validated before it is applied. A client cannot widen its own write
surface by fabricating a plausible-looking pointer.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Iterable

from core.rules.content_budgets import get_content_budget_registry
from editable_brochure_contract import MEDIA_SLOT_REGISTRY, content_write_allowlist, is_content_writable_source, resolve_id_keyed_source


class ContentAclDeniedError(ValueError):
    """`source` does not match any content-owned pointer template."""

    def __init__(self, source: str) -> None:
        super().__init__(f"Content source is not writable from the Design canvas: {source!r}")
        self.source = source


class ContentTargetMissingError(ValueError):
    """`source` is content-owned, but its entity no longer exists in the document."""

    def __init__(self, source: str) -> None:
        super().__init__(f"Content target no longer exists: {source!r}")
        self.source = source


class ContentValueBudgetError(ValueError):
    """`value` fails the content budget (length) for its field."""

    def __init__(self, source: str, *, max_chars: int) -> None:
        super().__init__(f"Content value for {source!r} exceeds the {max_chars}-character budget.")
        self.source = source


# Maps a content-owned source template to the field's budget lookup. Static
# (non-entity) fields resolve straight to a (budget_scope, field_key) pair in
# `core/rules/content_budgets.py`; entity fields (itinerary day) share one
# budget scope ("itinerary_day") regardless of which day is being edited.
# Fields with no registered budget spec (pricing, hotel editorial,
# finalization — Plan 16 §B.2 tracks migrating these into the registry) fall
# back to an explicit `max_chars`.
_BUDGET_LOOKUP: dict[str, dict[str, Any]] = {
    "/trip/title": {"budget": ("hero", "trip_title")},
    "/trip/lede": {"budget": ("hero", "trip_lede")},
    "/narrative/coverKicker": {"budget": ("hero", "cover_kicker")},
    "/narrative/heroMeta1": {"budget": ("hero", "hero_meta_1")},
    "/narrative/heroMeta2": {"budget": ("hero", "hero_meta_2")},
    "/narrative/footerText": {"budget": ("hero", "footer_text")},
    "/narrative/journeyOverviewTitle": {"budget": ("overview_letter", "overview_title")},
    "/narrative/letterHighlight": {"budget": ("overview_letter", "letter_highlight")},
    "/narrative/letterGreeting": {"budget": ("overview_letter", "letter_greeting")},
    "/narrative/letterIntro": {"budget": ("overview_letter", "letter_intro")},
    "/narrative/letterBody2": {"budget": ("overview_letter", "letter_body")},
    "/narrative/letterOutro": {"budget": ("overview_letter", "letter_outro")},
    "/narrative/letterSignOff": {"budget": ("overview_letter", "letter_signoff")},
    "/narrative/letterSender": {"budget": ("overview_letter", "letter_sender")},
    "/route/title": {"budget": ("route", "route_title")},
    "/route/description": {"budget": ("route", "route_description")},
    "/route/staySegments/{segmentId}/mapSegmentDesc": {"budget": ("route", "map_segment_descriptions")},
    "/itinerary/title": {"budget": ("itinerary", "itinerary_title")},
    "/itinerary/description": {"budget": ("itinerary", "itinerary_description")},
    "/itinerary/days/{dayId}/title": {"budget": ("itinerary_day", "title")},
    "/itinerary/days/{dayId}/description/0": {"budget": ("itinerary_day", "description")},
    "/itinerary/days/{dayId}/activities": {"budget": ("itinerary_day", "activities")},
    "/pricing/kicker": {"max_chars": 160},
    "/pricing/title": {"max_chars": 160},
    "/pricing/description": {"max_chars": 1600},
    "/stays/hotels/{hotelId}/editorialIntroduction": {"max_chars": 300},
    "/content/sections/finalization/blocks/0/groups/0/items/*": {"max_chars": 1600},
    "/content/sections/finalization/blocks/0/groups/1/items/*": {"max_chars": 1600},
    "/content/sections/finalization/blocks/0/groups/0/title": {"max_chars": 160},
    "/content/sections/finalization/blocks/0/groups/1/title": {"max_chars": 160},
}


def _is_wildcard_segment(segment: str) -> bool:
    # Mirrors `editable_brochure_contract._is_wildcard_segment`: `*` is the v3
    # numeric-index wildcard, `{param}` the v4 id-keyed wildcard (Plan 16 §C.2).
    return segment == "*" or (segment.startswith("{") and segment.endswith("}") and len(segment) > 2)


def _match_template(source: str) -> str | None:
    segments = source.strip("/").split("/")
    for template in content_write_allowlist():
        template_segments = template.strip("/").split("/")
        if len(template_segments) == len(segments) and all(_is_wildcard_segment(t) or t == s for t, s in zip(template_segments, segments)):
            return template
    return None


def _budget_max_chars(template: str) -> int:
    spec = _BUDGET_LOOKUP.get(template)
    if spec is None:
        return 1600
    if "max_chars" in spec:
        return int(spec["max_chars"])
    scope, field_key = spec["budget"]
    return get_content_budget_registry("v1").get_max_chars(scope, field_key, default=1600)


def _value_length(value: str | list[str]) -> int:
    if isinstance(value, list):
        return sum(len(item) for item in value)
    return len(value)


@dataclass(frozen=True)
class ContentValueMutationInput:
    source: str
    value: str | list[str]


@dataclass(frozen=True)
class ContentValueResult:
    document: dict[str, Any]
    updated_sources: tuple[str, ...]
    touched_scopes: tuple[str, ...]


class ContentValueService:
    """Validates and applies Design-canvas content mutations against the persisted document."""

    @staticmethod
    def validate_mutation(mutation: ContentValueMutationInput, document: dict[str, Any]) -> tuple[str, str]:
        """ACL + resolve one mutation against `document`.

        Returns `(normalized_source, scope)`. Raises `ContentAclDeniedError`,
        `ContentTargetMissingError`, or `ContentValueBudgetError`.
        """
        if not is_content_writable_source(mutation.source):
            raise ContentAclDeniedError(mutation.source)
        resolved = resolve_id_keyed_source(mutation.source, document)
        if resolved is None:
            raise ContentTargetMissingError(mutation.source)
        template = _match_template(mutation.source)
        max_chars = _budget_max_chars(template) if template else 1600
        if _value_length(mutation.value) > max_chars:
            raise ContentValueBudgetError(mutation.source, max_chars=max_chars)
        return resolved

    @staticmethod
    def apply(document: dict[str, Any], mutations: Iterable[ContentValueMutationInput]) -> ContentValueResult:
        """Apply validated mutations immutably; returns the merged document plus touched scopes."""
        merged = copy.deepcopy(document)
        updated_sources: list[str] = []
        touched_scopes: list[str] = []
        for mutation in mutations:
            normalized_source, scope = ContentValueService.validate_mutation(mutation, merged)
            _write_pointer(merged, normalized_source, mutation.value)
            updated_sources.append(mutation.source)
            if scope not in touched_scopes:
                touched_scopes.append(scope)
        return ContentValueResult(document=merged, updated_sources=tuple(updated_sources), touched_scopes=tuple(touched_scopes))


def _write_pointer(document: dict[str, Any], source: str, value: Any) -> None:
    segments = source[1:].split("/")
    current: Any = document
    for segment in segments[:-1]:
        if isinstance(current, dict):
            current = current.setdefault(segment, {})
        elif isinstance(current, list) and segment.isdigit() and int(segment) < len(current):
            current = current[int(segment)]
        else:
            raise ContentTargetMissingError(source)
    leaf = segments[-1]
    if isinstance(current, dict):
        current[leaf] = value
    elif isinstance(current, list) and leaf.isdigit() and int(leaf) < len(current):
        current[int(leaf)] = value
    else:
        raise ContentTargetMissingError(source)


class DocumentStructuralDiffError(ValueError):
    """`PUT /document` payload changes a structural (Facts-owned) pointer.

    Plan 16 §B.4/§C.1: `PUT /document` used to persist a client-submitted
    document wholesale; a client bug or direct API call could silently
    rewrite dates, party size, pricing, or itinerary structure. This is the
    defense-in-depth guard — the Design canvas itself now writes content via
    `PATCH /content-values` and never sends a whole-document payload for
    content edits.
    """

    def __init__(self, paths: tuple[str, ...]) -> None:
        super().__init__(f"Document payload changes structural (Facts-owned) fields: {', '.join(paths)}")
        self.paths = paths


# Pointers a whole-document PUT may still legitimately change: Design/content
# copy (the content ACL), presentation overrides, and the registered media
# slots (Facts-owned asset uploads that flow through the Design canvas' full
# save today, per Plan 16 audit item B1). `/meta` and `/brand` are always
# server-recomputed before validation regardless of what the client sends.
# `/layout` keeps its own dedicated Pydantic validation (`ensure_layout_defaults`)
# and is not part of Plan 16's Facts threat model (dates/party/pricing/itinerary/hotels).
_STRUCTURAL_GUARD_EXEMPT_SUBTREES: tuple[str, ...] = ("/presentation", "/meta", "/brand", "/layout")


def _is_under_pointer_prefix(path: str, prefix_template: str) -> bool:
    path_segments = path.strip("/").split("/")
    prefix_segments = prefix_template.strip("/").split("/")
    if len(path_segments) < len(prefix_segments):
        return False
    return all(p == "*" or p == s for p, s in zip(prefix_segments, path_segments[: len(prefix_segments)]))


# `QuoteAssetRef.source`/`resolverVersion` (quote_document.py) are resolver
# bookkeeping stamped onto every asset ref in the document (hero, day images,
# hotel images, dividers, ...) and are recomputed on every hydrate regardless
# of client input. They are never Facts-owned structural data, so a leaf
# named either is exempt everywhere it appears.
_STRUCTURAL_GUARD_EXEMPT_LEAF_NAMES: frozenset[str] = frozenset({"resolverVersion", "source"})


def is_structurally_mutable_pointer(path: str) -> bool:
    """True when `path` is content-owned, presentation-owned, or a registered media slot."""
    if any(path == subtree or path.startswith(subtree + "/") for subtree in _STRUCTURAL_GUARD_EXEMPT_SUBTREES):
        return True
    if path.rsplit("/", 1)[-1] in _STRUCTURAL_GUARD_EXEMPT_LEAF_NAMES:
        return True
    if is_content_writable_source(path):
        return True
    return any(_is_under_pointer_prefix(path, str(slot["source"])) for slot in MEDIA_SLOT_REGISTRY)


def _diff_paths(current: Any, submitted: Any, prefix: str = "") -> list[str]:
    if isinstance(current, dict) and isinstance(submitted, dict):
        paths: list[str] = []
        for key in sorted(set(current) | set(submitted)):
            paths.extend(_diff_paths(current.get(key), submitted.get(key), f"{prefix}/{key}"))
        return paths
    if isinstance(current, list) and isinstance(submitted, list):
        if len(current) != len(submitted):
            return [prefix]
        paths = []
        for index, (current_item, submitted_item) in enumerate(zip(current, submitted)):
            paths.extend(_diff_paths(current_item, submitted_item, f"{prefix}/{index}"))
        return paths
    return [] if current == submitted else [prefix]


def assert_no_structural_diff(current: dict[str, Any], submitted: dict[str, Any]) -> None:
    """Raise `DocumentStructuralDiffError` when `submitted` changes a Facts-owned pointer.

    Compares the canonical (already sanitized/hydrated) `submitted` document
    against the persisted `current` document. Only diffs outside the content
    ACL, presentation overrides, and registered media slots are structural.
    """
    diff_paths = tuple(path for path in _diff_paths(current, submitted) if not is_structurally_mutable_pointer(path))
    if diff_paths:
        raise DocumentStructuralDiffError(diff_paths)
