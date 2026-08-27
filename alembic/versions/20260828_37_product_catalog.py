"""Add product catalog (15.2) — sellable service variants, no pricing."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260828_37"
down_revision = "20260827_36"
branch_labels = None
depends_on = None

_JSON_VARIANT = sa.JSON().with_variant(JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="capella"),
        sa.Column("supplier_id", sa.String(length=64), sa.ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=True),
        sa.Column(
            "property_id",
            sa.String(length=64),
            sa.ForeignKey("accommodation_profiles.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "destination_id",
            sa.String(length=64),
            sa.ForeignKey("destination_catalog.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("category", sa.String(length=24), nullable=False),
        sa.Column("subcategory", sa.String(length=48), nullable=True),
        sa.Column("subcategory_note", sa.String(length=120), nullable=True),
        sa.Column("supplier_product_name", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("title_normalized", sa.String(length=255), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("time_basis", sa.String(length=16), nullable=False),
        sa.Column("default_min_pax", sa.Integer(), nullable=True),
        sa.Column("default_max_pax", sa.Integer(), nullable=True),
        sa.Column("category_attributes", _JSON_VARIANT, nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("updated_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_products_tenant_id", "products", ["tenant_id"], unique=False)
    op.create_index("ix_products_supplier_id", "products", ["supplier_id"], unique=False)
    op.create_index("ix_products_property_id", "products", ["property_id"], unique=False)
    op.create_index(
        "ix_products_tenant_destination_category_active",
        "products",
        ["tenant_id", "destination_id", "category", "is_active"],
        unique=False,
    )
    op.create_index(
        "uq_products_tenant_destination_category_title_supplier",
        "products",
        [
            "tenant_id",
            "destination_id",
            "category",
            "title_normalized",
            sa.text("coalesce(supplier_id, '')"),
        ],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_products_tenant_destination_category_title_supplier", table_name="products")
    op.drop_index("ix_products_tenant_destination_category_active", table_name="products")
    op.drop_index("ix_products_property_id", table_name="products")
    op.drop_index("ix_products_supplier_id", table_name="products")
    op.drop_index("ix_products_tenant_id", table_name="products")
    op.drop_table("products")
