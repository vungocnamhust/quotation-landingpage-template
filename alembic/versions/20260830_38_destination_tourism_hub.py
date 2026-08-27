"""Destination Tourism Hub (15.2b) — additive hierarchy, merge redirect, product origin leg."""
from alembic import op
import sqlalchemy as sa


revision = "20260830_38"
down_revision = "20260828_37"
branch_labels = None
depends_on = None

_COUNTRY_CODE_BY_COUNTRY_SLUG = {
    "vietnam": "VN",
    "cambodia": "KH",
    "laos": "LA",
    "thailand": "TH",
}

_BANGKOK_TZ_SLUGS = ("bangkok", "chiang-mai", "phuket")


def upgrade() -> None:
    with op.batch_alter_table("destination_catalog") as batch_op:
        batch_op.add_column(sa.Column("parent_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("destination_type", sa.String(length=16), nullable=False, server_default="city"))
        batch_op.add_column(sa.Column("country_code", sa.String(length=2), nullable=True))
        batch_op.add_column(sa.Column("iata_code", sa.String(length=3), nullable=True))
        batch_op.add_column(
            sa.Column("timezone", sa.String(length=64), nullable=False, server_default="Asia/Ho_Chi_Minh")
        )
        batch_op.add_column(sa.Column("merged_into_id", sa.String(length=64), nullable=True))
        batch_op.create_foreign_key(
            "fk_destination_catalog_parent_id", "destination_catalog", ["parent_id"], ["id"], ondelete="RESTRICT"
        )
        batch_op.create_foreign_key(
            "fk_destination_catalog_merged_into_id",
            "destination_catalog",
            ["merged_into_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_check_constraint(
            "ck_destination_catalog_merge_not_self", "merged_into_id IS NULL OR merged_into_id != id"
        )
        batch_op.create_index("ix_destination_catalog_parent", ["parent_id"], unique=False)
        batch_op.create_index("ix_destination_catalog_type_active", ["destination_type", "is_active"], unique=False)

    with op.batch_alter_table("destination_aliases") as batch_op:
        batch_op.add_column(sa.Column("is_merge_alias", sa.Boolean(), nullable=False, server_default="false"))
        batch_op.add_column(sa.Column("source_slug", sa.String(length=255), nullable=True))

    connection = op.get_bind()
    destination_catalog = sa.table(
        "destination_catalog",
        sa.column("id", sa.String),
        sa.column("country_slug", sa.String),
        sa.column("slug", sa.String),
        sa.column("country_code", sa.String),
        sa.column("timezone", sa.String),
    )
    for country_slug, country_code in _COUNTRY_CODE_BY_COUNTRY_SLUG.items():
        connection.execute(
            destination_catalog.update()
            .where(destination_catalog.c.country_slug == country_slug)
            .values(country_code=country_code)
        )
    connection.execute(
        destination_catalog.update()
        .where(destination_catalog.c.slug.in_(_BANGKOK_TZ_SLUGS))
        .values(timezone="Asia/Bangkok")
    )

    # SQLite's batch-table-recreate mode cannot reflect this expression index (it would be
    # silently dropped on recreate anyway), so drop it explicitly before touching the table.
    op.drop_index("uq_products_tenant_destination_category_title_supplier", table_name="products")

    with op.batch_alter_table("products") as batch_op:
        batch_op.add_column(sa.Column("origin_destination_id", sa.String(length=64), nullable=True))
        batch_op.create_foreign_key(
            "fk_products_origin_destination_id",
            "destination_catalog",
            ["origin_destination_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index("ix_products_origin_destination_id", ["origin_destination_id"], unique=False)

    op.create_index(
        "uq_products_tenant_destination_category_title_supplier",
        "products",
        [
            "tenant_id",
            "destination_id",
            "category",
            "title_normalized",
            sa.text("coalesce(supplier_id, '')"),
            sa.text("coalesce(origin_destination_id, '')"),
        ],
        unique=True,
    )


def downgrade() -> None:
    # Drop first: SQLite batch-recreate below cannot reflect this expression index and would
    # silently lose it anyway.
    op.drop_index("uq_products_tenant_destination_category_title_supplier", table_name="products")

    with op.batch_alter_table("destination_aliases") as batch_op:
        batch_op.drop_column("source_slug")
        batch_op.drop_column("is_merge_alias")

    with op.batch_alter_table("products") as batch_op:
        batch_op.drop_index("ix_products_origin_destination_id")
        batch_op.drop_constraint("fk_products_origin_destination_id", type_="foreignkey")
        batch_op.drop_column("origin_destination_id")

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

    with op.batch_alter_table("destination_catalog") as batch_op:
        batch_op.drop_index("ix_destination_catalog_type_active")
        batch_op.drop_index("ix_destination_catalog_parent")
        batch_op.drop_constraint("ck_destination_catalog_merge_not_self", type_="check")
        batch_op.drop_constraint("fk_destination_catalog_merged_into_id", type_="foreignkey")
        batch_op.drop_constraint("fk_destination_catalog_parent_id", type_="foreignkey")
        batch_op.drop_column("merged_into_id")
        batch_op.drop_column("timezone")
        batch_op.drop_column("iata_code")
        batch_op.drop_column("country_code")
        batch_op.drop_column("destination_type")
        batch_op.drop_column("parent_id")
