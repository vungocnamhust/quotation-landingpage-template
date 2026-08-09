"""add accommodation catalog profiles"""

from alembic import op
import sqlalchemy as sa


revision = "20260808_14"
down_revision = "20260806_13"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("accommodation_profiles", sa.Column("id", sa.String(64), nullable=False), sa.Column("destination_id", sa.String(64), nullable=False), sa.Column("storage_slug", sa.String(255), nullable=False), sa.Column("asset_prefix", sa.String(1024), nullable=False), sa.Column("name", sa.String(255), nullable=False), sa.Column("room_type", sa.String(255), nullable=True), sa.Column("check_in", sa.String(32), nullable=True), sa.Column("check_out", sa.String(32), nullable=True), sa.Column("intro", sa.String(4000), nullable=True), sa.Column("phone", sa.String(64), nullable=True), sa.Column("display_city", sa.String(255), nullable=True), sa.Column("display_date", sa.String(255), nullable=True), sa.Column("hotel_asset", sa.String(1024), nullable=True), sa.Column("room_asset", sa.String(1024), nullable=True), sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.ForeignKeyConstraint(["destination_id"], ["destination_catalog.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("asset_prefix"), sa.UniqueConstraint("destination_id", "storage_slug", name="uq_accommodation_profiles_destination_storage_slug"))
    op.create_index("ix_accommodation_profiles_active_name", "accommodation_profiles", ["is_active", "name"], unique=False)
    op.create_index("ix_accommodation_profiles_destination_id", "accommodation_profiles", ["destination_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_accommodation_profiles_destination_id", table_name="accommodation_profiles")
    op.drop_index("ix_accommodation_profiles_active_name", table_name="accommodation_profiles")
    op.drop_table("accommodation_profiles")
