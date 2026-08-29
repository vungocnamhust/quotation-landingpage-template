"""Costing applications (15.5) — immutable pricing application audit log."""
from alembic import op
import sqlalchemy as sa


revision = "20260903_41"
down_revision = "20260902_40"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "costing_applications",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="capella"),
        sa.Column("sheet_id", sa.String(length=64), sa.ForeignKey("costing_sheets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quotation_id", sa.String(length=64), sa.ForeignKey("quotations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("costing_revision_at_apply", sa.Integer(), nullable=False),
        sa.Column("facts_revision_after", sa.Integer(), nullable=False),
        sa.Column("target_option_id", sa.String(length=64), nullable=False),
        sa.Column("sell_total_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("cost_total_minor", sa.BigInteger(), nullable=False),
        sa.Column("margin_bps", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_costing_applications_tenant_id", "costing_applications", ["tenant_id"], unique=False)
    op.create_index("ix_costing_applications_sheet_id", "costing_applications", ["sheet_id"], unique=False)
    op.create_index("ix_costing_applications_quotation_id", "costing_applications", ["quotation_id"], unique=False)
    op.create_index(
        "uq_costing_applications_sheet_idempotency_key",
        "costing_applications",
        ["sheet_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
        sqlite_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_table("costing_applications")
