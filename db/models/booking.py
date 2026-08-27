"""Booking aggregate (15.6): Booking + BookingLine + BusinessCodeCounter — one file, one aggregate.

A Booking is created once a quotation's deposit lands; each ``service_line``
copies into a ``booking_line`` that FREEZES pricing/terms forever (T3/R3) and
carries the LIVE ops fields (status, deadlines, supplier_ref, voucher). See
15.6-booking-operations.md §1.3/§1.4 for the full contract.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from db.types import JSON_VARIANT


class Booking(Base):
    """Aggregate root — 1 booking sống mỗi quotation (chốt #3 of 15.6 §1.3)."""

    __tablename__ = "bookings"
    __table_args__ = (
        Index(
            "uq_bookings_quotation_id_active",
            "quotation_id",
            unique=True,
            postgresql_where=text("status != 'cancelled'"),
            sqlite_where=text("status != 'cancelled'"),
        ),
        Index(
            "uq_bookings_idempotency_key",
            "tenant_id",
            text("coalesce(idempotency_key, '')"),
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, default="capella", server_default="capella", index=True)

    quotation_id: Mapped[str] = mapped_column(ForeignKey("quotations.id", ondelete="RESTRICT"), nullable=False)
    sheet_id: Mapped[str] = mapped_column(ForeignKey("costing_sheets.id", ondelete="RESTRICT"), nullable=False)

    booking_code: Mapped[str] = mapped_column(String(24), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active", server_default="active")

    deposit_received_at: Mapped[date] = mapped_column(Date, nullable=False)
    customer_balance_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    party_label_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    travel_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    travel_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    booking_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True)

    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    lines: Mapped[list["BookingLine"]] = relationship(
        "BookingLine", cascade="all, delete-orphan", order_by="BookingLine.sort_order"
    )


class BookingLine(Base):
    """FROZEN snapshot (T3) + LIVE ops fields — no API ever rewrites the FROZEN half."""

    __tablename__ = "booking_lines"
    __table_args__ = (
        Index("ix_booking_lines_status_request_by", "tenant_id", "status", "request_by_date"),
        Index("ix_booking_lines_booking_sort", "booking_id", "sort_order"),
        Index(
            "uq_booking_lines_source_service_line_active",
            "source_service_line_id",
            unique=True,
            postgresql_where=text("status != 'cancelled'"),
            sqlite_where=text("status != 'cancelled'"),
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, default="capella", server_default="capella", index=True)

    booking_id: Mapped[str] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    source_service_line_id: Mapped[str] = mapped_column(ForeignKey("service_lines.id", ondelete="RESTRICT"), nullable=False)

    # ---------------------------------------------------------------- FROZEN
    supplier_id_snapshot: Mapped[str | None] = mapped_column(String(64), nullable=True)
    supplier_name_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    supplier_contact_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_VARIANT, nullable=True)

    title_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(24), nullable=False)
    service_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    time_basis: Mapped[str] = mapped_column(String(16), nullable=False)
    qty_unit: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    qty_time: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    unit_cost_minor_snapshot: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cost_currency_snapshot: Mapped[str] = mapped_column(String(3), nullable=False)
    fx_rate_ppm_snapshot: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sell_minor_snapshot: Mapped[int] = mapped_column(BigInteger, nullable=False)

    payment_terms_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_VARIANT, nullable=True)
    cancellation_policy_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_VARIANT, nullable=True)

    # ------------------------------------------------------------------ LIVE
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="to_request", server_default="to_request")
    request_by_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    penalty_free_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    deposit_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    balance_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    supplier_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    voucher_ref: Mapped[str | None] = mapped_column(String(24), nullable=True, unique=True)

    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cancel_penalty_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    assignee_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    transition_idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class BusinessCodeCounter(Base):
    """Portable PG/SQLite sequence for ``BK-``/``VC-`` business codes (§1.4)."""

    __tablename__ = "business_code_counters"

    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    code_type: Mapped[str] = mapped_column(String(16), primary_key=True)
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
