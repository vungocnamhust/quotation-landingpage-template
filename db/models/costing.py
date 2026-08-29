"""Costing aggregate (15.4): CostingSheet + ServiceLine — one file, one aggregate.

A CostingSheet is the dual-track workbench: it anchors to a ``quote_request``
(Costing-First), a ``quotation`` (Brochure-First / attached-from-request), or
both once attached. See 15.4-costing.md §1.3/§1.4 for the full contract.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
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


class CostingSheet(Base):
    """Aggregate root — attach = set quotation_id, never copy lines (chốt #1)."""

    __tablename__ = "costing_sheets"
    __table_args__ = (
        CheckConstraint(
            "quote_request_id IS NOT NULL OR quotation_id IS NOT NULL",
            name="ck_costing_sheets_has_a_parent",
        ),
        Index(
            "uq_costing_sheets_quotation_id",
            "quotation_id",
            unique=True,
            postgresql_where=text("quotation_id IS NOT NULL"),
            sqlite_where=text("quotation_id IS NOT NULL"),
        ),
        Index(
            "uq_costing_sheets_unattached_request_id",
            "quote_request_id",
            unique=True,
            postgresql_where=text("quotation_id IS NULL"),
            sqlite_where=text("quotation_id IS NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, default="capella", server_default="capella", index=True)

    quote_request_id: Mapped[str | None] = mapped_column(ForeignKey("quote_requests.id", ondelete="RESTRICT"), nullable=True)
    quotation_id: Mapped[str | None] = mapped_column(ForeignKey("quotations.id", ondelete="RESTRICT"), nullable=True)

    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    markup_rate_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    rounding_increment_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    costing_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    attach_idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    lines: Mapped[list["ServiceLine"]] = relationship(
        "ServiceLine", cascade="all, delete-orphan", order_by="ServiceLine.day_number, ServiceLine.sort_order"
    )
    applications: Mapped[list["CostingApplication"]] = relationship(
        "CostingApplication", cascade="all, delete-orphan", order_by="CostingApplication.created_at"
    )


class ServiceLine(Base):
    """Manual-first cost/sell line — snapshotted at write time, never joins live (R3)."""

    __tablename__ = "service_lines"
    __table_args__ = (
        Index(
            "uq_service_lines_sheet_idempotency_key",
            "sheet_id",
            text("coalesce(idempotency_key, '')"),
            unique=True,
        ),
        Index("ix_service_lines_sheet_day_sort", "sheet_id", "day_number", "sort_order"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, default="capella", server_default="capella", index=True)

    sheet_id: Mapped[str] = mapped_column(ForeignKey("costing_sheets.id", ondelete="CASCADE"), nullable=False)

    day_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    service_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    category: Mapped[str] = mapped_column(String(24), nullable=False)
    subcategory: Mapped[str | None] = mapped_column(String(48), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    supplier_id: Mapped[str | None] = mapped_column(ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=True)
    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), nullable=True)
    tariff_id: Mapped[str | None] = mapped_column(ForeignKey("rates.id", ondelete="RESTRICT"), nullable=True)
    price_line_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    time_basis: Mapped[str] = mapped_column(String(16), nullable=False)
    qty_unit: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    qty_time: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    unit_cost_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cost_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    fx_rate_ppm: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sell_override_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    booking_status: Mapped[str] = mapped_column(String(16), nullable=False, default="quoted", server_default="quoted")
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual", server_default="manual")
    idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True)

    note: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
