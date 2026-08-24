"""Atomic domain execution for selected Actionable Content Plan actions."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal


ExecutionPolicy = Literal["auto", "bypass"]


@dataclass(frozen=True)
class ExecuteContentActionsCommand:
    quotation_id: str
    plan_id: str
    action_ids: tuple[str, ...]
    expected_document_revision: int
    writing_style: Literal["storytelling", "detailed"]
    idempotency_key: str
    correlation_id: str


@dataclass(frozen=True)
class GeneratedActionCandidate:
    action_id: str
    scope: str
    candidate: dict[str, Any]


class ContentActionExecutionService:
    """Coordinates external generation then one atomic persistence operation.

    The persistence callbacks are injected so this service remains testable and
    never opens a database session or calls a router.
    """

    async def execute(
        self,
        *,
        command: ExecuteContentActionsCommand,
        policy: ExecutionPolicy,
        actions: list[dict[str, Any]],
        generate: Callable[[dict[str, Any], str], Awaitable[dict[str, Any]]],
        validate: Callable[[str, dict[str, Any]], dict[str, Any]],
        persist_drafts: Callable[[list[GeneratedActionCandidate]], Awaitable[dict[str, str]]],
        apply_atomically: Callable[[list[GeneratedActionCandidate], int], Awaitable[int]],
    ) -> tuple[list[GeneratedActionCandidate], dict[str, str] | int]:
        if not command.action_ids:
            raise ValueError("At least one Content action is required.")
        selected = [action for action in actions if action.get("id") in set(command.action_ids)]
        if len(selected) != len(command.action_ids):
            raise ValueError("One or more selected Content actions do not belong to this plan.")
        if any(action.get("automation_policy") != policy for action in selected):
            raise ValueError("Selected Content actions do not match the requested execution policy.")

        generated: list[GeneratedActionCandidate] = []
        # No persistence occurs before every remote generation and validation
        # succeeds. This is the fail-closed boundary for batch execution.
        for action in selected:
            candidate = await generate(action, command.writing_style)
            generated.append(GeneratedActionCandidate(
                action_id=str(action["id"]),
                scope=str(action["scope"]),
                candidate=validate(str(action["scope"]), candidate),
            ))
        if policy == "auto":
            return generated, await persist_drafts(generated)
        return generated, await apply_atomically(generated, command.expected_document_revision)
