from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base
from db.types import JSON_VARIANT


class Supplier(Base):
    """Creditor-side supplier registry (DMC, hotel, wholesaler, ...).

    Mirrors ``PartnerProfile`` in shape but never shares a table or FK with
    it — a partner is a debtor (source of guests, money flows in), a
    supplier is a creditor (money flows out). See 15.1-supplier-registry.md.
    """

    __tablename__ = "suppliers"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name_normalized", name="uq_suppliers_tenant_name_normalized"),
        Index("ix_suppliers_active_name", "is_active", "name"),
        Index("ix_suppliers_tenant_type", "tenant_id", "supplier_type"),
        Index("ix_suppliers_destination_id", "destination_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, default="capella", server_default="capella", index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_normalized: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    supplier_type: Mapped[str] = mapped_column(String(24), nullable=False)

    country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    city: Mapped[str | None] = mapped_column(String(64), nullable=True)
    destination_id: Mapped[str | None] = mapped_column(
        ForeignKey("destination_catalog.id", ondelete="RESTRICT"), nullable=True
    )

    default_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    preferred_status: Mapped[str] = mapped_column(String(16), nullable=False, default="standard", server_default="standard")
    quality_tier: Mapped[str | None] = mapped_column(String(16), nullable=True)

    contact_json: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict, server_default="{}")
    payment_terms_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_VARIANT, nullable=True)
    cancellation_policy_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_VARIANT, nullable=True)
    child_policy_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_VARIANT, nullable=True)

    bank_details_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tax_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    credit_terms_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    internal_notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
