"""Application service for Actionable Content Plan HTTP use cases."""
from __future__ import annotations

import asyncio
import copy
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from quote_document import CreateQuoteRequestV1
from repositories import (
    BrandRepository,
    ContentActionPlanRepository,
    ContentDraftRepository,
    QuotationDocumentRepository,
    QuotationRepository,
)
from repositories.errors import DocumentRevisionConflictError
from schemas.brand_contract import _brand_generation_profile
from services.content_draft_service import ContentDraftService
from services.content_registry import scope_spec
from services.inherited_content_context_service import InheritedContentContextService
from services.outbox_service import OutboxService
from services.section_content_generator import SectionContentGenerator


class ContentActionNotFoundError(ValueError):
    pass


class ContentActionPolicyError(ValueError):
    pass


class ContentActionApplicationService:
    """Service owns transactions; routers only validate/authenticate/delegate."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.plans = ContentActionPlanRepository(session)
        self.quotes = QuotationRepository(session)
        self.documents = QuotationDocumentRepository(session)
        self.drafts = ContentDraftRepository(session)
        self.brands = BrandRepository(session)

    async def list(self, quotation_id: str) -> tuple[Any, list[Any]]:
        plan = await self._latest_plan(quotation_id)
        return plan, await self.plans.list_actions(plan.id)

    async def accept(self, *, quotation_id: str, note: str, profile_id: str | None, correlation_id: str) -> tuple[Any, list[Any]]:
        plan, actions = await self.list(quotation_id)
        was_accepted = plan.status == "accepted"
        await self.plans.accept_plan(plan=plan, profile_id=profile_id, note=note, correlation_id=correlation_id)
        quotation = await self._new_model_quotation(quotation_id)
        if not was_accepted:
            await OutboxService(self.session).emit_event(
                event_type="quotation.content_plan.accepted", aggregate_type="quotation", aggregate_id=quotation_id,
                brand_id=quotation.brand_id, correlation_id=correlation_id,
                payload={"plan_id": plan.id, "quotation_family_id": quotation.quotation_family_id, "business_version": quotation.business_version, "actor_profile_id": profile_id},
            )
        await self.session.commit()
        return plan, actions

    async def generate_drafts(
        self, *, quotation_id: str, plan_id: str, action_ids: list[str], writing_style: Literal["storytelling", "detailed"], profile_id: str | None, correlation_id: str,
    ) -> tuple[list[Any], int]:
        plan, actions, quotation, facts, document, brand = await self._execution_context(quotation_id, plan_id, action_ids, "auto")
        generated = await self._generate_all(actions=actions, facts=facts, document=document.document_json, quotation=quotation, brand=brand, writing_style=writing_style)
        lang = quotation.baseline_lang
        brand_id = quotation.brand_id
        source_revision = document.revision
        selected_action_ids = [row.id for row in actions]
        plan_id = plan.id
        # Complete the read transaction before atomically persisting every draft.
        await self.session.rollback()
        async with self.session.begin():
            current = await self.documents.get_current_document(quotation_id, lang)
            if current is None or current.revision != source_revision:
                raise DocumentRevisionConflictError(quotation_id=quotation_id, lang=lang, expected_revision=source_revision, current_revision=current.revision if current else 0, current_document=current.document_json if current else None)
            draft_rows = []
            for item in generated:
                draft_rows.append(await self.drafts.create(**item["draft_values"]))
            await self.plans.mark_actions(action_ids=selected_action_ids, state="draft_created", draft_ids={action_id: draft.id for action_id, draft in zip(selected_action_ids, draft_rows)}, correlation_id=correlation_id, profile_id=profile_id)
            await OutboxService(self.session).emit_event(event_type="quotation.content_action.drafts_created", aggregate_type="quotation", aggregate_id=quotation_id, brand_id=brand_id, correlation_id=correlation_id, payload={"plan_id": plan_id, "action_ids": selected_action_ids, "draft_ids": [draft.id for draft in draft_rows]})
        return draft_rows, source_revision

    async def generate_and_apply(
        self, *, quotation_id: str, plan_id: str, action_ids: list[str], expected_revision: int, writing_style: Literal["storytelling", "detailed"], profile_id: str | None, correlation_id: str, idempotency_key: str, document_overlay: dict[str, Any] | None = None,
        on_action_complete: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> tuple[list[Any], int]:
        replay = await self._replay_bypass_if_idempotent(
            quotation_id=quotation_id,
            plan_id=plan_id,
            action_ids=action_ids,
            idempotency_key=idempotency_key,
        )
        if replay is not None:
            return replay
        plan, actions, quotation, facts, document, brand = await self._execution_context(quotation_id, plan_id, action_ids, "bypass")
        if document.revision != expected_revision:
            raise DocumentRevisionConflictError(quotation_id=quotation_id, lang=quotation.baseline_lang, expected_revision=expected_revision, current_revision=document.revision, current_document=document.document_json)
        generated = await self._generate_all(actions=actions, facts=facts, document=document.document_json, quotation=quotation, brand=brand, writing_style=writing_style, on_action_complete=on_action_complete)
        lang = quotation.baseline_lang
        brand_id = quotation.brand_id
        selected_action_ids = [row.id for row in actions]
        plan_id = plan.id
        # The generated candidates are now in memory; persistence is a single
        # transaction so a partial bypass can never alter the document.
        await self.session.rollback()
        async with self.session.begin():
            current = await self.documents.get_current_document(quotation_id, lang)
            if current is None:
                raise ContentActionNotFoundError("Current quotation document was not found.")
            # Fast Track may supply an in-memory, Facts-owned media patch. It
            # is persisted only in this same transaction after every remote
            # content candidate has been generated and validated.
            merged = copy.deepcopy(document_overlay if document_overlay is not None else current.document_json)
            for item in generated:
                merged = ContentDraftService.apply_candidate(merged, item["scope"], item["candidate"])
            saved = await self.documents.save_current_document(quotation_id=quotation_id, lang=lang, document_json=merged, expected_revision=expected_revision)
            merged.setdefault("meta", {})["revision"] = saved.revision
            await self.documents.append_document_revision(quotation_id=quotation_id, lang=lang, revision=saved.revision, document_json=merged, change_source="content_action_bypass")
            draft_rows = []
            for item in generated:
                values = dict(item["draft_values"])
                values["status"] = "applied"
                draft_rows.append(await self.drafts.create(**values))
            await self.plans.mark_actions(action_ids=selected_action_ids, state="applied", draft_ids={action_id: draft.id for action_id, draft in zip(selected_action_ids, draft_rows)}, applied_document_revision=saved.revision, idempotency_key=idempotency_key, correlation_id=correlation_id, profile_id=profile_id)
            await OutboxService(self.session).emit_event(event_type="quotation.content_action.applied", aggregate_type="quotation", aggregate_id=quotation_id, brand_id=brand_id, correlation_id=correlation_id, payload={"plan_id": plan_id, "action_ids": selected_action_ids, "document_revision": saved.revision, "idempotency_key": idempotency_key})
        return draft_rows, saved.revision

    async def replay_bypass_if_idempotent(
        self,
        *,
        quotation_id: str,
        plan_id: str,
        action_ids: list[str],
        idempotency_key: str,
    ) -> tuple[list[Any], int] | None:
        """Public replay lookup for orchestrators (Fast Track D4) — see the private impl."""
        return await self._replay_bypass_if_idempotent(
            quotation_id=quotation_id,
            plan_id=plan_id,
            action_ids=action_ids,
            idempotency_key=idempotency_key,
        )

    async def _replay_bypass_if_idempotent(
        self,
        *,
        quotation_id: str,
        plan_id: str,
        action_ids: list[str],
        idempotency_key: str,
    ) -> tuple[list[Any], int] | None:
        """Return the original result for a safe client retry, never reapply it."""
        actions = await self.plans.get_actions(
            plan_id=plan_id,
            quotation_id=quotation_id,
            action_ids=action_ids,
        )
        if len(actions) != len(set(action_ids)) or not actions:
            return None
        if not all(action.state == "applied" for action in actions):
            return None
        if not all(action.idempotency_key == idempotency_key for action in actions):
            raise ContentActionPolicyError("Selected Content actions were already applied by another request.")
        draft_rows = []
        for action in actions:
            if action.draft_id is None:
                raise ContentActionPolicyError("Applied Content action is missing its audit draft.")
            draft = await self.drafts.get(quotation_id, action.draft_id)
            if draft is None:
                raise ContentActionPolicyError("Applied Content action audit draft is unavailable.")
            draft_rows.append(draft)
        revision = max(action.applied_document_revision or 0 for action in actions)
        if revision < 1:
            raise ContentActionPolicyError("Applied Content action is missing its document revision audit.")
        return draft_rows, revision

    async def _execution_context(self, quotation_id: str, plan_id: str, action_ids: list[str], policy: str) -> tuple[Any, list[Any], Any, CreateQuoteRequestV1, Any, Any]:
        plan = await self.plans.get_plan(plan_id, quotation_id)
        if plan is None:
            raise ContentActionNotFoundError("Content action plan was not found.")
        actions = await self.plans.get_actions(plan_id=plan_id, quotation_id=quotation_id, action_ids=action_ids)
        if len(actions) != len(set(action_ids)):
            raise ContentActionNotFoundError("One or more selected Content actions were not found.")
        if not actions:
            raise ContentActionPolicyError("At least one Content action must be selected.")
        if plan.status != "accepted":
            raise ContentActionPolicyError("Accept the Content action plan before executing an action.")
        if any(action.automation_policy != policy for action in actions):
            raise ContentActionPolicyError("Selected Content actions do not support this execution mode.")
        if any(action.state not in {"pending", "accepted"} for action in actions):
            raise ContentActionPolicyError("Selected Content actions have already been executed.")
        quotation = await self._new_model_quotation(quotation_id)
        version_facts = await self.quotes.get_version_facts(quotation_id)
        document = await self.documents.get_current_document(quotation_id, quotation.baseline_lang)
        brand = await self.brands.get_active(quotation.brand_id)
        if version_facts is None or document is None or brand is None:
            raise ContentActionNotFoundError("Content action context is unavailable.")
        return plan, actions, quotation, CreateQuoteRequestV1.model_validate(version_facts.canonical_facts_json), document, brand

    async def _generate_all(
        self,
        *,
        actions: list[Any],
        facts: CreateQuoteRequestV1,
        document: dict[str, Any],
        quotation: Any,
        brand: Any,
        writing_style: str,
        on_action_complete: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> list[dict[str, Any]]:
        predecessor_document = None
        predecessor_facts = None
        if quotation.parent_quotation_id:
            previous = await self.documents.get_current_document(quotation.parent_quotation_id, quotation.baseline_lang)
            previous_facts = await self.quotes.get_version_facts(quotation.parent_quotation_id)
            predecessor_document = previous.document_json if previous else None
            predecessor_facts = previous_facts.canonical_facts_json if previous_facts else None
        generator = SectionContentGenerator()
        draft_service = ContentDraftService(self.drafts, _brand_generation_profile(brand))
        version_facts = await self.quotes.get_version_facts(quotation.id)
        if version_facts is None:
            raise ContentActionNotFoundError("Immutable Facts snapshot is unavailable.")
        current_facts_json = facts.model_dump(mode="json")

        async def _generate_one(action: Any) -> dict[str, Any]:
            scope = action.scope
            inherited = InheritedContentContextService.for_scope(
                scope=scope,
                predecessor_document=predecessor_document,
                predecessor_facts=predecessor_facts,
                current_facts=current_facts_json,
            )
            snapshot = draft_service.facts_snapshot(facts, scope, inherited_reference=inherited)
            missing = draft_service.missing_for_scope(facts, scope)
            if missing:
                raise ValueError(f"Required Facts are missing for {scope}.")
            spec = scope_spec(scope)
            started = time.perf_counter()
            candidate, metadata = await generator.generate(
                spec=spec,
                brand=_brand_generation_profile(brand),
                facts_snapshot=snapshot,
                mode=writing_style,
                instruction="",
            )
            candidate = draft_service.validate_candidate(scope, candidate)
            prompt_version = f"cap-{uuid.uuid4().hex[:24]}"
            return (
                {
                    "scope": scope,
                    "candidate": candidate,
                    "draft_values": {
                        "id": f"cd_{uuid.uuid4().hex[:20]}",
                        "quotation_id": quotation.id,
                        "lang": quotation.baseline_lang,
                        "scope": scope,
                        "generation_mode": writing_style,
                        "status": "draft",
                        "facts_hash": version_facts.facts_hash,
                        "source_document_revision": int((document.get("meta") or {}).get("revision") or 1),
                        "prompt_version": prompt_version,
                        "facts_snapshot": snapshot,
                        "candidate_json": candidate,
                        "missing_inputs": [],
                        "generation_metadata": {
                            **metadata,
                            "actionPlan": True,
                            "actionId": action.id,
                            "inheritedReferenceStatus": inherited.get("status"),
                            "inheritedReferenceHash": inherited.get("hash"),
                            "latencyMs": round((time.perf_counter() - started) * 1000),
                        },
                    },
                }
            )

        total = len(actions)
        completed = 0

        async def _generate_one_and_report(action: Any) -> dict[str, Any]:
            nonlocal completed
            result = await _generate_one(action)
            # Single-threaded event loop: no lock needed between the increment
            # and the report — no `await` separates them (16.3 F-21).
            completed += 1
            if on_action_complete is not None:
                await on_action_complete(completed, total)
            return result

        # All remote generations run concurrently (16.3 F-07); gather preserves
        # action order and the first failure aborts the whole batch — same
        # all-or-nothing semantics as the sequential loop, at 1/N the latency.
        return list(await asyncio.gather(*(_generate_one_and_report(action) for action in actions)))

    async def _latest_plan(self, quotation_id: str) -> Any:
        from sqlalchemy import select
        from db.models.quotation import QuotationContentActionPlan
        plan = await self.session.scalar(select(QuotationContentActionPlan).where(QuotationContentActionPlan.quotation_id == quotation_id).order_by(QuotationContentActionPlan.created_at.desc()))
        if plan is None:
            raise ContentActionNotFoundError("Content action plan was not found.")
        return plan

    async def _new_model_quotation(self, quotation_id: str) -> Any:
        quotation = await self.quotes.get_quotation_by_id(quotation_id)
        if quotation is None or quotation.quotation_family_id is None:
            raise ContentActionNotFoundError("Content actions are available only for new-model quotation versions.")
        return quotation
