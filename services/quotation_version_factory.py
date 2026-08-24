"""Domain factory for immutable quotation successor creation.

The factory is intentionally transport-free. Sprint 3 supplies repository and
session adapters; routers do not import this module's collaborators directly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, TypeVar

from core.rules.semantic_identity import assign_missing_source_fact_ids
from quote_document import CreateQuoteRequestV1
from services.semantic_content_carry_forward_service import SemanticContentCarryForwardService


@dataclass(frozen=True)
class CreateSuccessorCommand:
    predecessor_id: str
    facts: CreateQuoteRequestV1
    base_document_revision: int
    actor_profile_id: str | None
    correlation_id: str


@dataclass(frozen=True)
class SuccessorPreparation:
    facts: CreateQuoteRequestV1
    resolved_facts: dict[str, Any]
    document: dict[str, Any]
    predecessor_id: str


PersistedSuccessor = TypeVar("PersistedSuccessor")


class QuotationVersionFactory:
    """Prepare a successor without importing the FastAPI composition root."""

    def __init__(
        self,
        *,
        resolve_facts: Callable[[CreateQuoteRequestV1], Awaitable[dict[str, Any]]],
        build_skeleton: Callable[[CreateQuoteRequestV1, dict[str, Any]], dict[str, Any]],
        resolve_media_defaults: Callable[[dict[str, Any], CreateQuoteRequestV1], Awaitable[dict[str, Any]]],
    ) -> None:
        self._resolve_facts = resolve_facts
        self._build_skeleton = build_skeleton
        self._resolve_media_defaults = resolve_media_defaults

    async def prepare(
        self,
        *,
        command: CreateSuccessorCommand,
        predecessor_document: dict[str, Any],
    ) -> SuccessorPreparation:
        facts = self._with_permanent_fact_ids(command.facts, command.predecessor_id)
        resolved = await self._resolve_facts(facts)
        canonical_snapshot = resolved.pop("canonicalFacts", None)
        if isinstance(canonical_snapshot, dict):
            facts = CreateQuoteRequestV1.model_validate(canonical_snapshot)
        if resolved.get("missingInputs"):
            raise ValueError("Required quotation facts are missing.")
        rebuilt = self._build_skeleton(facts, resolved)
        carried = SemanticContentCarryForwardService.carry_forward(predecessor_document, rebuilt)
        completed = await self._resolve_media_defaults(carried, facts)
        return SuccessorPreparation(
            facts=facts,
            resolved_facts=resolved,
            document=completed,
            predecessor_id=command.predecessor_id,
        )

    async def create(
        self,
        *,
        command: CreateSuccessorCommand,
        predecessor_document: dict[str, Any],
        persist_in_transaction: Callable[[SuccessorPreparation], Awaitable[PersistedSuccessor]],
    ) -> PersistedSuccessor:
        """Prepare then persist through one caller-owned transaction boundary.

        The injected callback is deliberately responsible for repository writes,
        action-plan creation and outbox emission in a single database session.
        This keeps domain creation testable and avoids a router/main.py cycle.
        """
        prepared = await self.prepare(command=command, predecessor_document=predecessor_document)
        return await persist_in_transaction(prepared)

    @staticmethod
    def _with_permanent_fact_ids(facts: CreateQuoteRequestV1, namespace: str) -> CreateQuoteRequestV1:
        payload = facts.model_dump(mode="json")
        trip = payload.setdefault("trip_facts", {})
        services = payload.setdefault("service_facts", {})
        trip["itinerary"] = assign_missing_source_fact_ids(
            list(trip.get("itinerary") or []), creation_namespace=namespace, kind="itinerary_day"
        )
        services["hotels"] = assign_missing_source_fact_ids(
            list(services.get("hotels") or []), creation_namespace=namespace, kind="hotel"
        )
        return CreateQuoteRequestV1.model_validate(payload)
