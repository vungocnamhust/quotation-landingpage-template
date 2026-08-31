from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base
from db.types import JSON_VARIANT


class IngestionBatch(Base):
    """Staging area for the Interactive Ingestion Co-Pilot (15.8 §1.4) — the ONLY table any
    AI agent in this feature is allowed to write. ``commit_service`` is the sole place that
    replays a batch's content into the real catalog tables (suppliers/products/rates).
    """

    __tablename__ = "ingestion_batches"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_ingestion_batches_tenant_idempotency_key"),
        Index("ix_ingestion_batches_tenant_status_created", "tenant_id", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, default="capella", server_default="capella")

    # draft -> needs_clarification -> ready -> committed | rejected | archived
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft", server_default="draft")

    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_channel: Mapped[str] = mapped_column(String(16), nullable=False)
    source_document_type: Mapped[str] = mapped_column(String(24), nullable=False)

    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict, server_default="{}")
    resolution_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_VARIANT, nullable=True)
    conversation_json: Mapped[list[Any]] = mapped_column(JSON_VARIANT, nullable=False, default=list, server_default="[]")
    operator_edits_json: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict, server_default="{}")
    commit_result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_VARIANT, nullable=True)
    error_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_VARIANT, nullable=True)

    batch_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)

    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
