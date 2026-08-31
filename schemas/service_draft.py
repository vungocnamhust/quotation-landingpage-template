"""``ServiceDraft``/``DayDraftResult`` — ServiceDrafter output (15.7 §1.5).

Zero-Money Invariant: NO field here names an amount/price/currency. The drafter identifies
WHAT to book (a ``product_id`` it saw via a catalog tool this run) and WHY (``selection_reason``)
— never HOW MUCH. Price resolution happens server-side only, via ``core.rules.rate_selection``
(chốt #1/#2). This module is grepped by ``tests/test_draft_run_service.py`` for
``_minor|price|amount`` and must stay empty.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from core.rules.catalog_vocab import CATEGORY, OCCUPANCY_BASIS, PRICE_FOR

DraftFlag = Literal["rate_missing", "rate_conflict", "has_supplement_in_range", "needs_manual"]


class ServiceDraft(BaseModel):
    category: str = Field(description=f"one of {sorted(CATEGORY)}")
    subcategory: str | None = None
    product_id: str = Field(description="must be an id the agent actually saw via a catalog tool this run")
    occupancy_basis: str = Field(default="na", description=f"one of {sorted(OCCUPANCY_BASIS)}")
    price_for: str = Field(default="adult", description=f"one of {sorted(PRICE_FOR)}")
    pax_count: int = Field(ge=1)
    qty_unit: int = Field(default=1, ge=1)
    qty_time: int = Field(default=1, ge=1)
    selection_reason: str = Field(max_length=160)
    flags: list[DraftFlag] = Field(default_factory=list)


class DayDraftResult(BaseModel):
    day_number: int = Field(ge=1)
    services: list[ServiceDraft] = Field(default_factory=list)
    skipped_reasons: list[str] = Field(
        default_factory=list,
        description="Why a day has no drafted services (never silently empty) — e.g. "
        "'no accommodation candidates found for this destination/tier'.",
    )
