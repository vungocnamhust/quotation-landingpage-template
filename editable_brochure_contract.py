"""Versioned editable brochure contract shared by API, workspace and renderer tests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CONTRACT_PATH = Path(__file__).with_name("editable-brochure-contract.json")
EDITABLE_BROCHURE_CONTRACT: dict[str, Any] = json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))

_OWNERS = frozenset({"design", "content", "fact", "fact-derived", "system"})
_HANDOFF_OWNERS = frozenset({"content", "fact", "fact-derived"})
_HANDOFF_STAGES = frozenset({"facts", "content"})
_HANDOFF_ITEMS = frozenset({"day", "hotel", "pricingOption", "bookingTerm", "routeSegment"})
_HANDOFF_KEYS = frozenset({"stage", "section", "anchor", "item", "indexFromSource"})
_EDITOR_SURFACES = frozenset({"design-inspector"})


def _source_segments(source: str) -> tuple[str, ...]:
    if not source.startswith("/") or source == "/":
        raise ValueError(f"Editable contract source must be a non-root JSON pointer: {source!r}")
    segments = tuple(source[1:].split("/"))
    if any(not segment or ("*" in segment and segment != "*") for segment in segments):
        raise ValueError(f"Editable contract source has invalid wildcard syntax: {source!r}")
    return segments


def _is_wildcard_segment(segment: str) -> bool:
    # `*` is today's index wildcard; `{param}` is the id-keyed wildcard the
    # contract migrates to in v4 (Plan 16 C.2). Both mean "matches anything"
    # when checking whether two source templates address the same slot.
    return segment == "*" or (segment.startswith("{") and segment.endswith("}") and len(segment) > 2)


def _source_templates_intersect(left: str, right: str) -> bool:
    left_segments, right_segments = _source_segments(left), _source_segments(right)
    return (
        len(left_segments) == len(right_segments)
        and all(a == b or _is_wildcard_segment(a) or _is_wildcard_segment(b) for a, b in zip(left_segments, right_segments))
    )


def _normalized_handoff(field_id: str, owner: str, source_segments: tuple[str, ...], handoff: Any) -> dict[str, Any]:
    if not isinstance(handoff, dict):
        raise ValueError(f"Editable contract field {field_id} requires an explicit valid handoff.")
    unknown_keys = set(handoff) - _HANDOFF_KEYS
    if unknown_keys:
        raise ValueError(f"Editable contract field {field_id} has unsupported handoff keys: {sorted(unknown_keys)!r}")

    stage = handoff.get("stage")
    section = handoff.get("section")
    if stage not in _HANDOFF_STAGES or not isinstance(section, str) or not section.strip():
        raise ValueError(f"Editable contract field {field_id} requires an explicit valid handoff.")
    if owner == "content" and stage != "content":
        raise ValueError(f"Content field {field_id} must hand off to Content.")
    if owner in {"fact", "fact-derived"} and stage != "facts":
        raise ValueError(f"Fact field {field_id} must hand off to Facts.")

    anchor = handoff.get("anchor")
    if anchor is not None and (not isinstance(anchor, str) or not anchor.strip()):
        raise ValueError(f"Editable contract field {field_id} has an invalid handoff anchor.")
    item = handoff.get("item")
    if item is not None and item not in _HANDOFF_ITEMS:
        raise ValueError(f"Editable contract field {field_id} has an invalid handoff item.")
    index_from_source = handoff.get("indexFromSource")
    if index_from_source is not None:
        if isinstance(index_from_source, bool) or not isinstance(index_from_source, int) or index_from_source < 0 or index_from_source >= len(source_segments) or not _is_wildcard_segment(source_segments[index_from_source]):
            raise ValueError(f"Editable contract field {field_id} has an invalid wildcard index resolver.")
        if item is None:
            raise ValueError(f"Editable contract field {field_id} cannot resolve a wildcard without a handoff item.")
    if item is not None and any(_is_wildcard_segment(segment) for segment in source_segments) and index_from_source is None:
        raise ValueError(f"Editable contract field {field_id} requires a wildcard index resolver for its handoff item.")
    return dict(handoff)


def _normalized_fields(contract: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    handoffs = contract.get("handoffs")
    if not isinstance(handoffs, dict):
        raise ValueError("Editable contract must declare its explicit handoff registry.")
    normalized: list[dict[str, Any]] = []
    field_ids: set[str] = set()
    sources: list[tuple[str, str]] = []
    for raw_field in contract.get("fields", []):
        field = dict(raw_field)
        field_id, owner, source = field.get("fieldId"), field.get("owner"), field.get("source")
        if not isinstance(field_id, str) or not field_id or field_id in field_ids:
            raise ValueError(f"Editable contract field IDs must be unique: {field_id!r}")
        if owner not in _OWNERS:
            raise ValueError(f"Editable contract field {field_id} has unsupported owner: {owner!r}")
        if not isinstance(source, str):
            raise ValueError(f"Editable contract field {field_id} must declare one canonical source.")
        segments = _source_segments(source)
        editor_surface = field.get("editorSurface")
        if editor_surface is not None:
            if editor_surface not in _EDITOR_SURFACES or owner != "fact" or field.get("kind") not in {"text", "richText"}:
                raise ValueError(f"Editable contract field {field_id} has an invalid editor surface.")
        handoff = handoffs.get(field_id)
        if owner in _HANDOFF_OWNERS:
            field["handoff"] = _normalized_handoff(field_id, owner, segments, handoff)
            # These are still Fact-owned (and retain their canonical Facts
            # handoff), but the Design Canvas owns the interaction surface.
            # Advertising them as a generic handoff makes the client render a
            # non-editable inspector even though a safe, revision-locked Fact
            # write is available there.
            field["editMode"] = "inspector" if editor_surface == "design-inspector" else "handoff"
        elif owner == "design":
            if handoff is not None:
                raise ValueError(f"Design field {field_id} cannot declare a handoff.")
            field["editMode"] = "inspector"
        else:
            if handoff is not None:
                raise ValueError(f"System field {field_id} cannot declare a handoff.")
            field["editMode"] = "readonly"
        conflicting_field_id = next(
            (existing_field_id for existing_source, existing_field_id in sources if _source_templates_intersect(source, existing_source)),
            None,
        )
        if conflicting_field_id is not None:
            raise ValueError(
                f"Editable contract source overlaps descriptor {conflicting_field_id!r}: {source!r}"
            )
        sources.append((source, field_id))
        field_ids.add(field_id)
        normalized.append(field)
    unknown_handoffs = set(handoffs) - field_ids
    if unknown_handoffs:
        raise ValueError(f"Editable contract contains handoffs without a descriptor: {sorted(unknown_handoffs)!r}")
    return tuple(normalized)


EDITABLE_BROCHURE_FIELDS: tuple[dict[str, Any], ...] = _normalized_fields(EDITABLE_BROCHURE_CONTRACT)
MEDIA_SLOT_REGISTRY: tuple[dict[str, Any], ...] = tuple(EDITABLE_BROCHURE_CONTRACT.get("mediaSlotRegistry", []))


def editable_contract_payload() -> dict[str, Any]:
    # Descriptors are derived from the versioned registry, never from the DOM.
    # The workspace consumes these fields to decide whether an element can be
    # edited locally or must hand off to its canonical owner.
    fields = []
    for field in EDITABLE_BROCHURE_FIELDS:
        descriptor = dict(field)
        owner = str(descriptor["owner"])
        control_kind = "none"
        if owner == "design" or descriptor.get("editorSurface") == "design-inspector":
            control_kind = {"text": "text", "richText": "textarea", "aria": "text", "altText": "text"}.get(str(descriptor["kind"]), "none")
        descriptor.update({
            "inspectorControl": control_kind,
        })
        handoff = descriptor.get("handoff")
        if isinstance(handoff, dict):
            descriptor["handoffStage"] = handoff["stage"]
            descriptor["handoffSection"] = handoff["section"]
        fields.append(descriptor)
    return {**EDITABLE_BROCHURE_CONTRACT, "fields": fields}


def is_design_copy_field(field_id: str) -> bool:
    return any(field["fieldId"] == field_id and field["owner"] == "design" and field["kind"] in {"text", "richText", "aria", "altText"} for field in EDITABLE_BROCHURE_FIELDS)


def design_identity_field(field_id: str) -> dict[str, Any] | None:
    """Return the registry descriptor that owns an identity override."""
    source = f"/presentation/identityOverrides/{field_id}"
    return next((field for field in EDITABLE_BROCHURE_FIELDS if field["owner"] == "design" and field.get("source") == source), None)


def is_design_media_field(field_id: str) -> bool:
    if any(field["fieldId"] == field_id and field["owner"] == "design" and field["kind"] in {"image", "gallery"} for field in EDITABLE_BROCHURE_FIELDS):
        return True
    for field in EDITABLE_BROCHURE_FIELDS:
        template = field["fieldId"]
        if field["owner"] == "design" and field["kind"] in {"image", "gallery"} and "*" in template:
            prefix, suffix = template.split("*", 1)
            if field_id.startswith(prefix) and field_id.endswith(suffix):
                return True
    return False


def is_fact_media_field(field_id: str) -> bool:
    for field in EDITABLE_BROCHURE_FIELDS:
        if field["owner"] != "fact" or field["kind"] not in {"image", "gallery"}:
            continue
        template = field["fieldId"]
        if field_id == template or ("*" in template and field_id.startswith(template.split("*", 1)[0]) and field_id.endswith(template.split("*", 1)[1])):
            return True
    return False


def is_gallery_field(field_id: str) -> bool:
    return any(
        field["kind"] == "gallery"
        and (field_id == field["fieldId"] or ("*" in field["fieldId"] and field_id.startswith(field["fieldId"].split("*", 1)[0]) and field_id.endswith(field["fieldId"].split("*", 1)[1])))
        for field in EDITABLE_BROCHURE_FIELDS
    )


def media_slot_descriptor(field_id: str) -> dict[str, Any] | None:
    for descriptor in MEDIA_SLOT_REGISTRY:
        template = str(descriptor["fieldTemplate"])
        if field_id == template or ("*" in template and field_id.startswith(template.split("*", 1)[0]) and field_id.endswith(template.split("*", 1)[1])):
            return descriptor
    return None


def content_write_allowlist() -> tuple[str, ...]:
    """Source templates the Design canvas may PATCH (owner == 'content').

    This is the server-side ACL for `PATCH /content-values` (Plan 16 §C.1):
    any mutation whose `source` does not template-match one of these pointers
    is rejected, regardless of what a client believes it is allowed to edit.
    """
    return tuple(field["source"] for field in EDITABLE_BROCHURE_FIELDS if field["owner"] == "content")


# Entity-array content sources are addressed by the item's position today
# (numeric index, contract v3) and will migrate to a stable id (contract v4,
# Plan 16 §C.2). `resolve_id_keyed_source` accepts either shape already so
# the migration is additive: it resolves the segment against `document` by
# id first, falling back to treating it as a numeric index.
_ID_KEYED_ENTITY_SOURCES: dict[tuple[str, str], dict[str, Any]] = {
    ("itinerary", "days"): {
        "id_keys": ("sourceFactId", "id"),
        "index_key": "dayNumber",
        "scope": lambda entity: f"itinerary:day:{entity.get('sourceFactId') or entity.get('dayNumber')}",
    },
    ("stays", "hotels"): {
        "id_keys": ("sourceFactId", "id"),
        "index_key": None,
        "scope": lambda entity: "hotel_plan",
    },
    ("route", "staySegments"): {
        "id_keys": ("id", "segmentId"),
        "index_key": None,
        "scope": lambda entity: "route",
    },
}

# Content sources that address a single scalar/list slot (no entity array to
# resolve). Maps the literal JSON pointer to its Content Studio scope.
_STATIC_CONTENT_SCOPES: dict[str, str] = {
    "/trip/title": "hero",
    "/trip/lede": "hero",
    "/narrative/coverKicker": "hero",
    "/narrative/heroMeta1": "hero",
    "/narrative/heroMeta2": "hero",
    "/narrative/footerText": "hero",
    "/narrative/journeyOverviewTitle": "overview_letter",
    "/narrative/letterHighlight": "overview_letter",
    "/narrative/letterGreeting": "overview_letter",
    "/narrative/letterIntro": "overview_letter",
    "/narrative/letterBody2": "overview_letter",
    "/narrative/letterOutro": "overview_letter",
    "/narrative/letterSignOff": "overview_letter",
    "/narrative/letterSender": "overview_letter",
    "/route/title": "route",
    "/route/description": "route",
    "/itinerary/title": "itinerary",
    "/itinerary/description": "itinerary",
    "/pricing/kicker": "pricing",
    "/pricing/title": "pricing",
    "/pricing/description": "pricing",
    "/content/sections/finalization/blocks/0/groups/0/items/*": "finalization",
    "/content/sections/finalization/blocks/0/groups/1/items/*": "finalization",
    "/content/sections/finalization/blocks/0/groups/0/title": "finalization",
    "/content/sections/finalization/blocks/0/groups/1/title": "finalization",
}


def _match_content_template(source: str) -> str | None:
    """Return the `content_write_allowlist()` template matching `source`, or None.

    A template segment matches literally, or as a wildcard (`*`, the v3
    numeric-index contract, or `{param}`, the v4 id-keyed contract — Plan 16
    §C.2). Both contract shapes are accepted during the migration.
    """
    try:
        segments = _source_segments(source)
    except ValueError:
        return None
    for template in content_write_allowlist():
        template_segments = _source_segments(template)
        if len(template_segments) != len(segments):
            continue
        if all(_is_wildcard_segment(t) or t == s for t, s in zip(template_segments, segments)):
            return template
    return None


def is_content_writable_source(source: str) -> bool:
    """True when `source` matches a content-owned source template."""
    return _match_content_template(source) is not None


def _resolve_entity_index(items: list[Any], token: str, *, id_keys: tuple[str, ...], index_key: str | None) -> int | None:
    for index, item in enumerate(items):
        if isinstance(item, dict) and any(str(item.get(key) or "") == token for key in id_keys):
            return index
    if token.isdigit():
        numeric = int(token)
        if 0 <= numeric < len(items):
            return numeric
        if index_key is not None:
            for index, item in enumerate(items):
                if isinstance(item, dict) and item.get(index_key) == numeric:
                    return index
    return None


def resolve_id_keyed_source(source: str, document: dict[str, Any]) -> tuple[str, str] | None:
    """Resolve a content-owned source pointer against `document`.

    Returns `(normalized_source, scope)` where `normalized_source` rewrites
    any entity-array segment to that entity's current numeric index in
    `document`, and `scope` is the Content Studio scope owning the field.
    Returns `None` when `source` is not content-owned, or when it addresses
    an entity (day/hotel/route segment) that no longer exists.
    """
    template = _match_content_template(source)
    if template is None:
        return None
    segments = list(_source_segments(source))
    template_segments = _source_segments(template)

    for (root, child), spec in _ID_KEYED_ENTITY_SOURCES.items():
        if template_segments[:2] != (root, child):
            continue
        items = ((document.get(root) or {}).get(child) or [])
        token = segments[2]
        index = _resolve_entity_index(items, token, id_keys=spec["id_keys"], index_key=spec["index_key"])
        if index is None:
            return None
        segments[2] = str(index)
        scope = spec["scope"](items[index])
        return "/" + "/".join(segments), scope

    scope = _STATIC_CONTENT_SCOPES.get(template)
    if scope is None:
        return None
    return source, scope


def expand_media_slot_field_ids(document: dict[str, Any]) -> tuple[str, ...]:
    """Expand only the registry's declared wildcard slots for this document."""
    fields: list[str] = []
    for descriptor in MEDIA_SLOT_REGISTRY:
        template = str(descriptor["fieldTemplate"])
        if "*" not in template:
            fields.append(template)
        elif template.startswith("itinerary.days."):
            fields.extend(template.replace("*", str(index)) for index, _ in enumerate(((document.get("itinerary") or {}).get("days") or [])))
        elif template.startswith("stays.hotels."):
            fields.extend(template.replace("*", str(index)) for index, _ in enumerate(((document.get("stays") or {}).get("hotels") or [])))
        else:
            fields.extend(template.replace("*", str(key)) for key in descriptor.get("keys", []))
    return tuple(fields)
