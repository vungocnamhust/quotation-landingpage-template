"""AP reconciliation aggregate (15.9): SupplierInvoice + lines + payments — one file (§5.1).

Consumer-only: this module never mutates ``bookings``/``booking_lines``/
``costing_*`` — it reads voucher/cost snapshots and reconciles them against
supplier invoices in a parallel actuals ledger (Option B, §1.1).
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
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


class SupplierInvoice(Base):
    """Aggregate root — CAS via ``invoice_revision`` (§5.3, §8)."""

    __tablename__ = "supplier_invoices"
    __table_args__ = (
        Index(
            "uq_supplier_invoices_supplier_number",
            "tenant_id",
            "supplier_id",
            "invoice_number",
            unique=True,
            postgresql_where=text("invoice_number IS NOT NULL"),
            sqlite_where=text("invoice_number IS NOT NULL"),
        ),
        Index(
            "uq_supplier_invoices_idempotency_key",
            "tenant_id",
            text("coalesce(idempotency_key, '')"),
            unique=True,
        ),
        Index("ix_supplier_invoices_status_due", "tenant_id", "status", "due_date"),
        Index("ix_supplier_invoices_supplier_date", "supplier_id", "invoice_date"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, default="capella", server_default="capella", index=True)

    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False)
    invoice_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    gross_total_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tax_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft", server_default="draft")
    invoice_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    file_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    lines: Mapped[list["SupplierInvoiceLine"]] = relationship(
        "SupplierInvoiceLine", cascade="all, delete-orphan", order_by="SupplierInvoiceLine.sort_order"
    )
    allocations: Mapped[list["ApPaymentAllocation"]] = relationship(
        "ApPaymentAllocation", cascade="all, delete-orphan", order_by="ApPaymentAllocation.created_at"
    )


class SupplierInvoiceLine(Base):
    """Match unit — one voucher/booking_line at a time (§5.3)."""

    __tablename__ = "supplier_invoice_lines"
    __table_args__ = (
        Index(
            "uq_supplier_invoice_lines_booking_line_active",
            "booking_line_id",
            unique=True,
            postgresql_where=text("match_status IN ('auto_matched', 'manual_matched')"),
            sqlite_where=text("match_status IN ('auto_matched', 'manual_matched')"),
        ),
        Index("ix_supplier_invoice_lines_invoice_sort", "invoice_id", "sort_order"),
        Index("ix_supplier_invoice_lines_voucher_ref", "voucher_ref"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK_VARIANT, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, default="capella", server_default="capella", index=True)

    invoice_id: Mapped[str] = mapped_column(ForeignKey("supplier_invoices.id", ondelete="CASCADE"), nullable=False)
    line_type: Mapped[str] = mapped_column(String(16), nullable=False, default="service", server_default="service")

    booking_id: Mapped[str | None] = mapped_column(ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=True)
    booking_line_id: Mapped[str | None] = mapped_column(ForeignKey("booking_lines.id", ondelete="RESTRICT"), nullable=True)
    voucher_ref: Mapped[str | None] = mapped_column(String(24), nullable=True)

    description: Mapped[str] = mapped_column(String(500), nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    expected_cost_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    variance_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    match_status: Mapped[str] = mapped_column(String(16), nullable=False, default="unmatched", server_default="unmatched")
    match_issues_json: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list, server_default="[]")
    match_note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ApPayment(Base):
    """Append-only — a wrong payment is reversed with a negative-amount row (§5.3, chốt #9)."""

    __tablename__ = "ap_payments"
    __table_args__ = (
        Index(
            "uq_ap_payments_idempotency_key",
            "tenant_id",
            text("coalesce(idempotency_key, '')"),
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, default="capella", server_default="capella", index=True)

    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False)
    payment_code: Mapped[str] = mapped_column(String(24), nullable=False, unique=True)

    paid_at: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    fx_rate_ppm: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    method: Mapped[str] = mapped_column(String(16), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    allocations: Mapped[list["ApPaymentAllocation"]] = relationship(
        "ApPaymentAllocation", cascade="all, delete-orphan", order_by="ApPaymentAllocation.created_at"
    )


class ApPaymentAllocation(Base):
    """Append-only — 2 allocations for the same (payment, invoice) pair are legal (§5.3)."""

    __tablename__ = "ap_payment_allocations"
    __table_args__ = (
        Index("ix_ap_payment_allocations_payment", "payment_id"),
        Index("ix_ap_payment_allocations_invoice", "invoice_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK_VARIANT, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, default="capella", server_default="capella", index=True)

    payment_id: Mapped[str] = mapped_column(ForeignKey("ap_payments.id", ondelete="CASCADE"), nullable=False)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("supplier_invoices.id", ondelete="RESTRICT"), nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
