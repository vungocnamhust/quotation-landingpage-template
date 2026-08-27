"""Add supplier registry (15.1) — creditor-side reference data."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260827_36"
down_revision = "20260824_35"
branch_labels = None
depends_on = None

_JSON_VARIANT = sa.JSON().with_variant(JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "suppliers",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="capella"),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("name_normalized", sa.String(length=255), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=True),
        sa.Column("supplier_type", sa.String(length=24), nullable=False),
        sa.Column("country", sa.String(length=64), nullable=True),
        sa.Column("city", sa.String(length=64), nullable=True),
        sa.Column("destination_id", sa.String(length=64), sa.ForeignKey("destination_catalog.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("default_currency", sa.String(length=3), nullable=False),
        sa.Column("preferred_status", sa.String(length=16), nullable=False, server_default="standard"),
        sa.Column("quality_tier", sa.String(length=16), nullable=True),
        sa.Column("contact_json", _JSON_VARIANT, nullable=False, server_default="{}"),
        sa.Column("payment_terms_json", _JSON_VARIANT, nullable=True),
        sa.Column("cancellation_policy_json", _JSON_VARIANT, nullable=True),
        sa.Column("child_policy_json", _JSON_VARIANT, nullable=True),
        sa.Column("bank_details_ref", sa.String(length=255), nullable=True),
        sa.Column("tax_code", sa.String(length=64), nullable=True),
        sa.Column("credit_terms_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("internal_notes", sa.String(length=2000), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("updated_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "name_normalized", name="uq_suppliers_tenant_name_normalized"),
    )
    op.create_index("ix_suppliers_active_name", "suppliers", ["is_active", "name"], unique=False)
    op.create_index("ix_suppliers_tenant_type", "suppliers", ["tenant_id", "supplier_type"], unique=False)
    op.create_index("ix_suppliers_destination_id", "suppliers", ["destination_id"], unique=False)
    op.create_index("ix_suppliers_tenant_id", "suppliers", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_suppliers_tenant_id", table_name="suppliers")
    op.drop_index("ix_suppliers_destination_id", table_name="suppliers")
    op.drop_index("ix_suppliers_tenant_type", table_name="suppliers")
    op.drop_index("ix_suppliers_active_name", table_name="suppliers")
    op.drop_table("suppliers")
