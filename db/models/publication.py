from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base
from db.types import BIGINT_PK_VARIANT, JSON_VARIANT


class QuotationPublication(Base):
    __tablename__ = "quotation_publications"
    __table_args__ = (
        UniqueConstraint("quotation_id", "version", "lang", name="uq_quotation_publications_quotation_version_lang"),
        Index("ix_quotation_publications_quotation_version", "quotation_id", "version"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK_VARIANT, primary_key=True, autoincrement=True)
    quotation_id: Mapped[str] = mapped_column(
        ForeignKey("quotations.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    lang: Mapped[str] = mapped_column(String(5), nullable=False)
    html_r2_key: Mapped[str] = mapped_column(String(512), nullable=False)
    pdf_r2_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    published_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    document_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="published", server_default="published")
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    restored_from_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class PublicationTarget(Base):
    """Stable branded public URL for one quotation and locale."""

    __tablename__ = "publication_targets"
    __table_args__ = (
        UniqueConstraint("brand_id", "locale", "public_slug", name="uq_publication_targets_brand_locale_slug"),
        UniqueConstraint("quotation_id", "brand_id", "locale", name="uq_publication_targets_quotation_brand_locale"),
        Index("ix_publication_targets_quotation", "quotation_id"),
        CheckConstraint("status IN ('draft', 'published', 'unpublished')", name="ck_publication_targets_status"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    quotation_id: Mapped[str] = mapped_column(ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False)
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id", ondelete="RESTRICT"), nullable=False)
    locale: Mapped[str] = mapped_column(String(5), nullable=False)
    public_slug: Mapped[str] = mapped_column(String(128), nullable=False)
    # Unlike ``public_slug`` (which is scoped to a brand and locale), this
    # token is globally unique and backs the public fallback hostname.
    fallback_slug: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", server_default="draft")
    active_release_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class PublicationRelease(Base):
    """Immutable render snapshot. HTML is deliberately never persisted here."""

    __tablename__ = "publication_releases"
    __table_args__ = (
        UniqueConstraint("target_id", "release_number", name="uq_publication_releases_target_number"),
        Index("ix_publication_releases_target_current", "target_id", "is_current"),
        CheckConstraint("status IN ('staging', 'published', 'superseded', 'failed')", name="ck_publication_releases_status"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    target_id: Mapped[str] = mapped_column(ForeignKey("publication_targets.id", ondelete="CASCADE"), nullable=False)
    release_number: Mapped[int] = mapped_column(Integer, nullable=False)
    document_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    source_base_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    render_profile_snapshot: Mapped[dict] = mapped_column(JSON_VARIANT, nullable=False)
    asset_manifest: Mapped[dict] = mapped_column(JSON_VARIANT, nullable=False, default=dict)
    pdf_r2_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="staging", server_default="staging")
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PublicationJob(Base):
    """Durable work queue for V2 publication side effects.

    Jobs live with their release so a process restart cannot silently lose a
    PDF render or cache invalidation.
    """

    __tablename__ = "publication_jobs"
    __table_args__ = (
        UniqueConstraint("release_id", "job_type", "event_key", name="uq_publication_jobs_release_type_event"),
        Index("ix_publication_jobs_claim", "status", "next_run_at", "created_at"),
        CheckConstraint("job_type IN ('render_pdf', 'purge_cache')", name="ck_publication_jobs_type"),
        CheckConstraint("status IN ('queued', 'running', 'succeeded', 'failed')", name="ck_publication_jobs_status"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    release_id: Mapped[str] = mapped_column(ForeignKey("publication_releases.id", ondelete="CASCADE"), nullable=False)
    job_type: Mapped[str] = mapped_column(String(32), nullable=False)
    event_key: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", server_default="queued")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text(), nullable=True)
    artifact_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON_VARIANT, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
