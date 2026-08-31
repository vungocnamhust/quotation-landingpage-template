from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base
from db.types import JSON_VARIANT


class AiRun(Base):
    """Append-only run log for every AI Platform agent call (15.8 bootstrap §1.3, shared by
    all future agents — 15.7 adds new ``agent_name`` values here, never a new table).

    ``anchor_type``/``anchor_id`` is a soft, polymorphic reference (e.g. ``ingestion_batch`` /
    ``igb_...``) — no FK, since the platform must not depend on any one feature's schema.
    """

    __tablename__ = "ai_runs"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "anchor_type", "anchor_id", "idempotency_key",
            name="uq_ai_runs_anchor_idempotency_key",
        ),
        Index("ix_ai_runs_tenant_agent_created", "tenant_id", "agent_name", "created_at"),
        Index("ix_ai_runs_anchor", "anchor_type", "anchor_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, default="capella", server_default="capella")

    agent_name: Mapped[str] = mapped_column(String(48), nullable=False)
    anchor_type: Mapped[str] = mapped_column(String(24), nullable=False)
    anchor_id: Mapped[str] = mapped_column(String(64), nullable=False)

    status: Mapped[str] = mapped_column(String(16), nullable=False)  # succeeded | partial | failed
    input_ref_json: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict, server_default="{}")
    output_json: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict, server_default="{}")
    stats_json: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict, server_default="{}")
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)

    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
