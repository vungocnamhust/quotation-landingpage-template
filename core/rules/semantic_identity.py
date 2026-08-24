"""Pure stable-identity helpers for immutable quotation Facts."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal
from uuid import NAMESPACE_URL, uuid5


EntityOperation = Literal["added", "removed", "reordered", "semantic_replaced", "changed", "unchanged"]


@dataclass(frozen=True)
class FactEntityIdentity:
    """Identity and immutable semantic signature for a Facts entity."""

    source_fact_id: str
    semantic_signature: tuple[str, ...]


@dataclass(frozen=True)
class SemanticEntityChange:
    """A deterministic entity lifecycle result; it has no persistence or I/O."""

    entity_key: str
    operation: EntityOperation
    old_value: dict[str, Any] | None
    new_value: dict[str, Any] | None
    carry_forward_allowed: bool


def itinerary_semantic_signature(day: dict[str, Any]) -> tuple[str, ...]:
    """Fields whose change makes inherited itinerary narrative unsafe."""
    return (
        str(day.get("destination_ref") or day.get("destination") or "").strip(),
        str(day.get("overnight") or "").strip(),
    )


def hotel_semantic_signature(hotel: dict[str, Any]) -> tuple[str, ...]:
    return (
        str(hotel.get("accommodation_id") or hotel.get("name") or "").strip(),
        str(hotel.get("destination") or "").strip(),
    )


def assign_missing_source_fact_ids(
    entities: list[dict[str, Any]],
    *,
    creation_namespace: str,
    kind: Literal["itinerary_day", "hotel"],
) -> list[dict[str, Any]]:
    """Return a copied Facts list with permanent IDs for first persistence.

    The caller must persist this output as the first immutable snapshot.  The
    fallback seed is intentionally used only when an entity does not have an
    ID; later successor creation must preserve the persisted ID verbatim.
    """
    assigned: list[dict[str, Any]] = []
    for position, entity in enumerate(entities, 1):
        item = deepcopy(entity)
        if not item.get("id"):
            item["id"] = f"{kind}_{uuid5(NAMESPACE_URL, f'{creation_namespace}:{kind}:{position}').hex}"
        assigned.append(item)
    return assigned
