"""Costing application model (15.5) — immutable audit trail of pricing applied to commercial."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class CostingApplication(Base):
    """Append-only audit record created whenever a costing sheet's sell total is applied to a commercial option."""

    __tablename__ = "costing_applications"
    __table_args__ = (
        Index(
            "uq_costing_applications_sheet_idempotency_key",
            "sheet_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
            sqlite_where=text("idempotency_key IS NOT NULL"),
        ),
        Index("ix_costing_applications_quotation_id", "quotation_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="capella", server_default="capella", index=True
    )

    sheet_id: Mapped[str] = mapped_column(ForeignKey("costing_sheets.id", ondelete="RESTRICT"), nullable=False, index=True)
    quotation_id: Mapped[str] = mapped_column(ForeignKey("quotations.id", ondelete="RESTRICT"), nullable=False)

    costing_revision_at_apply: Mapped[int] = mapped_column(Integer, nullable=False)
    facts_revision_after: Mapped[int] = mapped_column(Integer, nullable=False)
    target_option_id: Mapped[str] = mapped_column(String(64), nullable=False)

    sell_total_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    cost_total_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    margin_bps: Mapped[int] = mapped_column(Integer, nullable=False)

    idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
