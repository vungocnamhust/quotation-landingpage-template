"""Service Drafter (15.7 §1.1) — tool-using, one agent call per day, against toolset group A.

Never sees the customer's raw prose (chốt #3) — only a structured ``DayContext`` derived from
an already sale-reviewed ``TripProfile``. Every ``product_id`` it proposes must have been seen
via a catalog tool this run (``AllowlistRecorder``); the caller (``draft_run_service``) is the
one that independently re-resolves price server-side (chốt #1/#2) — this module never trusts
its own ``tariff_id``/``price_line_id`` hints for anything beyond a search hint.
"""
from __future__ import annotations

from pydantic import BaseModel

from schemas.service_draft import DayDraftResult
from schemas.trip_profile import RoomAllocation, TripProfile
from services.ai_platform.deps import CatalogReadOnlyDeps
from services.ai_platform.runtime import build_agent, run_agent
from services.ai_platform.toolsets.catalog import CATALOG_TOOLSET_A

AGENT_NAME = "service_drafter"


class DayContext(BaseModel):
    day_number: int
    destination_id: str
    service_date: str
    quality_tier: str
    pace: str
    mobility: str
    dietary: list[str]
    room_config: list[RoomAllocation]
    adults: int
    children: int
    guide_need: bool
    guide_languages: list[str]
    special_flags: list[str]


def build_day_context(trip_profile: TripProfile, *, day_number: int, destination_id: str, service_date: str) -> DayContext:
    return DayContext(
        day_number=day_number,
        destination_id=destination_id,
        service_date=service_date,
        quality_tier=trip_profile.quality_tier,
        pace=trip_profile.pace,
        mobility=trip_profile.mobility,
        dietary=trip_profile.dietary,
        room_config=trip_profile.room_config,
        adults=trip_profile.party.adults,
        children=trip_profile.party.children,
        guide_need=trip_profile.guide_need,
        guide_languages=trip_profile.guide_languages,
        special_flags=trip_profile.special_flags,
    )


async def draft_day(deps: CatalogReadOnlyDeps, day_context: DayContext) -> DayDraftResult:
    """Run the Service Drafter agent for one day. Raises on a hard agent/provider failure —
    the caller (``draft_run_service``) catches this per day so one bad day cannot sink the
    whole run (§3 partial-run requirement)."""
    agent = build_agent(
        AGENT_NAME,
        output_type=DayDraftResult,
        prompt_file="service_drafter",
        deps_type=CatalogReadOnlyDeps,
        tools=CATALOG_TOOLSET_A,
    )
    result = await run_agent(agent, day_context.model_dump_json(), deps=deps)
    deps.budget.record_usage(result.usage)
    return result.output
