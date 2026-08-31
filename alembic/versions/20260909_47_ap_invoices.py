"""AP reconciliation (15.9) — supplier_invoices, supplier_invoice_lines, ap_payments, ap_payment_allocations."""
from alembic import op
import sqlalchemy as sa


revision = "20260909_47"
down_revision = "20260908_46"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "supplier_invoices",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="capella"),
        sa.Column("supplier_id", sa.String(length=64), sa.ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("invoice_number", sa.String(length=64), nullable=True),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("gross_total_minor", sa.BigInteger(), nullable=False),
        sa.Column("tax_minor", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("invoice_revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("file_ref", sa.String(length=255), nullable=True),
        sa.Column("idempotency_key", sa.String(length=64), nullable=True),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("updated_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_supplier_invoices_tenant_id", "supplier_invoices", ["tenant_id"], unique=False)
    op.create_index("ix_supplier_invoices_status_due", "supplier_invoices", ["tenant_id", "status", "due_date"], unique=False)
    op.create_index("ix_supplier_invoices_supplier_date", "supplier_invoices", ["supplier_id", "invoice_date"], unique=False)
    op.create_index(
        "uq_supplier_invoices_supplier_number",
        "supplier_invoices",
        ["tenant_id", "supplier_id", "invoice_number"],
        unique=True,
        postgresql_where=sa.text("invoice_number IS NOT NULL"),
        sqlite_where=sa.text("invoice_number IS NOT NULL"),
    )
    op.create_index(
        "uq_supplier_invoices_idempotency_key",
        "supplier_invoices",
        ["tenant_id", sa.text("coalesce(idempotency_key, '')")],
        unique=True,
    )

    op.create_table(
        "supplier_invoice_lines",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="capella"),
        sa.Column("invoice_id", sa.String(length=64), sa.ForeignKey("supplier_invoices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("line_type", sa.String(length=16), nullable=False, server_default="service"),
        sa.Column("booking_id", sa.String(length=64), sa.ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("booking_line_id", sa.String(length=64), sa.ForeignKey("booking_lines.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("voucher_ref", sa.String(length=24), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("expected_cost_minor", sa.BigInteger(), nullable=True),
        sa.Column("variance_minor", sa.BigInteger(), nullable=True),
        sa.Column("match_status", sa.String(length=16), nullable=False, server_default="unmatched"),
        sa.Column("match_issues_json", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("match_note", sa.String(length=500), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("updated_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_supplier_invoice_lines_tenant_id", "supplier_invoice_lines", ["tenant_id"], unique=False)
    op.create_index("ix_supplier_invoice_lines_invoice_sort", "supplier_invoice_lines", ["invoice_id", "sort_order"], unique=False)
    op.create_index("ix_supplier_invoice_lines_voucher_ref", "supplier_invoice_lines", ["voucher_ref"], unique=False)
    op.create_index(
        "uq_supplier_invoice_lines_booking_line_active",
        "supplier_invoice_lines",
        ["booking_line_id"],
        unique=True,
        postgresql_where=sa.text("match_status IN ('auto_matched', 'manual_matched')"),
        sqlite_where=sa.text("match_status IN ('auto_matched', 'manual_matched')"),
    )

    op.create_table(
        "ap_payments",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="capella"),
        sa.Column("supplier_id", sa.String(length=64), sa.ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("payment_code", sa.String(length=24), nullable=False, unique=True),
        sa.Column("paid_at", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("fx_rate_ppm", sa.BigInteger(), nullable=True),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("reference", sa.String(length=128), nullable=True),
        sa.Column("idempotency_key", sa.String(length=64), nullable=True),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ap_payments_tenant_id", "ap_payments", ["tenant_id"], unique=False)
    op.create_index(
        "uq_ap_payments_idempotency_key",
        "ap_payments",
        ["tenant_id", sa.text("coalesce(idempotency_key, '')")],
        unique=True,
    )

    op.create_table(
        "ap_payment_allocations",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="capella"),
        sa.Column("payment_id", sa.String(length=64), sa.ForeignKey("ap_payments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_id", sa.String(length=64), sa.ForeignKey("supplier_invoices.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ap_payment_allocations_tenant_id", "ap_payment_allocations", ["tenant_id"], unique=False)
    op.create_index("ix_ap_payment_allocations_payment", "ap_payment_allocations", ["payment_id"], unique=False)
    op.create_index("ix_ap_payment_allocations_invoice", "ap_payment_allocations", ["invoice_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ap_payment_allocations_invoice", table_name="ap_payment_allocations")
    op.drop_index("ix_ap_payment_allocations_payment", table_name="ap_payment_allocations")
    op.drop_index("ix_ap_payment_allocations_tenant_id", table_name="ap_payment_allocations")
    op.drop_table("ap_payment_allocations")

    op.drop_index("uq_ap_payments_idempotency_key", table_name="ap_payments")
    op.drop_index("ix_ap_payments_tenant_id", table_name="ap_payments")
    op.drop_table("ap_payments")

    op.drop_index("uq_supplier_invoice_lines_booking_line_active", table_name="supplier_invoice_lines")
    op.drop_index("ix_supplier_invoice_lines_voucher_ref", table_name="supplier_invoice_lines")
    op.drop_index("ix_supplier_invoice_lines_invoice_sort", table_name="supplier_invoice_lines")
    op.drop_index("ix_supplier_invoice_lines_tenant_id", table_name="supplier_invoice_lines")
    op.drop_table("supplier_invoice_lines")

    op.drop_index("uq_supplier_invoices_idempotency_key", table_name="supplier_invoices")
    op.drop_index("uq_supplier_invoices_supplier_number", table_name="supplier_invoices")
    op.drop_index("ix_supplier_invoices_supplier_date", table_name="supplier_invoices")
    op.drop_index("ix_supplier_invoices_status_due", table_name="supplier_invoices")
    op.drop_index("ix_supplier_invoices_tenant_id", table_name="supplier_invoices")
    op.drop_table("supplier_invoices")
