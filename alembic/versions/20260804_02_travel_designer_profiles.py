"""add temporary travel designer profiles and quote assignment"""

from alembic import op
import sqlalchemy as sa


revision = "20260804_02"
down_revision = "20260729_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "travel_designer_profiles",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=64), server_default="", nullable=False),
        sa.Column("image_asset_id", sa.String(length=64), nullable=True),
        sa.Column("image_url", sa.String(length=1024), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_travel_designer_profiles_email"),
    )
    op.create_index(
        "ix_travel_designer_profiles_active_email",
        "travel_designer_profiles",
        ["is_active", "email"],
        unique=False,
    )
    op.create_table(
        "travel_designer_brand_defaults",
        sa.Column("brand_id", sa.String(length=64), nullable=False),
        sa.Column("designer_profile_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["designer_profile_id"], ["travel_designer_profiles.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("brand_id"),
    )
    op.add_column(
        "quotations",
        sa.Column("designer_profile_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_quotations_designer_profile_id",
        "quotations",
        ["designer_profile_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_quotations_designer_profile_id",
        "quotations",
        "travel_designer_profiles",
        ["designer_profile_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_quotations_designer_profile_id", "quotations", type_="foreignkey")
    op.drop_index("ix_quotations_designer_profile_id", table_name="quotations")
    op.drop_column("quotations", "designer_profile_id")
    op.drop_table("travel_designer_brand_defaults")
    op.drop_index("ix_travel_designer_profiles_active_email", table_name="travel_designer_profiles")
    op.drop_table("travel_designer_profiles")
