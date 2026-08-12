from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Select, and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db.models.quotation import Quotation, QuotationContentDraft, QuotationDocument, QuotationDocumentRevision, QuotationRequest
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
            customer_name=customer_name,
            title=title,
        )
        self.session.add(quotation)
        await self.session.flush()
        return quotation

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
