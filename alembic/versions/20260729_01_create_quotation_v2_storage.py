"""create quotation v2 storage

Revision ID: 20260729_01
Revises:
Create Date: 2026-07-29 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260729_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quotations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("opportunity_id", sa.String(length=128), nullable=True),
        sa.Column("brand_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("baseline_lang", sa.String(length=5), server_default="en", nullable=False),
        sa.Column("current_revision", sa.Integer(), server_default="0", nullable=False),
        sa.Column("current_version", sa.Integer(), server_default="0", nullable=False),
        sa.Column("template_name", sa.String(length=255), nullable=False),
        sa.Column("customer_name", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quotations_opportunity_id", "quotations", ["opportunity_id"], unique=False)
    op.create_index("ix_quotations_status_updated_at", "quotations", ["status", "updated_at"], unique=False)

    op.create_table(
        "quotation_requests",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("quotation_id", sa.String(length=64), nullable=False),
        sa.Column("request_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["quotation_id"], ["quotations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quotation_requests_quotation_id", "quotation_requests", ["quotation_id"], unique=False)

    op.create_table(
        "quotation_documents",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("quotation_id", sa.String(length=64), nullable=False),
        sa.Column("lang", sa.String(length=5), nullable=False),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column("document_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("html_sync", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("generation_status", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["quotation_id"], ["quotations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("quotation_id", "lang", name="uq_quotation_documents_quotation_lang"),
    )
    op.create_index(
        "ix_quotation_documents_quotation_lang_current",
        "quotation_documents",
        ["quotation_id", "lang", "is_current"],
        unique=False,
    )

    op.create_table(
        "quotation_document_revisions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("quotation_id", sa.String(length=64), nullable=False),
        sa.Column("lang", sa.String(length=5), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("document_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("change_source", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["quotation_id"], ["quotations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_quotation_document_revisions_quotation_lang_revision",
        "quotation_document_revisions",
        ["quotation_id", "lang", "revision"],
        unique=False,
    )

    op.create_table(
        "quotation_publications",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("quotation_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("lang", sa.String(length=5), nullable=False),
        sa.Column("html_r2_key", sa.String(length=512), nullable=False),
        sa.Column("pdf_r2_key", sa.String(length=512), nullable=True),
        sa.Column("published_url", sa.String(length=1024), nullable=True),
        sa.Column("pdf_url", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["quotation_id"], ["quotations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("quotation_id", "version", "lang", name="uq_quotation_publications_quotation_version_lang"),
    )
    op.create_index(
        "ix_quotation_publications_quotation_version",
        "quotation_publications",
        ["quotation_id", "version"],
        unique=False,
    )

    op.create_table(
        "media_assets",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("quotation_id", sa.String(length=64), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("bucket", sa.String(length=255), nullable=False),
        sa.Column("r2_key", sa.String(length=512), nullable=False),
        sa.Column("preview_r2_key", sa.String(length=512), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("local_path", sa.String(length=1024), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="ready", nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["quotation_id"], ["quotations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("r2_key"),
    )
    op.create_index("ix_media_assets_checksum_sha256", "media_assets", ["checksum_sha256"], unique=False)
    op.create_index("ix_media_assets_quotation_created_at", "media_assets", ["quotation_id", "created_at"], unique=False)
    op.create_index("ix_media_assets_status_created_at", "media_assets", ["status", "created_at"], unique=False)

    op.create_table(
        "media_selections",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("quotation_id", sa.String(length=64), nullable=False),
        sa.Column("asset_id", sa.String(length=64), nullable=False),
        sa.Column("lang", sa.String(length=5), nullable=True),
        sa.Column("section_key", sa.String(length=128), nullable=False),
        sa.Column("slot_key", sa.String(length=128), nullable=False),
        sa.Column("display_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["media_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["quotation_id"], ["quotations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_media_selections_quotation_section_slot",
        "media_selections",
        ["quotation_id", "section_key", "slot_key"],
        unique=False,
    )
    op.create_index(
        "uq_media_selections_shared_slot_order",
        "media_selections",
        ["quotation_id", "section_key", "slot_key", "display_order"],
        unique=True,
        postgresql_where=sa.text("lang IS NULL"),
    )
    op.create_index(
        "uq_media_selections_lang_slot_order",
        "media_selections",
        ["quotation_id", "lang", "section_key", "slot_key", "display_order"],
        unique=True,
        postgresql_where=sa.text("lang IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_media_selections_lang_slot_order", table_name="media_selections")
    op.drop_index("uq_media_selections_shared_slot_order", table_name="media_selections")
    op.drop_index("ix_media_selections_quotation_section_slot", table_name="media_selections")
    op.drop_table("media_selections")

    op.drop_index("ix_media_assets_status_created_at", table_name="media_assets")
    op.drop_index("ix_media_assets_quotation_created_at", table_name="media_assets")
    op.drop_index("ix_media_assets_checksum_sha256", table_name="media_assets")
    op.drop_table("media_assets")

    op.drop_index("ix_quotation_publications_quotation_version", table_name="quotation_publications")
    op.drop_table("quotation_publications")

    op.drop_index(
        "ix_quotation_document_revisions_quotation_lang_revision",
        table_name="quotation_document_revisions",
    )
    op.drop_table("quotation_document_revisions")

    op.drop_index(
        "ix_quotation_documents_quotation_lang_current",
        table_name="quotation_documents",
    )
    op.drop_table("quotation_documents")

    op.drop_index("ix_quotation_requests_quotation_id", table_name="quotation_requests")
    op.drop_table("quotation_requests")

    op.drop_index("ix_quotations_status_updated_at", table_name="quotations")
    op.drop_index("ix_quotations_opportunity_id", table_name="quotations")
    op.drop_table("quotations")
