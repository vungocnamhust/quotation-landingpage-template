"""add reviewable quotation content drafts

Revision ID: 20260804_03
Revises: 20260804_02
Create Date: 2026-08-04 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260804_03"
down_revision = "20260804_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quotation_content_drafts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("quotation_id", sa.String(length=64), nullable=False),
        sa.Column("lang", sa.String(length=5), nullable=False),
        sa.Column("scope", sa.String(length=128), nullable=False),
        sa.Column("generation_mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("facts_hash", sa.String(length=64), nullable=False),
        sa.Column("source_document_revision", sa.Integer(), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("facts_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("candidate_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("missing_inputs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("generation_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["quotation_id"], ["quotations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quotation_content_drafts_quotation_lang_created", "quotation_content_drafts", ["quotation_id", "lang", "created_at"], unique=False)
    op.create_index("ix_quotation_content_drafts_cache", "quotation_content_drafts", ["quotation_id", "lang", "scope", "generation_mode", "facts_hash"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_quotation_content_drafts_cache", table_name="quotation_content_drafts")
    op.drop_index("ix_quotation_content_drafts_quotation_lang_created", table_name="quotation_content_drafts")
    op.drop_table("quotation_content_drafts")
