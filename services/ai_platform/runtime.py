"""``build_agent`` — the ONE factory for every ``pydantic_ai.Agent`` in this repo's AI
Platform Layer (15.8 bootstrap §1.1).

Wraps ``llm_client.get_model()`` + a ``prompts/v1/*.yaml`` system prompt + a typed output
model + retries, standardizing the pattern already proven by
``services/section_content_generator.py``. This does not reinvent an agent runtime — it only
removes the boilerplate of repeating that construction per feature. No plugin system, no tool
auto-discovery: callers pass their own explicit tool list.

Ingestion prompts are simpler than the brochure ``PromptLoader`` (no brand/mode/facts_snapshot
composition), so this module reads ``prompts/v1/<name>.yaml`` directly — a flat
``{system_prompt: str}`` document — rather than routing through the brochure-specific loader.
"""
from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache
from typing import Any

import yaml
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.agent import AgentRunResult

import llm_client
from prompts.loader import PROMPTS_DIR

DEFAULT_RETRIES = 2


@lru_cache(maxsize=32)
def _load_prompt_yaml(prompt_file: str) -> dict[str, Any]:
    path = PROMPTS_DIR / "v1" / f"{prompt_file}.yaml"
    if not path.exists():
        raise ValueError(f"AI platform prompt file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        document = yaml.safe_load(handle) or {}
    if "system_prompt" not in document:
        raise ValueError(f"AI platform prompt file '{path}' is missing 'system_prompt'.")
    return document


def load_system_prompt(prompt_file: str) -> str:
    return str(_load_prompt_yaml(prompt_file)["system_prompt"]).strip()


def build_agent(
    name: str,
    *,
    output_type: type[BaseModel],
    prompt_file: str,
    deps_type: type | None = None,
    tools: Sequence[Any] = (),
    retries: int = DEFAULT_RETRIES,
) -> Agent:
    """Build one ``pydantic_ai.Agent`` for an AI Platform feature.

    ``tools`` must be an explicit list (e.g. ``CATALOG_TOOLSET_B``) — there is no
    auto-discovery. An agent with an empty ``tools`` list (the Extractor, 15.8 §0 chốt #2) is
    the architectural 0-tool boundary: it never gets a chance to call anything, so it never
    gets a chance to act on untrusted text as instructions.
    """
    return Agent(
        model=llm_client.get_model(),
        output_type=output_type,
        system_prompt=load_system_prompt(prompt_file),
        deps_type=deps_type or type(None),
        tools=list(tools),
        retries=retries,
        name=name,
    )


async def run_agent(agent: Agent, user_prompt: str, *, deps: Any = None) -> AgentRunResult[Any]:
    """Run ``agent`` with tool-call execution forced sequential.

    pydantic_ai 2.16 defaults to running the multiple tool calls a single model turn can emit
    concurrently (``asyncio.create_task`` per call). Every AI Platform tool reads through
    ``ctx.deps.session`` — one ``AsyncSession`` shared for the whole agent run (and, for the
    drafter, the very session the caller later writes lines with) — and ``AsyncSession``
    forbids concurrent operations. Forcing 'sequential' here is the single choke point that
    keeps every current and future tool-bearing agent safe from that crash/session-poisoning
    class of bug (Track 4 audit C3), including 0-tool agents for which this is a no-op.
    """
    with Agent.parallel_tool_call_execution_mode("sequential"):
        return await agent.run(user_prompt, deps=deps)
