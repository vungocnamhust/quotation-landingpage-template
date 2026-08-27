"""Server-owned, fail-closed Fast Track assembly orchestration."""
from __future__ import annotations

import copy
from collections.abc import Awaitable, Callable
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from repositories import QuotationDocumentRepository, QuotationRepository
from repositories.errors import DocumentRevisionConflictError
from services.content_action_application_service import ContentActionApplicationService


class FastTrackReviewBlockedError(ValueError):
    def __init__(self, review: dict[str, Any]) -> None:
        super().__init__("Fast Track assembly is incomplete; resolve the reported blockers before opening Design.")
        self.review = review


class FastTrackAssemblyService:
    """Coordinates media, bypass actions, and canonical readiness without UI policy."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.documents = QuotationDocumentRepository(session)
        self.quotations = QuotationRepository(session)

    async def assemble(
        self,
        *,
        quotation_id: str,
        lang: str,
        base_revision: int,
        writing_style: Literal["storytelling", "detailed"],
        profile_id: str | None,
        correlation_id: str,
        idempotency_key: str,
        apply_media_defaults: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
        normalize_document: Callable[[dict[str, Any], int], dict[str, Any]],
        review_status: Callable[[], Awaitable[dict[str, Any]]],
    ) -> dict[str, Any]:
        quotation = await self.quotations.get_quotation_by_id(quotation_id)
        current = await self.documents.get_current_document(quotation_id, lang)
        if quotation is None or current is None:
            raise ValueError("Quotation or canonical document was not found.")
        if current.revision != base_revision:
            raise DocumentRevisionConflictError(quotation_id=quotation_id, lang=lang, expected_revision=base_revision, current_revision=current.revision, current_document=current.document_json)

        next_document = copy.deepcopy(current.document_json)
        media = await apply_media_defaults(next_document)
        current_revision = current.revision
        document_overlay = normalize_document(next_document, current_revision) if media.get("hasChanges") else None

        actions_service = ContentActionApplicationService(self.session)
        plan, actions = await actions_service.list(quotation_id)
        bypass_ids = [action.id for action in actions if action.automation_policy == "bypass" and action.state in {"pending", "accepted"}]
        if bypass_ids:
            await actions_service.accept(quotation_id=quotation_id, note="Accepted by explicit Fast Track assembly.", profile_id=profile_id, correlation_id=correlation_id)
            _drafts, current_revision = await actions_service.generate_and_apply(
                quotation_id=quotation_id, plan_id=plan.id, action_ids=bypass_ids,
                expected_revision=current_revision, writing_style=writing_style, profile_id=profile_id,
                correlation_id=correlation_id, idempotency_key=idempotency_key, document_overlay=document_overlay,
            )
        elif document_overlay is not None:
            saved = await self.documents.save_current_document(
                quotation_id=quotation_id, lang=lang, document_json=document_overlay, expected_revision=current_revision,
            )
            document_overlay.setdefault("meta", {})["revision"] = saved.revision
            await self.documents.append_document_revision(
                quotation_id=quotation_id, lang=lang, revision=saved.revision,
                document_json=document_overlay, change_source="fast_track_media_defaults",
            )
            await self.session.commit()
            current_revision = saved.revision

        review = await review_status()
        if not review.get("ready"):
            raise FastTrackReviewBlockedError(review)
        return {"status": "complete", "quotationId": quotation_id, "currentRevision": int(review["currentRevision"]), "review": review}
