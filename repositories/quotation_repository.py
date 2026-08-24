from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Select, and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db.models.quotation import (
    Quotation,
    QuotationContentDraft,
    QuotationDocument,
    QuotationDocumentRevision,
    QuotationRequest,
    QuotationVersionFacts,
    QuotationVersionImpact,
    QuotationVersionImpactTarget,
    QuotationVersionImpactAcceptance,
    QuotationContentAction,
    QuotationContentActionPlan,
)
from repositories.errors import DocumentRevisionConflictError

_UNSET = object()


class QuotationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_quotation(
        self,
        *,
        quotation_id: str,
        brand_id: str,
        template_name: str,
        baseline_lang: str,
        opportunity_id: str | None = None,
        customer_name: str | None = None,
        title: str | None = None,
        status: str = "draft",
        current_revision: int = 0,
        current_version: int = 0,
        source_kind: str = "manual",
        source_version: str | None = None,
        source_snapshot_at: datetime | None = None,
        designer_profile_id: str | None = None,
        created_by_profile_id: str | None = None,
        quotation_family_id: str | None = None,
        business_version: int | None = None,
        parent_quotation_id: str | None = None,
        source_request_id: str | None = None,
        source_request_revision: int | None = None,
    ) -> Quotation:
        quotation = Quotation(
            id=quotation_id,
            opportunity_id=opportunity_id,
            source_kind=source_kind,
            source_version=source_version,
            source_snapshot_at=source_snapshot_at,
            brand_id=brand_id,
            status=status,
            baseline_lang=baseline_lang,
            current_revision=current_revision,
            current_version=current_version,
            template_name=template_name,
            designer_profile_id=designer_profile_id,
            created_by_profile_id=created_by_profile_id or designer_profile_id,
            quotation_family_id=quotation_family_id,
            business_version=business_version,
            parent_quotation_id=parent_quotation_id,
            source_request_id=source_request_id,
            source_request_revision=source_request_revision,
            customer_name=customer_name,
            title=title,
        )
        self.session.add(quotation)
        await self.session.flush()
        return quotation

    async def list_versions_for_request_revision(self, request_id: str, revision: int) -> list[Quotation]:
        result = await self.session.scalars(
            select(Quotation)
            .where(Quotation.source_request_id == request_id, Quotation.source_request_revision == revision)
            .order_by(Quotation.quotation_family_id.asc(), Quotation.business_version.asc(), Quotation.created_at.asc())
        )
        return list(result.all())

    async def next_business_version(self, quotation_family_id: str) -> int:
        value = await self.session.scalar(
            select(func.max(Quotation.business_version)).where(Quotation.quotation_family_id == quotation_family_id)
        )
        return int(value or 0) + 1

    async def get_version_facts(self, quotation_id: str) -> QuotationVersionFacts | None:
        return await self.session.scalar(
            select(QuotationVersionFacts).where(QuotationVersionFacts.quotation_id == quotation_id)
        )

    async def create_version_facts(
        self,
        *,
        quotation_id: str,
        canonical_facts_json: dict[str, Any],
        resolved_facts_json: dict[str, Any],
        facts_hash: str,
        source_request_id: str | None,
        source_request_revision: int | None,
    ) -> QuotationVersionFacts:
        row = QuotationVersionFacts(
            quotation_id=quotation_id,
            canonical_facts_json=canonical_facts_json,
            resolved_facts_json=resolved_facts_json,
            facts_hash=facts_hash,
            source_request_id=source_request_id,
            source_request_revision=source_request_revision,
        )
        self.session.add(row)
        await self.session.flush()
        return row


    async def create_quotation_request(
        self,
        *,
        quotation_id: str,
        request_json: dict[str, Any],
    ) -> QuotationRequest:
        request = QuotationRequest(
            quotation_id=quotation_id,
            request_json=request_json,
        )
        self.session.add(request)
        await self.session.flush()
        return request

    async def get_quotation_by_id(self, quotation_id: str) -> Quotation | None:
        return await self.session.get(Quotation, quotation_id)

    async def get_latest_quotation_request(self, quotation_id: str) -> QuotationRequest | None:
        stmt = (
            select(QuotationRequest)
            .where(QuotationRequest.quotation_id == quotation_id)
            .order_by(QuotationRequest.created_at.desc(), QuotationRequest.id.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_quotations(
        self,
        *,
        status: str | None = None,
        opportunity_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Quotation]:
        stmt: Select[tuple[Quotation]] = select(Quotation).order_by(Quotation.updated_at.desc(), Quotation.id.desc())
        if status:
            stmt = stmt.where(Quotation.status == status)
        if opportunity_id:
            stmt = stmt.where(Quotation.opportunity_id == opportunity_id)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def list_for_designer(
        self,
        *,
        designer_profile_id: str | None = None,
        status: str | None = None,
        search: str = "",
        updated_before: datetime | None = None,
        id_before: str | None = None,
        limit: int = 20,
    ) -> list[Quotation]:
        """Keyset-paginated, owner-scoped workspace list."""
        stmt: Select[tuple[Quotation]] = select(Quotation).where(Quotation.template_name == "quote-generator")
        if designer_profile_id:
            stmt = stmt.where(
                or_(
                    Quotation.designer_profile_id == designer_profile_id,
                    Quotation.created_by_profile_id == designer_profile_id,
                )
            )
        if status:
            stmt = stmt.where(Quotation.status == status)
        term = search.strip()
        if term:
            pattern = f"%{term}%"
            stmt = stmt.where(
                or_(
                    Quotation.id.ilike(pattern),
                    Quotation.title.ilike(pattern),
                    Quotation.customer_name.ilike(pattern),
                )
            )
        if updated_before is not None and id_before:
            stmt = stmt.where(or_(Quotation.updated_at < updated_before, and_(Quotation.updated_at == updated_before, Quotation.id < id_before)))
        stmt = stmt.order_by(Quotation.updated_at.desc(), Quotation.id.desc()).limit(max(1, min(limit, 100)))
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def status_summary_for_designer(self, designer_profile_id: str) -> dict[str, int]:
        rows = await self.session.execute(
            select(Quotation.status, func.count(Quotation.id))
            .where(
                or_(
                    Quotation.designer_profile_id == designer_profile_id,
                    Quotation.created_by_profile_id == designer_profile_id,
                ),
                Quotation.template_name == "quote-generator",
            )
            .group_by(Quotation.status)
        )
        return {str(status): int(count) for status, count in rows.all()}

    async def status_summary_workspace(self) -> dict[str, int]:
        rows = await self.session.execute(
            select(Quotation.status, func.count(Quotation.id))
            .where(Quotation.template_name == "quote-generator")
            .group_by(Quotation.status)
        )
        return {str(status): int(count) for status, count in rows.all()}

    async def update_quotation_status(
        self,
        quotation_id: str,
        *,
        status: str,
        current_version: int | None = None,
    ) -> Quotation:
        quotation = await self.get_quotation_by_id(quotation_id)
        if quotation is None:
            raise ValueError(f"Quotation {quotation_id} not found")
        quotation.status = status
        if current_version is not None:
            quotation.current_version = current_version
        await self.session.flush()
        return quotation


class ContentActionPlanRepository:
    """Persistence only for Actionable Content Plans and their action rows."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_plan(
        self,
        *,
        plan_id: str,
        quotation_id: str,
        predecessor_quotation_id: str | None,
        facts_hash: str,
        plan_hash: str,
        correlation_id: str | None,
    ) -> QuotationContentActionPlan:
        plan = QuotationContentActionPlan(
            id=plan_id,
            quotation_id=quotation_id,
            predecessor_quotation_id=predecessor_quotation_id,
            facts_hash=facts_hash,
            plan_hash=plan_hash,
            correlation_id=correlation_id,
        )
        self.session.add(plan)
        await self.session.flush()
        return plan

    async def create_actions(self, *, plan_id: str, quotation_id: str, values: list[dict[str, Any]]) -> list[QuotationContentAction]:
        rows: list[QuotationContentAction] = []
        for value in values:
            payload = dict(value)
            rows.append(QuotationContentAction(id=str(payload.pop("id")), plan_id=plan_id, quotation_id=quotation_id, **payload))
        self.session.add_all(rows)
        await self.session.flush()
        return rows

    async def list_actions(self, plan_id: str) -> list[QuotationContentAction]:
        result = await self.session.scalars(
            select(QuotationContentAction)
            .where(QuotationContentAction.plan_id == plan_id)
            .order_by(QuotationContentAction.scope, QuotationContentAction.action_key)
        )
        return list(result.all())

    async def get_plan(self, plan_id: str, quotation_id: str) -> QuotationContentActionPlan | None:
        return await self.session.scalar(
            select(QuotationContentActionPlan).where(
                QuotationContentActionPlan.id == plan_id,
                QuotationContentActionPlan.quotation_id == quotation_id,
            )
        )

    async def get_actions(self, *, plan_id: str, quotation_id: str, action_ids: list[str]) -> list[QuotationContentAction]:
        result = await self.session.scalars(
            select(QuotationContentAction).where(
                QuotationContentAction.plan_id == plan_id,
                QuotationContentAction.quotation_id == quotation_id,
                QuotationContentAction.id.in_(action_ids),
            )
        )
        return list(result.all())

    async def accept_plan(
        self,
        *,
        plan: QuotationContentActionPlan,
        profile_id: str | None,
        note: str,
        correlation_id: str,
    ) -> QuotationContentActionPlan:
        if plan.status == "accepted":
            return plan
        plan.status = "accepted"
        plan.accepted_by_profile_id = profile_id
        plan.accepted_at = datetime.now().astimezone()
        plan.acceptance_note = note
        plan.correlation_id = correlation_id
        await self.session.flush()
        return plan

    async def mark_actions(
        self,
        *,
        action_ids: list[str],
        state: str,
        draft_ids: dict[str, str] | None = None,
        applied_document_revision: int | None = None,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
        profile_id: str | None = None,
    ) -> None:
        rows = await self.session.scalars(select(QuotationContentAction).where(QuotationContentAction.id.in_(action_ids)))
        now = datetime.now().astimezone()
        for row in rows:
            row.state = state
            row.draft_id = (draft_ids or {}).get(row.id, row.draft_id)
            row.applied_document_revision = applied_document_revision
            row.idempotency_key = idempotency_key
            row.correlation_id = correlation_id
            row.executed_by_profile_id = profile_id
            row.executed_at = now
        await self.session.flush()


class QuotationVersionImpactRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_many(self, quotation_id: str, impacts: list[dict[str, Any]]) -> list[QuotationVersionImpact]:
        target_specs = [impact.pop("targets", []) for impact in impacts]
        rows = [QuotationVersionImpact(quotation_id=quotation_id, **impact) for impact in impacts]
        self.session.add_all(rows)
        await self.session.flush()
        targets = [QuotationVersionImpactTarget(impact_id=row.id, quotation_id=quotation_id, **target)
                   for row, specs in zip(rows, target_specs) for target in specs]
        self.session.add_all(targets)
        await self.session.flush()
        return rows

    async def list(self, quotation_id: str, *, pending_only: bool = False) -> list[QuotationVersionImpact]:
        statement = select(QuotationVersionImpact).where(QuotationVersionImpact.quotation_id == quotation_id)
        if pending_only:
            statement = statement.where(QuotationVersionImpact.status == "pending")
        result = await self.session.scalars(
            statement.order_by(QuotationVersionImpact.stage, QuotationVersionImpact.scope, QuotationVersionImpact.id)
        )
        return list(result.all())

    async def list_targets(self, quotation_id: str) -> list[QuotationVersionImpactTarget]:
        result = await self.session.scalars(
            select(QuotationVersionImpactTarget)
            .where(QuotationVersionImpactTarget.quotation_id == quotation_id)
            .order_by(QuotationVersionImpactTarget.stage, QuotationVersionImpactTarget.scope, QuotationVersionImpactTarget.id)
        )
        return list(result.all())

    async def get_acceptance(self, quotation_id: str, idempotency_key: str) -> QuotationVersionImpactAcceptance | None:
        return await self.session.scalar(
            select(QuotationVersionImpactAcceptance).where(
                QuotationVersionImpactAcceptance.quotation_id == quotation_id,
                QuotationVersionImpactAcceptance.idempotency_key == idempotency_key,
            )
        )

    async def resolve(self, quotation_id: str, impact_id: int, *, note: str, profile_id: str | None) -> QuotationVersionImpact | None:
        row = await self.session.scalar(
            select(QuotationVersionImpact).where(
                QuotationVersionImpact.id == impact_id,
                QuotationVersionImpact.quotation_id == quotation_id,
            )
        )
        if row is None:
            return None
        row.status = "resolved"
        row.resolution_note = note
        row.resolved_by_profile_id = profile_id
        row.resolved_at = datetime.now().astimezone()
        await self.session.flush()
        return row

    async def accept_all(
        self,
        quotation_id: str,
        *,
        selected_target_ids: set[int],
        note: str,
        profile_id: str | None,
        idempotency_key: str,
        correlation_id: str,
    ) -> list[QuotationVersionImpact]:
        existing = await self.get_acceptance(quotation_id, idempotency_key)
        if existing is not None:
            if set(existing.selected_target_ids_json) != set(selected_target_ids) or existing.resolution_note != note:
                raise ValueError("Idempotency key was already used with a different Impact Center acceptance.")
            return await self.list(quotation_id)
        rows = await self.list(quotation_id, pending_only=True)
        now = datetime.now().astimezone()
        for row in rows:
            row.status = "resolved"
            row.resolution_note = note
            row.resolved_by_profile_id = profile_id
            row.resolved_at = now
            row.generation_selected = False
            row.generation_status = "not_requested"
        targets = await self.session.scalars(
            select(QuotationVersionImpactTarget).where(QuotationVersionImpactTarget.quotation_id == quotation_id)
        )
        selected = set(selected_target_ids)
        for target in targets:
            target.accepted_by_profile_id = profile_id
            target.accepted_at = now
            target.generation_selected = target.generation_eligible and target.id in selected
            target.execution_status = "selected" if target.generation_selected else "not_requested"
            target.correlation_id = correlation_id
        self.session.add(QuotationVersionImpactAcceptance(quotation_id=quotation_id, idempotency_key=idempotency_key, correlation_id=correlation_id, selected_target_ids_json=sorted(selected), resolution_note=note, accepted_by_profile_id=profile_id))
        await self.session.flush()
        return rows

    async def selected_for_generation(self, quotation_id: str) -> list[QuotationVersionImpact]:
        result = await self.session.scalars(
            select(QuotationVersionImpact).where(
                QuotationVersionImpact.quotation_id == quotation_id,
                QuotationVersionImpact.generation_selected.is_(True),
                QuotationVersionImpact.generation_status == "selected",
            ).order_by(QuotationVersionImpact.id)
        )
        return list(result.all())

    async def mark_generation_status(
        self,
        rows: list[QuotationVersionImpact],
        *,
        status: str,
    ) -> None:
        for row in rows:
            row.generation_status = status
        row_ids = [row.id for row in rows]
        if row_ids:
            await self.session.execute(
                update(QuotationVersionImpactTarget)
                .where(QuotationVersionImpactTarget.impact_id.in_(row_ids))
                .values(execution_status=status)
            )
        await self.session.flush()


class QuotationDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _raise_document_conflict(
        self,
        *,
        quotation_id: str,
        lang: str,
        expected_revision: int | None,
    ) -> None:
        current = None
        bind = self.session.bind
        if bind is not None:
            fresh_session_factory = async_sessionmaker(bind=bind, class_=AsyncSession, expire_on_commit=False)
            async with fresh_session_factory() as fresh_session:
                fresh_repository = QuotationDocumentRepository(fresh_session)
                current = await fresh_repository.get_current_document(quotation_id, lang)
        if current is None:
            current = await self.get_current_document(quotation_id, lang)
        raise DocumentRevisionConflictError(
            quotation_id=quotation_id,
            lang=lang,
            expected_revision=expected_revision,
            current_revision=current.revision if current is not None else 0,
            current_document=current.document_json if current is not None else None,
        )

    async def _load_document_by_id(self, document_id: int) -> QuotationDocument:
        stmt = (
            select(QuotationDocument)
            .where(QuotationDocument.id == document_id)
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def _update_current_document_atomic(
        self,
        *,
        quotation_id: str,
        lang: str,
        document_json: dict[str, Any],
        expected_revision: int | None,
        next_revision: int | None,
        html_sync: dict[str, Any] | None | object,
        generation_status: dict[str, Any] | None | object,
    ) -> QuotationDocument | None:
        update_values: dict[str, Any] = {
            "document_json": document_json,
            "is_current": True,
        }
        update_values["revision"] = next_revision if next_revision is not None else QuotationDocument.revision + 1
        if html_sync is not _UNSET:
            update_values["html_sync"] = html_sync
        if generation_status is not _UNSET:
            update_values["generation_status"] = generation_status

        stmt = (
            update(QuotationDocument)
            .where(QuotationDocument.quotation_id == quotation_id)
            .where(QuotationDocument.lang == lang)
            .where(QuotationDocument.is_current.is_(True))
            .values(**update_values)
            .returning(QuotationDocument.id)
            .execution_options(synchronize_session=False)
        )
        if expected_revision is not None:
            stmt = stmt.where(QuotationDocument.revision == expected_revision)

        result = await self.session.execute(stmt)
        document_id = result.scalar_one_or_none()
        if document_id is None:
            return None
        return await self._load_document_by_id(document_id)

    async def get_current_document(self, quotation_id: str, lang: str) -> QuotationDocument | None:
        stmt = (
            select(QuotationDocument)
            .where(QuotationDocument.quotation_id == quotation_id)
            .where(QuotationDocument.lang == lang)
            .where(QuotationDocument.is_current.is_(True))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_current_documents(self, quotation_id: str) -> list[QuotationDocument]:
        result = await self.session.scalars(
            select(QuotationDocument)
            .where(QuotationDocument.quotation_id == quotation_id)
            .where(QuotationDocument.is_current.is_(True))
            .order_by(QuotationDocument.lang.asc())
        )
        return list(result.all())

    async def list_document_revisions(
        self,
        quotation_id: str,
        *,
        lang: str,
        limit: int = 20,
    ) -> list[QuotationDocumentRevision]:
        stmt = (
            select(QuotationDocumentRevision)
            .where(QuotationDocumentRevision.quotation_id == quotation_id)
            .where(QuotationDocumentRevision.lang == lang)
            .order_by(QuotationDocumentRevision.revision.desc(), QuotationDocumentRevision.id.desc())
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_document_revision(self, quotation_id: str, *, lang: str, revision: int) -> QuotationDocumentRevision | None:
        return await self.session.scalar(select(QuotationDocumentRevision).where(QuotationDocumentRevision.quotation_id == quotation_id, QuotationDocumentRevision.lang == lang, QuotationDocumentRevision.revision == revision).order_by(QuotationDocumentRevision.id.desc()))

    async def save_current_document(
        self,
        *,
        quotation_id: str,
        lang: str,
        document_json: dict[str, Any],
        expected_revision: int | None = None,
        html_sync: dict[str, Any] | None | object = _UNSET,
        generation_status: dict[str, Any] | None | object = _UNSET,
        next_revision: int | None = None,
    ) -> QuotationDocument:
        quotation = await self.session.get(Quotation, quotation_id)
        if quotation is None:
            raise ValueError(f"Quotation {quotation_id} not found")

        if expected_revision not in (None, 0):
            current = await self._update_current_document_atomic(
                quotation_id=quotation_id,
                lang=lang,
                document_json=document_json,
                expected_revision=expected_revision,
                next_revision=next_revision,
                html_sync=html_sync,
                generation_status=generation_status,
            )
            if current is None:
                await self._raise_document_conflict(
                    quotation_id=quotation_id,
                    lang=lang,
                    expected_revision=expected_revision,
                )
            quotation.current_revision = current.revision
            await self.session.flush()
            return current

        current = await self.get_current_document(quotation_id, lang)
        if current is None:
            if expected_revision not in (None, 0):
                await self._raise_document_conflict(
                    quotation_id=quotation_id,
                    lang=lang,
                    expected_revision=expected_revision,
                )
            revision = next_revision if next_revision is not None else 1
            current = QuotationDocument(
                quotation_id=quotation_id,
                lang=lang,
                revision=revision,
                document_json=document_json,
                html_sync=None if html_sync is _UNSET else html_sync,
                generation_status=None if generation_status is _UNSET else generation_status,
                is_current=True,
            )
            self.session.add(current)
        else:
            if expected_revision == 0:
                await self._raise_document_conflict(
                    quotation_id=quotation_id,
                    lang=lang,
                    expected_revision=expected_revision,
                )
            current = await self._update_current_document_atomic(
                quotation_id=quotation_id,
                lang=lang,
                document_json=document_json,
                expected_revision=None,
                next_revision=next_revision,
                html_sync=html_sync,
                generation_status=generation_status,
            )
            if current is None:
                raise RuntimeError(f"Failed to update current document for {quotation_id}/{lang}")

        quotation.current_revision = current.revision
        await self.session.flush()
        return current

    async def append_document_revision(
        self,
        *,
        quotation_id: str,
        lang: str,
        revision: int,
        document_json: dict[str, Any],
        change_source: str,
    ) -> QuotationDocumentRevision:
        revision_row = QuotationDocumentRevision(
            quotation_id=quotation_id,
            lang=lang,
            revision=revision,
            document_json=document_json,
            change_source=change_source,
        )
        self.session.add(revision_row)
        await self.session.flush()
        return revision_row


class ContentDraftRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, quotation_id: str, draft_id: str) -> QuotationContentDraft | None:
        row = await self.session.get(QuotationContentDraft, draft_id)
        return row if row is not None and row.quotation_id == quotation_id else None

    async def list(self, quotation_id: str, lang: str) -> list[QuotationContentDraft]:
        result = await self.session.scalars(
            select(QuotationContentDraft).where(
                QuotationContentDraft.quotation_id == quotation_id,
                QuotationContentDraft.lang == lang,
            ).order_by(QuotationContentDraft.created_at.desc())
        )
        return list(result.all())

    async def find_cached(self, *, quotation_id: str, lang: str, scope: str, mode: str, facts_hash: str, prompt_version: str) -> QuotationContentDraft | None:
        return await self.session.scalar(select(QuotationContentDraft).where(
            QuotationContentDraft.quotation_id == quotation_id,
            QuotationContentDraft.lang == lang,
            QuotationContentDraft.scope == scope,
            QuotationContentDraft.generation_mode == mode,
            QuotationContentDraft.facts_hash == facts_hash,
            QuotationContentDraft.prompt_version == prompt_version,
            QuotationContentDraft.status == "draft",
        ).order_by(QuotationContentDraft.created_at.desc()))

    async def create(self, **values: Any) -> QuotationContentDraft:
        draft = QuotationContentDraft(**values)
        self.session.add(draft)
        await self.session.flush()
        return draft

    async def mark_stale(self, quotation_id: str) -> None:
        """Invalidate all candidates after the authoritative Facts change."""
        await self.session.execute(update(QuotationContentDraft).where(
            QuotationContentDraft.quotation_id == quotation_id,
            QuotationContentDraft.status.in_(["draft", "applied"]),
        ).values(status="stale"))
        await self.session.flush()

    async def mark_pending_drafts_stale(self, quotation_id: str) -> None:
        """Invalidate sibling candidates after one candidate changes the document.

        An applied candidate is canonical content, not an unresolved draft.  It
        must remain `applied` across the subsequent Content scopes; otherwise
        each apply would make every earlier scope block Design/Review forever.
        """
        await self.session.execute(update(QuotationContentDraft).where(
            QuotationContentDraft.quotation_id == quotation_id,
            QuotationContentDraft.status == "draft",
        ).values(status="stale"))
        await self.session.flush()
