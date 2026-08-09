"""add media library index and destination catalog

Revision ID: 20260804_05
Revises: 20260804_04
Create Date: 2026-08-04 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260804_05"
down_revision = "20260804_04"
branch_labels = None
depends_on = None

JSON = postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table("media_library_sync_runs", sa.Column("id", sa.String(64), primary_key=True), sa.Column("status", sa.String(32), nullable=False, server_default="queued"), sa.Column("prefixes", JSON, nullable=False), sa.Column("scanned_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("indexed_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("preview_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("cursor", JSON, nullable=False), sa.Column("error_message", sa.String(1024)), sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("finished_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_media_library_sync_runs_status_created", "media_library_sync_runs", ["status", "created_at"])
    op.create_table("media_library_objects", sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True), sa.Column("bucket", sa.String(255), nullable=False), sa.Column("r2_key", sa.String(1024), nullable=False, unique=True), sa.Column("parent_prefix", sa.String(1024), nullable=False), sa.Column("file_name", sa.String(512), nullable=False), sa.Column("content_type", sa.String(255)), sa.Column("size_bytes", sa.BigInteger(), nullable=False, server_default="0"), sa.Column("etag", sa.String(255)), sa.Column("source_modified_at", sa.DateTime(timezone=True)), sa.Column("preview_r2_key", sa.String(1024)), sa.Column("width", sa.Integer()), sa.Column("height", sa.Integer()), sa.Column("preview_status", sa.String(32), nullable=False, server_default="pending"), sa.Column("preview_error", sa.String(512)), sa.Column("last_seen_run_id", sa.String(64), sa.ForeignKey("media_library_sync_runs.id", ondelete="SET NULL")), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_media_library_objects_parent_active", "media_library_objects", ["parent_prefix", "is_active", "file_name"])
    op.create_index("ix_media_library_objects_run", "media_library_objects", ["last_seen_run_id"])
    op.create_table("destination_catalog", sa.Column("id", sa.String(64), primary_key=True), sa.Column("canonical_name", sa.String(255), nullable=False), sa.Column("slug", sa.String(255), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("mapping_version", sa.String(64), nullable=False, server_default="resolver-v1"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("slug", name="uq_destination_catalog_slug"))
    op.create_index("ix_destination_catalog_active_name", "destination_catalog", ["is_active", "canonical_name"])
    op.create_table("destination_aliases", sa.Column("id", sa.String(64), primary_key=True), sa.Column("destination_id", sa.String(64), sa.ForeignKey("destination_catalog.id", ondelete="CASCADE"), nullable=False), sa.Column("normalized_alias", sa.String(255), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("normalized_alias", name="uq_destination_aliases_normalized_alias"))
    op.create_index("ix_destination_aliases_destination_id", "destination_aliases", ["destination_id"])


def downgrade() -> None:
    op.drop_table("destination_aliases")
    op.drop_table("destination_catalog")
    op.drop_table("media_library_objects")
    op.drop_table("media_library_sync_runs")
