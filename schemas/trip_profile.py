"""``TripProfile`` — TripAnalyst output (15.7 §1.5).

Reuses existing vocab (``OCCUPANCY_BASIS``) rather than introducing a new taxonomy (chốt #5).
``special_flags`` are verbatim excerpts from the customer's prose, never the model's own
interpretation — the same "copy, don't compute" discipline as the 15.8 Extractor.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from core.rules.catalog_vocab import OCCUPANCY_BASIS

TripArchetype = Literal[
    "solo",
    "couple",
    "honeymoon",
    "family_with_young_kids",
    "family_with_teens",
    "multi_generation",
    "friends_group",
    "corporate_incentive",
]

Pace = Literal["relaxed", "moderate", "packed"]

MobilityLevel = Literal["full", "limited", "wheelchair"]


class PartyComposition(BaseModel):
    adults: int = Field(ge=1)
    children: int = Field(default=0, ge=0)
    infants: int = Field(default=0, ge=0)
    child_ages: list[int] = Field(default_factory=list)


class RoomAllocation(BaseModel):
    room_type: str = Field(description=f"one of {sorted(OCCUPANCY_BASIS)}")
    count: int = Field(ge=1)
    extra_bed: bool = False
    occupants_note: str | None = Field(default=None, max_length=200)


class TripProfile(BaseModel):
    archetype: TripArchetype
    party: PartyComposition
    room_config: list[RoomAllocation] = Field(default_factory=list)
    mobility: MobilityLevel = "full"
    pace: Pace = "moderate"
    dietary: list[str] = Field(default_factory=list)
    quality_tier: Literal["ultra_luxury", "luxury", "premium", "standard", "value"] = "luxury"
    guide_need: bool = True
    guide_languages: list[str] = Field(default_factory=list)
    special_flags: list[str] = Field(
        default_factory=list,
        description="Verbatim excerpts from customer prose (allergies, mobility notes, "
        "special occasions) — never the model's own paraphrase.",
    )
    confidence_notes: list[str] = Field(
        default_factory=list,
        description="Things the model is NOT sure about — the frontend renders these in red "
        "for the sale to confirm before Draft can run.",
    )
