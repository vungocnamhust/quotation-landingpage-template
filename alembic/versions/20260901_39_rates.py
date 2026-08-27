"""Rates (15.3) — supplier NET pricing, immutable-by-supersede, one aggregate."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260901_39"
down_revision = "20260830_38"
branch_labels = None
depends_on = None

_JSON_VARIANT = sa.JSON().with_variant(JSONB(astext_type=sa.Text()), "postgresql")
_BIGINT_PK_VARIANT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "rate_sources",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="capella"),
        sa.Column("supplier_id", sa.String(length=64), sa.ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("document_type", sa.String(length=24), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("file_ref", sa.String(length=255), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("updated_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_rate_sources_supplier_id", "rate_sources", ["supplier_id"], unique=False)
    op.create_index("ix_rate_sources_tenant_id", "rate_sources", ["tenant_id"], unique=False)

    op.create_table(
        "rates",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="capella"),
        sa.Column("product_id", sa.String(length=64), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("rate_basis", sa.String(length=24), nullable=False),
        sa.Column("commission_pct", sa.Integer(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=False),
        sa.Column("season_name", sa.String(length=120), nullable=True),
        sa.Column("blackout_json", _JSON_VARIANT, nullable=False, server_default="[]"),
        sa.Column("min_pax", sa.Integer(), nullable=True),
        sa.Column("max_pax", sa.Integer(), nullable=True),
        sa.Column("tax_included", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("tax_pct", sa.Integer(), nullable=True),
        sa.Column("supplements_json", _JSON_VARIANT, nullable=False, server_default="[]"),
        sa.Column("inclusions_json", _JSON_VARIANT, nullable=False, server_default="[]"),
        sa.Column("exclusions_json", _JSON_VARIANT, nullable=False, server_default="[]"),
        sa.Column("payment_terms_json", _JSON_VARIANT, nullable=True),
        sa.Column("cancellation_policy_json", _JSON_VARIANT, nullable=True),
        sa.Column("child_policy_json", _JSON_VARIANT, nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("supersedes_rate_id", sa.String(length=64), sa.ForeignKey("rates.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("lifecycle_status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("review_status", sa.String(length=16), nullable=False, server_default="verified"),
        sa.Column("validation_flags_json", _JSON_VARIANT, nullable=False, server_default="[]"),
        sa.Column("source_id", sa.String(length=64), sa.ForeignKey("rate_sources.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("updated_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("valid_to >= valid_from", name="ck_rates_valid_to_after_from"),
    )
    op.create_index("ix_rates_product_status_validity", "rates", ["product_id", "lifecycle_status", "valid_from", "valid_to"], unique=False)
    op.create_index("ix_rates_tenant_id", "rates", ["tenant_id"], unique=False)

    op.create_table(
        "rate_price_lines",
        sa.Column("id", _BIGINT_PK_VARIANT, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="capella"),
        sa.Column("rate_id", sa.String(length=64), sa.ForeignKey("rates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("price_for", sa.String(length=16), nullable=False),
        sa.Column("occupancy_basis", sa.String(length=8), nullable=False, server_default="na"),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("tier_min_pax", sa.Integer(), nullable=True),
        sa.Column("tier_max_pax", sa.Integer(), nullable=True),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("updated_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_rate_price_lines_tenant_id", "rate_price_lines", ["tenant_id"], unique=False)
    op.create_index(
        "uq_rate_price_lines_rate_combo",
        "rate_price_lines",
        ["rate_id", "price_for", "occupancy_basis", "unit", sa.text("coalesce(tier_min_pax, -1)")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_rate_price_lines_rate_combo", table_name="rate_price_lines")
    op.drop_index("ix_rate_price_lines_tenant_id", table_name="rate_price_lines")
    op.drop_table("rate_price_lines")

    op.drop_index("ix_rates_tenant_id", table_name="rates")
    op.drop_index("ix_rates_product_status_validity", table_name="rates")
    op.drop_table("rates")

    op.drop_index("ix_rate_sources_tenant_id", table_name="rate_sources")
    op.drop_index("ix_rate_sources_supplier_id", table_name="rate_sources")
    op.drop_table("rate_sources")
