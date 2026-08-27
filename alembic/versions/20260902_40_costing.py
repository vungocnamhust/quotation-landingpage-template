"""Costing (15.4, dual-track) — CostingSheet + ServiceLine, one aggregate."""
from alembic import op
import sqlalchemy as sa


revision = "20260902_40"
down_revision = "20260901_39"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "costing_sheets",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="capella"),
        sa.Column("quote_request_id", sa.String(length=64), sa.ForeignKey("quote_requests.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("quotation_id", sa.String(length=64), sa.ForeignKey("quotations.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("markup_rate_bps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rounding_increment_minor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("costing_revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attach_idempotency_key", sa.String(length=64), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("updated_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "quote_request_id IS NOT NULL OR quotation_id IS NOT NULL",
            name="ck_costing_sheets_has_a_parent",
        ),
    )
    op.create_index("ix_costing_sheets_tenant_id", "costing_sheets", ["tenant_id"], unique=False)
    op.create_index(
        "uq_costing_sheets_quotation_id",
        "costing_sheets",
        ["quotation_id"],
        unique=True,
        postgresql_where=sa.text("quotation_id IS NOT NULL"),
        sqlite_where=sa.text("quotation_id IS NOT NULL"),
    )
    op.create_index(
        "uq_costing_sheets_unattached_request_id",
        "costing_sheets",
        ["quote_request_id"],
        unique=True,
        postgresql_where=sa.text("quotation_id IS NULL"),
        sqlite_where=sa.text("quotation_id IS NULL"),
    )

    op.create_table(
        "service_lines",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="capella"),
        sa.Column("sheet_id", sa.String(length=64), sa.ForeignKey("costing_sheets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day_number", sa.Integer(), nullable=True),
        sa.Column("service_date", sa.Date(), nullable=True),
        sa.Column("category", sa.String(length=24), nullable=False),
        sa.Column("subcategory", sa.String(length=48), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("supplier_id", sa.String(length=64), sa.ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("product_id", sa.String(length=64), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("tariff_id", sa.String(length=64), sa.ForeignKey("rates.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("price_line_id", sa.BigInteger(), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("time_basis", sa.String(length=16), nullable=False),
        sa.Column("qty_unit", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("qty_time", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_cost_minor", sa.BigInteger(), nullable=False),
        sa.Column("cost_currency", sa.String(length=3), nullable=False),
        sa.Column("fx_rate_ppm", sa.BigInteger(), nullable=True),
        sa.Column("sell_override_minor", sa.BigInteger(), nullable=True),
        sa.Column("booking_status", sa.String(length=16), nullable=False, server_default="quoted"),
        sa.Column("source", sa.String(length=16), nullable=False, server_default="manual"),
        sa.Column("idempotency_key", sa.String(length=64), nullable=True),
        sa.Column("note", sa.String(length=2000), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("updated_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_service_lines_tenant_id", "service_lines", ["tenant_id"], unique=False)
    op.create_index("ix_service_lines_sheet_day_sort", "service_lines", ["sheet_id", "day_number", "sort_order"], unique=False)
    op.create_index(
        "uq_service_lines_sheet_idempotency_key",
        "service_lines",
        ["sheet_id", sa.text("coalesce(idempotency_key, '')")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_service_lines_sheet_idempotency_key", table_name="service_lines")
    op.drop_index("ix_service_lines_sheet_day_sort", table_name="service_lines")
    op.drop_index("ix_service_lines_tenant_id", table_name="service_lines")
    op.drop_table("service_lines")

    op.drop_index("uq_costing_sheets_unattached_request_id", table_name="costing_sheets")
    op.drop_index("uq_costing_sheets_quotation_id", table_name="costing_sheets")
    op.drop_index("ix_costing_sheets_tenant_id", table_name="costing_sheets")
    op.drop_table("costing_sheets")
