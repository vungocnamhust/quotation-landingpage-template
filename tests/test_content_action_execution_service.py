import asyncio

import pytest

from services.content_action_execution_service import ContentActionExecutionService, ExecuteContentActionsCommand


def _command(*ids: str) -> ExecuteContentActionsCommand:
    return ExecuteContentActionsCommand("quo_1", "plan_1", ids, 4, "storytelling", "idem", "corr")


def test_auto_persists_only_after_every_candidate_is_valid() -> None:
    persisted = []

    async def generate(action, style):
        if action["id"] == "b":
            raise RuntimeError("provider failure")
        return {"value": action["id"]}

    async def persist(candidates):
        persisted.extend(candidates)
        return {candidate.action_id: f"draft_{candidate.action_id}" for candidate in candidates}

    async def apply(candidates, revision):
        raise AssertionError("auto must not apply")

    with pytest.raises(RuntimeError):
        asyncio.run(ContentActionExecutionService().execute(
            command=_command("a", "b"), policy="auto",
            actions=[{"id": "a", "scope": "hero", "automation_policy": "auto"}, {"id": "b", "scope": "route", "automation_policy": "auto"}],
            generate=generate, validate=lambda scope, candidate: candidate, persist_drafts=persist, apply_atomically=apply,
        ))
    assert persisted == []


def test_bypass_applies_once_after_all_generation_succeeds() -> None:
    calls = []

    async def generate(action, style):
        return {"scope": action["scope"]}

    async def persist(candidates):
        raise AssertionError("bypass must not create review drafts")

    async def apply(candidates, revision):
        calls.append((candidates, revision))
        return 5

    generated, revision = asyncio.run(ContentActionExecutionService().execute(
        command=_command("a"), policy="bypass",
        actions=[{"id": "a", "scope": "hero", "automation_policy": "bypass"}],
        generate=generate, validate=lambda scope, candidate: candidate, persist_drafts=persist, apply_atomically=apply,
    ))
    assert len(generated) == 1
    assert revision == 5
    assert calls[0][1] == 4
