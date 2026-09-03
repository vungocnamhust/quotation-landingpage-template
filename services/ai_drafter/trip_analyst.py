"""Trip Analyst (15.7 §1.1) — 0-tool agent, prose -> typed ``TripProfile``.

The ONLY layer that ever sees the customer's raw itinerary text (chốt #3). It has zero tools
(the same architectural boundary as the 15.8 Extractor), so untrusted prose has nothing to act
on even if it contains an injection attempt. On agent failure, falls back to a deterministic
``rooming_heuristic_service`` call so Analyze never hard-fails a run (``fallback_used=True``).
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from core.kernel import ActorRef
from schemas.trip_profile import PartyComposition, RoomAllocation, TripProfile
from services.ai_platform.guardrails import RunBudget
from services.ai_platform.runs import record_run
from services.ai_platform.runtime import build_agent, run_agent
from services.rooming_heuristic_service import RoomingHeuristicService

AGENT_NAME = "trip_analyst"
DEFAULT_TENANT_ID = "capella"


class TripAnalysisError(RuntimeError):
    """The Trip Analyst agent failed and the deterministic fallback also could not proceed."""


async def _run_analyst(raw_text: str) -> tuple[TripProfile, object]:
    agent = build_agent(AGENT_NAME, output_type=TripProfile, prompt_file="trip_analyst", tools=())
    result = await run_agent(agent, raw_text)
    return result.output, result.usage


async def _fallback_profile(session: AsyncSession, raw_text: str) -> TripProfile:
    """Deterministic minimum-viable profile from ``rooming_heuristic_service`` — 2 adults is the
    heuristic default when the Analyst fails and nothing else can be safely inferred."""
    heuristic = RoomingHeuristicService(session)
    evaluation = await heuristic.evaluate(adults=2, children=0)
    return TripProfile(
        archetype="couple",
        party=PartyComposition(adults=2, children=0, infants=0, child_ages=[]),
        room_config=[RoomAllocation(room_type="dbl", count=max(1, evaluation.get("min_estimated_rooms", 1)))],
        confidence_notes=[
            "Trip Analyst agent failed — this is a deterministic fallback profile (2 adults, "
            "double room). Please review and correct every field before drafting.",
            f"raw text length was {len(raw_text)} characters; nothing else could be inferred safely.",
        ],
    )


async def analyze_trip(
    session: AsyncSession,
    *,
    raw_text: str,
    anchor_type: str,
    anchor_id: str,
    idempotency_key: str,
    actor: ActorRef,
    tenant_id: str = DEFAULT_TENANT_ID,
) -> tuple[TripProfile, bool]:
    """Returns ``(profile, fallback_used)``. Never raises for a normal LLM failure — it
    degrades to the deterministic fallback and records that in the run log and the profile's
    own ``confidence_notes`` instead."""
    budget = RunBudget(max_calls=0)  # 0-tool by architecture
    fallback_used = False
    status = "succeeded"
    try:
        profile, usage = await _run_analyst(raw_text)
        budget.record_usage(usage)
    except Exception:  # pragma: no cover - network/provider errors
        profile = await _fallback_profile(session, raw_text)
        fallback_used = True
        status = "partial"

    await record_run(
        session,
        agent_name=AGENT_NAME,
        anchor_type=anchor_type,
        anchor_id=anchor_id,
        status=status,
        idempotency_key=idempotency_key,
        input_ref={"raw_text_length": len(raw_text)},
        output={"trip_profile": profile.model_dump(mode="json"), "fallback_used": fallback_used},
        stats=budget.stats(),
        actor=actor,
        tenant_id=tenant_id,
    )
    return profile, fallback_used
