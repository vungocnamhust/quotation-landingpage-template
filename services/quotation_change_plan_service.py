"""Create Content-only Actionable Content Plans from immutable Fact changes."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any
from uuid import uuid4

from core.rules.content_action_reconciler import content_input_fingerprint, reconcile_itinerary_entities
from services.content_registry import CONTENT_SECTION_REGISTRY, build_prompt_context, scope_spec


@dataclass(frozen=True)
class ContentActionBlueprint:
    action_key: str
    scope: str
    entity_key: str
    reason_code: str
    automation_policy: str
    input_facts_hash: str
    inherited_reference_status: str
    metadata: dict[str, Any]


class QuotationChangePlanService:
    """Small scope-input plan, not a leaf-level Fact dependency engine."""

    @classmethod
    def build(cls, previous_facts: dict[str, Any], current_facts: dict[str, Any]) -> list[ContentActionBlueprint]:
        previous_model = cls._model(previous_facts)
        current_model = cls._model(current_facts)
        actions: list[ContentActionBlueprint] = []
        for scope, spec in CONTENT_SECTION_REGISTRY.items():
            if spec.owner != "content":
                continue
            before = build_prompt_context(previous_model, scope)
            after = build_prompt_context(current_model, scope)
            if content_input_fingerprint(before) == content_input_fingerprint(after):
                continue
            reason = "manual_facts_changed" if not spec.generation else "facts_changed"
            actions.append(cls._action(scope, scope, reason, spec.automation_policy, after, "unavailable"))

        old_days = (previous_facts.get("trip_facts") or {}).get("itinerary") or []
        new_days = (current_facts.get("trip_facts") or {}).get("itinerary") or []
        for change in reconcile_itinerary_entities(old_days, new_days):
            fact_id = change.entity_key.removeprefix("day:")
            scope = f"itinerary:day:{fact_id}"
            if change.operation in {"added", "semantic_replaced"}:
                current_context = build_prompt_context(current_model, scope)
                actions.append(cls._action(scope, change.entity_key, change.operation, scope_spec(scope).automation_policy, current_context, "unavailable", old=change.old_value, new=change.new_value))
            elif change.operation == "removed":
                actions.append(cls._action(scope, change.entity_key, "retired", "manual", {}, "retired", old=change.old_value, new=None))
        return actions

    @classmethod
    def build_initial(cls, current_facts: dict[str, Any]) -> list[ContentActionBlueprint]:
        """Create the first lifecycle plan for an intentionally empty skeleton."""
        current_model = cls._model(current_facts)
        actions: list[ContentActionBlueprint] = []
        for scope, spec in CONTENT_SECTION_REGISTRY.items():
            if spec.owner == "content" and spec.generation:
                actions.append(cls._action(scope, scope, "initial_skeleton", spec.automation_policy, build_prompt_context(current_model, scope), "unavailable"))
        for day in (current_facts.get("trip_facts") or {}).get("itinerary") or []:
            fact_id = str(day.get("id") or day.get("day_number"))
            scope = f"itinerary:day:{fact_id}"
            actions.append(cls._action(scope, f"day:{fact_id}", "initial_skeleton", scope_spec(scope).automation_policy, build_prompt_context(current_model, scope), "unavailable"))
        return actions

    @staticmethod
    async def persist(
        *,
        repository: Any,
        quotation_id: str,
        predecessor_quotation_id: str | None,
        facts_hash: str,
        correlation_id: str,
        actions: list[ContentActionBlueprint],
    ) -> tuple[str, list[Any]]:
        """Persist the plan through a repository owned by the caller session."""
        canonical_actions = [
            {
                "actionKey": action.action_key,
                "scope": action.scope,
                "entityKey": action.entity_key,
                "reasonCode": action.reason_code,
                "policy": action.automation_policy,
                "inputFactsHash": action.input_facts_hash,
            }
            for action in actions
        ]
        plan_hash = sha256(json.dumps(canonical_actions, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        plan_id = f"cap_{uuid4().hex[:20]}"
        await repository.create_plan(
            plan_id=plan_id,
            quotation_id=quotation_id,
            predecessor_quotation_id=predecessor_quotation_id,
            facts_hash=facts_hash,
            plan_hash=plan_hash,
            correlation_id=correlation_id,
        )
        rows = await repository.create_actions(
            plan_id=plan_id,
            quotation_id=quotation_id,
            values=[
                {
                    "id": f"caa_{uuid4().hex[:20]}",
                    "action_key": action.action_key,
                    "scope": action.scope,
                    "entity_key": action.entity_key,
                    "reason_code": action.reason_code,
                    "automation_policy": action.automation_policy,
                    "input_facts_hash": action.input_facts_hash,
                    "predecessor_quotation_id": predecessor_quotation_id,
                    "inherited_reference_status": action.inherited_reference_status,
                    "action_metadata_json": action.metadata,
                }
                for action in actions
            ],
        )
        return plan_id, rows

    @staticmethod
    def _model(facts: dict[str, Any]) -> Any:
        from quote_document import CreateQuoteRequestV1
        return CreateQuoteRequestV1.model_validate(facts)

    @staticmethod
    def _action(scope: str, entity_key: str, reason_code: str, policy: str, context: dict[str, Any], inherited_status: str, *, old: dict[str, Any] | None = None, new: dict[str, Any] | None = None) -> ContentActionBlueprint:
        return ContentActionBlueprint(
            action_key=f"{scope}:{reason_code}", scope=scope, entity_key=entity_key,
            reason_code=reason_code, automation_policy=policy,
            input_facts_hash=content_input_fingerprint(context), inherited_reference_status=inherited_status,
            metadata={"old": old, "new": new},
        )
