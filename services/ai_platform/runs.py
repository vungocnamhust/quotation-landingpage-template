"""``AiRun`` lifecycle helpers (15.8 bootstrap §1.3) — append-only run log for every agent call.

There is no separate repository module for ``ai_runs``: this file is the only writer, by
design (mirrors the "commit_service is the only catalog writer" isolation used elsewhere in
15.8). Rows are never updated after insert.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.kernel import ActorRef, generate_id
from db.models.ai_run import AiRun

ID_PREFIX = "air"
DEFAULT_TENANT_ID = "capella"

_VALID_STATUSES = frozenset({"succeeded", "partial", "failed"})


async def record_run(
    session: AsyncSession,
    *,
    agent_name: str,
    anchor_type: str,
    anchor_id: str,
    status: str,
    idempotency_key: str,
    input_ref: dict[str, Any],
    output: dict[str, Any],
    stats: dict[str, Any],
    actor: ActorRef,
    tenant_id: str = DEFAULT_TENANT_ID,
) -> AiRun:
    """Insert one append-only ``ai_runs`` row for a completed agent call."""
    if status not in _VALID_STATUSES:
        raise ValueError(f"invalid AiRun status '{status}'")
    run = AiRun(
        id=generate_id(ID_PREFIX),
        tenant_id=tenant_id,
        agent_name=agent_name,
        anchor_type=anchor_type,
        anchor_id=anchor_id,
        status=status,
        idempotency_key=idempotency_key,
        input_ref_json=input_ref,
        output_json=output,
        stats_json=stats,
        created_by=actor.serialize(),
        updated_by=actor.serialize(),
    )
    session.add(run)
    await session.flush()
    return run
