from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, false, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base
from db.types import BIGINT_PK_VARIANT, JSON_VARIANT


class Quotation(Base):
    __tablename__ = "quotations"
    __table_args__ = (
        Index("ix_quotations_opportunity_id", "opportunity_id"),
        Index("ix_quotations_status_updated_at", "status", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    opportunity_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="manual", server_default="manual")
    source_snapshot_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    brand_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", server_default="draft")
    baseline_lang: Mapped[str] = mapped_column(String(5), nullable=False, default="en", server_default="en")
    current_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    # Business-versioning is deliberately distinct from ``current_version``:
    # the latter is the immutable public publication-release number.
    quotation_family_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    business_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parent_quotation_id: Mapped[str | None] = mapped_column(
        ForeignKey("quotations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_request_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    template_name: Mapped[str] = mapped_column(String(255), nullable=False)
    designer_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("travel_designer_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("travel_designer_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class QuotationRequest(Base):
    __tablename__ = "quotation_requests"

    id: Mapped[int] = mapped_column(BIGINT_PK_VARIANT, primary_key=True, autoincrement=True)
    quotation_id: Mapped[str] = mapped_column(
        ForeignKey("quotations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    request_json: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class QuotationDocument(Base):
    __tablename__ = "quotation_documents"
    __table_args__ = (
        UniqueConstraint("quotation_id", "lang", name="uq_quotation_documents_quotation_lang"),
        Index("ix_quotation_documents_quotation_lang_current", "quotation_id", "lang", "is_current"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK_VARIANT, primary_key=True, autoincrement=True)
    quotation_id: Mapped[str] = mapped_column(
        ForeignKey("quotations.id", ondelete="CASCADE"),
        nullable=False,
    )
    lang: Mapped[str] = mapped_column(String(5), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    document_json: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False)
    html_sync: Mapped[dict[str, Any] | None] = mapped_column(JSON_VARIANT, nullable=True)
    generation_status: Mapped[dict[str, Any] | None] = mapped_column(JSON_VARIANT, nullable=True)
    is_current: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class QuotationDocumentRevision(Base):
    __tablename__ = "quotation_document_revisions"
    __table_args__ = (
        Index("ix_quotation_document_revisions_quotation_lang_revision", "quotation_id", "lang", "revision"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK_VARIANT, primary_key=True, autoincrement=True)
    quotation_id: Mapped[str] = mapped_column(
        ForeignKey("quotations.id", ondelete="CASCADE"),
        nullable=False,
    )
    lang: Mapped[str] = mapped_column(String(5), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    document_json: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False)
    change_source: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class QuotationContentDraft(Base):
    __tablename__ = "quotation_content_drafts"
    __table_args__ = (
        Index("ix_quotation_content_drafts_quotation_lang_created", "quotation_id", "lang", "created_at"),
        Index("ix_quotation_content_drafts_cache", "quotation_id", "lang", "scope", "generation_mode", "facts_hash"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    quotation_id: Mapped[str] = mapped_column(ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False)
    lang: Mapped[str] = mapped_column(String(5), nullable=False)
    scope: Mapped[str] = mapped_column(String(128), nullable=False)
    generation_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", server_default="draft")
    facts_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_document_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    facts_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False)
    candidate_json: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False)
    missing_inputs: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False)
    generation_metadata: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class QuotationVersionFacts(Base):
    """The authoritative current Facts snapshot for a new-model draft version."""

    __tablename__ = "quotation_version_facts"
    __table_args__ = (UniqueConstraint("quotation_id", name="uq_quotation_version_facts_quotation"),)

    id: Mapped[int] = mapped_column(BIGINT_PK_VARIANT, primary_key=True, autoincrement=True)
    quotation_id: Mapped[str] = mapped_column(ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False)
    canonical_facts_json: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False)
    resolved_facts_json: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False)
    facts_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_request_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class QuotationVersionImpact(Base):
    """A required, auditable review created while carrying a version forward."""

    __tablename__ = "quotation_version_impacts"
    __table_args__ = (
        Index("ix_quotation_version_impacts_quotation_status", "quotation_id", "status"),
        UniqueConstraint("quotation_id", "stage", "scope", "source_path", name="uq_quotation_version_impact_target"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK_VARIANT, primary_key=True, autoincrement=True)
    quotation_id: Mapped[str] = mapped_column(ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False)
    stage: Mapped[str] = mapped_column(String(16), nullable=False)
    scope: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    source_path: Mapped[str] = mapped_column(String(255), nullable=False)
    target_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    explanation: Mapped[str] = mapped_column(String(1000), nullable=False)
    entity_key: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    operation: Mapped[str] = mapped_column(String(32), nullable=False, default="changed", server_default="changed")
    old_value_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_VARIANT, nullable=True)
    new_value_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_VARIANT, nullable=True)
    generation_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    generation_selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    generation_status: Mapped[str] = mapped_column(String(24), nullable=False, default="not_requested", server_default="not_requested")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", server_default="pending")
    resolution_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    resolved_by_profile_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class QuotationVersionImpactTarget(Base):
    """An executable/document-level target belonging to one Fact change.

    The parent impact is the immutable audit of *what* changed; targets describe
    the precise output that may be rebuilt, reviewed, or selectively generated.
    """

    __tablename__ = "quotation_version_impact_targets"
    __table_args__ = (
        Index("ix_quotation_version_impact_targets_quotation_status", "quotation_id", "execution_status"),
        UniqueConstraint("impact_id", "stage", "scope", "target_path", name="uq_quotation_version_impact_target_path"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK_VARIANT, primary_key=True, autoincrement=True)
    impact_id: Mapped[int] = mapped_column(ForeignKey("quotation_version_impacts.id", ondelete="CASCADE"), nullable=False)
    quotation_id: Mapped[str] = mapped_column(ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False)
    stage: Mapped[str] = mapped_column(String(16), nullable=False)
    scope: Mapped[str] = mapped_column(String(128), nullable=False)
    target_path: Mapped[str] = mapped_column(String(255), nullable=False)
    treatment: Mapped[str] = mapped_column(String(32), nullable=False)
    affected_fields_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    deep_link_json: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict)
    generation_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    generation_selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    execution_status: Mapped[str] = mapped_column(String(24), nullable=False, default="not_requested", server_default="not_requested")
    draft_id: Mapped[str | None] = mapped_column(ForeignKey("quotation_content_drafts.id", ondelete="SET NULL"), nullable=True)
    accepted_by_profile_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())




class QuotationVersionImpactAcceptance(Base):
    __tablename__ = "quotation_version_impact_acceptances"
    __table_args__ = (UniqueConstraint("quotation_id", "idempotency_key", name="uq_quotation_impact_acceptance_idempotency"),)

    id: Mapped[int] = mapped_column(BIGINT_PK_VARIANT, primary_key=True, autoincrement=True)
    quotation_id: Mapped[str] = mapped_column(ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    selected_target_ids_json: Mapped[list[int]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    resolution_note: Mapped[str] = mapped_column(String(1000), nullable=False)
    accepted_by_profile_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class QuotationContentActionPlan(Base):
    """Execution plan for Content-only successor remediation.

    This intentionally does not replace historical impact rows.  It is the
    clean persistence boundary for newly created actionable plans from the
    migration-34 baseline onward.
    """

    __tablename__ = "quotation_content_action_plans"
    __table_args__ = (
        UniqueConstraint("quotation_id", "plan_hash", name="uq_quotation_content_action_plan_hash"),
        Index("ix_quotation_content_action_plans_quotation_status", "quotation_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    quotation_id: Mapped[str] = mapped_column(ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False)
    predecessor_quotation_id: Mapped[str | None] = mapped_column(ForeignKey("quotations.id", ondelete="SET NULL"), nullable=True)
    facts_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    plan_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", server_default="pending")
    accepted_by_profile_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acceptance_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class QuotationContentAction(Base):
    """One auditable Content execution unit belonging to an action plan."""

    __tablename__ = "quotation_content_actions"
    __table_args__ = (
        UniqueConstraint("plan_id", "action_key", name="uq_quotation_content_action_plan_key"),
        Index("ix_quotation_content_actions_quotation_state", "quotation_id", "state"),
        Index("ix_quotation_content_actions_plan_policy", "plan_id", "automation_policy"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("quotation_content_action_plans.id", ondelete="CASCADE"), nullable=False)
    quotation_id: Mapped[str] = mapped_column(ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False)
    action_key: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_key: Mapped[str] = mapped_column(String(255), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    automation_policy: Mapped[str] = mapped_column(String(16), nullable=False)
    state: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", server_default="pending")
    input_facts_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    predecessor_quotation_id: Mapped[str | None] = mapped_column(ForeignKey("quotations.id", ondelete="SET NULL"), nullable=True)
    inherited_reference_status: Mapped[str] = mapped_column(String(24), nullable=False, default="unavailable", server_default="unavailable")
    action_metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict)
    draft_id: Mapped[str | None] = mapped_column(ForeignKey("quotation_content_drafts.id", ondelete="SET NULL"), nullable=True)
    applied_document_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    executed_by_profile_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
