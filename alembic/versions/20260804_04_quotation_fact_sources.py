"""add quotation factual source ownership

Revision ID: 20260804_04
Revises: 20260804_03
Create Date: 2026-08-04 00:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = "20260804_04"
down_revision = "20260804_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("quotations", sa.Column("source_kind", sa.String(length=32), server_default="manual", nullable=False))
    op.add_column("quotations", sa.Column("source_snapshot_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("quotations", sa.Column("source_version", sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column("quotations", "source_version")
    op.drop_column("quotations", "source_snapshot_at")
    op.drop_column("quotations", "source_kind")
