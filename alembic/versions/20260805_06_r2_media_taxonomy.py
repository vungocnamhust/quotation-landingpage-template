"""add R2 media taxonomy metadata

Revision ID: 20260805_06
Revises: 20260804_05
"""

from alembic import op
import sqlalchemy as sa

revision = "20260805_06"
down_revision = "20260804_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for name in ("country_slug", "region_slug", "province_slug"):
        op.add_column("destination_catalog", sa.Column(name, sa.String(128), nullable=True))
    op.add_column("travel_designer_profiles", sa.Column("storage_slug", sa.String(255), nullable=True))
    op.add_column("travel_designer_profiles", sa.Column("image_r2_key", sa.String(1024), nullable=True))
    op.create_unique_constraint("uq_travel_designer_profiles_storage_slug", "travel_designer_profiles", ["storage_slug"])
    for name, type_ in (("media_kind", sa.String(32)), ("subject_type", sa.String(32)), ("subject_id", sa.String(128)), ("destination_id", sa.String(64)), ("accommodation_slug", sa.String(255)), ("accommodation_kind", sa.String(32))):
        op.add_column("media_library_objects", sa.Column(name, type_, nullable=True))
    op.add_column("media_library_objects", sa.Column("source", sa.String(32), nullable=False, server_default="r2_sync"))


def downgrade() -> None:
    op.drop_column("media_library_objects", "source")
    for name in ("accommodation_kind", "accommodation_slug", "destination_id", "subject_id", "subject_type", "media_kind"):
        op.drop_column("media_library_objects", name)
    op.drop_constraint("uq_travel_designer_profiles_storage_slug", "travel_designer_profiles", type_="unique")
    op.drop_column("travel_designer_profiles", "image_r2_key")
    op.drop_column("travel_designer_profiles", "storage_slug")
    for name in ("province_slug", "region_slug", "country_slug"):
        op.drop_column("destination_catalog", name)
