"""Rate aggregate (15.3): Rate + RatePriceLine + RateSource — one file, one aggregate.

Rate == commercial validity of a product's NET cost (E3, immutable-by-supersede).
Rate carries no destination/origin column by design — geography is inherited
from the product it hangs off (15.2 + 15.2b §3.4). See 15.3-rates.md.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from db.types import BIGINT_PK_VARIANT, JSON_VARIANT


class Rate(Base):
    """Rate header — NET cost validity for one product, one currency (chốt #1/#2)."""

    __tablename__ = "rates"
    __table_args__ = (
        CheckConstraint("valid_to >= valid_from", name="ck_rates_valid_to_after_from"),
        Index("ix_rates_product_status_validity", "product_id", "lifecycle_status", "valid_from", "valid_to"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, default="capella", server_default="capella", index=True)

    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)

    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate_basis: Mapped[str] = mapped_column(String(24), nullable=False)
    commission_pct: Mapped[int | None] = mapped_column(Integer, nullable=True)

    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date] = mapped_column(Date, nullable=False)
    season_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    blackout_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON_VARIANT, nullable=False, default=list, server_default="[]")

    min_pax: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_pax: Mapped[int | None] = mapped_column(Integer, nullable=True)

    tax_included: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    tax_pct: Mapped[int | None] = mapped_column(Integer, nullable=True)

    supplements_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON_VARIANT, nullable=False, default=list, server_default="[]")
    inclusions_json: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list, server_default="[]")
    exclusions_json: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list, server_default="[]")

    payment_terms_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_VARIANT, nullable=True)
    cancellation_policy_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_VARIANT, nullable=True)
    child_policy_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_VARIANT, nullable=True)

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    supersedes_rate_id: Mapped[str | None] = mapped_column(ForeignKey("rates.id", ondelete="RESTRICT"), nullable=True)
    lifecycle_status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft", server_default="draft")
    review_status: Mapped[str] = mapped_column(String(16), nullable=False, default="verified", server_default="verified")
    validation_flags_json: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list, server_default="[]")

    source_id: Mapped[str | None] = mapped_column(ForeignKey("rate_sources.id", ondelete="RESTRICT"), nullable=True)
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    lines: Mapped[list["RatePriceLine"]] = relationship(
        "RatePriceLine", cascade="all, delete-orphan", order_by="RatePriceLine.sort_order"
    )


class RatePriceLine(Base):
    """Append-only child of a rate — exactly one amount per line (chốt #3)."""

    __tablename__ = "rate_price_lines"
    __table_args__ = (
        Index(
            "uq_rate_price_lines_rate_combo",
            "rate_id",
            "price_for",
            "occupancy_basis",
            "unit",
            text("coalesce(tier_min_pax, -1)"),
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK_VARIANT, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, default="capella", server_default="capella", index=True)

    rate_id: Mapped[str] = mapped_column(ForeignKey("rates.id", ondelete="CASCADE"), nullable=False)

    price_for: Mapped[str] = mapped_column(String(16), nullable=False)
    occupancy_basis: Mapped[str] = mapped_column(String(8), nullable=False, default="na", server_default="na")
    unit: Mapped[str] = mapped_column(String(32), nullable=False)

    tier_min_pax: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tier_max_pax: Mapped[int | None] = mapped_column(Integer, nullable=True)

    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)

    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class RateSource(Base):
    """Slim provenance record — "where did this price come from" (chốt #7)."""

    __tablename__ = "rate_sources"
    __table_args__ = (Index("ix_rate_sources_supplier_id", "supplier_id"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, default="capella", server_default="capella", index=True)

    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(24), nullable=False)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    file_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)

    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
