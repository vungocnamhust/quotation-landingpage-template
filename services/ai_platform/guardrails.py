"""Guardrails for AI Platform agent runs (15.8 §1.1, bootstrap for 15.7).

Three independent, composable primitives — no framework, no plugin system:

- ``RunBudget``: hard cap on tool calls per run; raises when exceeded instead of letting a
  run spiral.
- ``AllowlistRecorder``: every id a read-only tool hands back to the LLM is recorded here.
  Downstream code (resolution_service) treats a ``matched_id`` proposed by an agent as
  untrusted unless it appears in this allowlist — the LLM cannot invent an id it never saw.
- ``OutputValidator``: drops individual invalid items from a typed agent output instead of
  failing the whole run ("bỏ dòng, không nổ run") — e.g. a candidate missing its required
  ``source_quote``.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import TypeVar

T = TypeVar("T")


class RunBudgetExceededError(RuntimeError):
    def __init__(self, max_calls: int) -> None:
        super().__init__(f"AI run exceeded its tool-call budget ({max_calls} calls).")
        self.max_calls = max_calls


@dataclass
class RunBudget:
    """Hard cap on tool calls for a single agent run — a call-count ceiling, not a token budget."""

    max_calls: int = 8
    max_retries: int = 2
    calls: int = 0
    retries: int = 0

    def has_budget(self) -> bool:
        """Non-raising check — tools should call this BEFORE doing work and degrade
        gracefully (return an informative result) rather than call ``record_call()``
        past the limit, since raising from inside a tool call aborts the whole agent run
        instead of letting the model wrap up with what it already has."""
        return self.calls < self.max_calls

    def record_call(self) -> None:
        """Hard stop for callers that do NOT check ``has_budget()`` first. Tool functions
        should prefer ``has_budget()`` + a graceful early return; this raise is a safety
        net for misuse, not the normal degrade path."""
        self.calls += 1
        if self.calls > self.max_calls:
            raise RunBudgetExceededError(self.max_calls)

    def record_retry(self) -> None:
        self.retries += 1

    def stats(self) -> dict[str, int]:
        return {"calls": self.calls, "retries": self.retries}


@dataclass
class AllowlistRecorder:
    """Append-only ledger of every entity id a read-only tool has returned to the LLM."""

    _ids: set[str] = field(default_factory=set)

    def record(self, ids: Iterable[str | None]) -> None:
        for value in ids:
            if value:
                self._ids.add(value)

    def contains(self, entity_id: str | None) -> bool:
        return bool(entity_id) and entity_id in self._ids

    def snapshot(self) -> frozenset[str]:
        return frozenset(self._ids)


@dataclass
class OutputValidator:
    """Filters a typed agent output list, dropping invalid items instead of failing the run."""

    dropped: list[tuple[int, str]] = field(default_factory=list)

    def filter_valid(self, items: Iterable[T], *, is_valid: Callable[[T], bool], reason: str) -> list[T]:
        kept: list[T] = []
        for index, item in enumerate(items):
            if is_valid(item):
                kept.append(item)
            else:
                self.dropped.append((index, reason))
        return kept

    def has_dropped(self) -> bool:
        return bool(self.dropped)
