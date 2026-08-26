"""Application service for immutable V2 quotation successor creation."""
from __future__ import annotations

import uuid
import copy
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from quote_document import CreateQuoteRequestV1, QuoteDocumentV1
from repositories import (
    ContentActionPlanRepository,
    QuotationDocumentRepository,
    QuotationRepository,
)
from repositories.destination_repository import DestinationRepository
from repositories.errors import DocumentRevisionConflictError
from services.facts_resolver import FactsResolutionError, FactsResolver
from services.media_default_service import MediaDefaultService
from services.outbox_service import OutboxService
from services.quotation_change_plan_service import QuotationChangePlanService
from services.quotation_version_factory import (
    CreateSuccessorCommand,
    QuotationVersionFactory,
    SuccessorPreparation,
)
from services.skeleton_builder import SkeletonBuilder


class LegacyQuotationVersionError(ValueError):
    pass


class TemplateChangeUnsupportedError(ValueError):
    pass


class QuotationVersionApplicationService:
    """Creates a physical successor and its Content Action Plan atomically."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.quotations = QuotationRepository(session)
        self.documents = QuotationDocumentRepository(session)
        self.action_plans = ContentActionPlanRepository(session)

    async def create_successor(
        self,
        *,
        predecessor_id: str,
        facts: CreateQuoteRequestV1,
        base_revision: int,
        profile_id: str | None,
        correlation_id: str,
    ) -> tuple[Any, list[Any]]:
        predecessor = await self.quotations.get_quotation_by_id(predecessor_id)
        if predecessor is None:
            raise LookupError("Quotation was not found.")
        if predecessor.quotation_family_id is None:
            raise LegacyQuotationVersionError("Legacy quotations cannot create business versions.")
        current = await self.documents.get_current_document(predecessor_id, predecessor.baseline_lang)
        previous_facts = await self.quotations.get_version_facts(predecessor_id)
        if current is None or previous_facts is None:
            raise ValueError("The immutable predecessor snapshot is unavailable.")
        if current.revision != base_revision:
            raise DocumentRevisionConflictError(
                quotation_id=predecessor_id,
                lang=predecessor.baseline_lang,
                expected_revision=base_revision,
                current_revision=current.revision,
                current_document=current.document_json,
            )
        predecessor_template_id = str((current.document_json.get("presentation") or {}).get("templateId") or "")
        requested_template_id = facts.presentation_options.template_id or predecessor_template_id
        if requested_template_id != predecessor_template_id:
            raise TemplateChangeUnsupportedError("Template cannot be changed until a V2 template registry is available.")

        successor_id = f"quo_{uuid.uuid4().hex[:12]}"
        successor_brand_id = facts.brand_id or predecessor.brand_id
        successor_lang = facts.lang or predecessor.baseline_lang

        async def resolve_facts(payload: CreateQuoteRequestV1) -> dict[str, Any]:
            try:
                canonical, resolved = await FactsResolver().resolve(payload, DestinationRepository(self.session).resolve)
            except FactsResolutionError as error:
                raise ValueError(f"Required quotation facts are missing: {', '.join(error.missing_inputs)}") from error
            # Factory owns the immutable snapshot; canonical Facts must be the
            # resolved payload, not the mutable request that entered the API.
            resolved["canonicalFacts"] = canonical.model_dump(mode="json")
            return resolved

        def build_skeleton(payload: CreateQuoteRequestV1, resolved: dict[str, Any]) -> dict[str, Any]:
            return SkeletonBuilder().build(
                quotation_id=successor_id,
                payload=payload,
                resolved_facts=resolved,
                template=predecessor.template_name,
            )

        async def resolve_media(document: dict[str, Any], _: CreateQuoteRequestV1) -> dict[str, Any]:
            await MediaDefaultService(self.session).apply_missing(
                document=document,
                quotation_id=successor_id,
                lang=successor_lang,
            )
            return document

        factory = QuotationVersionFactory(
            resolve_facts=resolve_facts,
            build_skeleton=build_skeleton,
            resolve_media_defaults=resolve_media,
        )

        async def persist(prepared: SuccessorPreparation) -> tuple[Any, list[Any]]:
            canonical_json = prepared.facts.model_dump(mode="json")
            next_business_version = await self.quotations.next_business_version(predecessor.quotation_family_id)
            successor = await self.quotations.create_quotation(
                quotation_id=successor_id,
                opportunity_id=predecessor.opportunity_id,
                brand_id=successor_brand_id,
                template_name=predecessor.template_name,
                baseline_lang=successor_lang,
                customer_name=prepared.facts.customer_facts.customer_name,
                title=(prepared.document.get("trip") or {}).get("title") or predecessor.title,
                status="draft",
                source_kind=predecessor.source_kind,
                source_snapshot_at=predecessor.source_snapshot_at,
                designer_profile_id=predecessor.designer_profile_id,
                created_by_profile_id=predecessor.created_by_profile_id,
                quotation_family_id=predecessor.quotation_family_id,
                business_version=next_business_version,
                parent_quotation_id=predecessor.id,
                source_request_id=predecessor.source_request_id,
                source_request_revision=predecessor.source_request_revision,
            )
            await self.quotations.create_quotation_request(quotation_id=successor_id, request_json=canonical_json)
            await self.quotations.create_version_facts(
                quotation_id=successor_id,
                canonical_facts_json=canonical_json,
                resolved_facts_json=prepared.resolved_facts,
                facts_hash=str(prepared.resolved_facts["factsHash"]),
                source_request_id=predecessor.source_request_id,
                source_request_revision=predecessor.source_request_revision,
            )
            prepared.document.setdefault("presentation", {})["templateId"] = requested_template_id
            if "viewOverrides" in current.document_json:
                prepared.document["viewOverrides"] = copy.deepcopy(current.document_json["viewOverrides"])
            document = QuoteDocumentV1.model_validate(prepared.document).model_dump(mode="json")
            document.setdefault("meta", {})["revision"] = 1
            saved = await self.documents.save_current_document(
                quotation_id=successor_id,
                lang=successor_lang,
                document_json=document,
                expected_revision=0,
            )
            document.setdefault("meta", {})["revision"] = saved.revision
            await self.documents.append_document_revision(
                quotation_id=successor_id,
                lang=successor_lang,
                revision=saved.revision,
                document_json=document,
                change_source="create_business_version",
            )
            actions = QuotationChangePlanService.build(previous_facts.canonical_facts_json, canonical_json)
            plan_id, action_rows = await QuotationChangePlanService.persist(
                repository=self.action_plans,
                quotation_id=successor_id,
                predecessor_quotation_id=predecessor_id,
                facts_hash=str(prepared.resolved_facts["factsHash"]),
                correlation_id=correlation_id,
                actions=actions,
            )
            outbox = OutboxService(self.session)
            await outbox.emit_event(
                event_type="quotation.version.created",
                aggregate_type="quotation",
                aggregate_id=successor_id,
                brand_id=successor_brand_id,
                correlation_id=correlation_id,
                payload={"quotation_family_id": successor.quotation_family_id, "business_version": successor.business_version, "parent_quotation_id": predecessor_id, "source_request_id": successor.source_request_id, "source_request_revision": successor.source_request_revision},
            )
            await outbox.emit_event(
                event_type="quotation.content_plan.created",
                aggregate_type="quotation",
                aggregate_id=successor_id,
                brand_id=successor_brand_id,
                correlation_id=correlation_id,
                payload={"plan_id": plan_id, "action_ids": [action.id for action in action_rows], "quotation_family_id": successor.quotation_family_id, "business_version": successor.business_version},
            )
            return successor, action_rows

        try:
            result = await factory.create(
                command=CreateSuccessorCommand(
                    predecessor_id=predecessor_id,
                    facts=facts,
                    base_document_revision=base_revision,
                    actor_profile_id=profile_id,
                    correlation_id=correlation_id,
                ),
                predecessor_document=current.document_json,
                persist_in_transaction=persist,
            )
            await self.session.commit()
            return result
        except Exception:
            await self.session.rollback()
            raise
