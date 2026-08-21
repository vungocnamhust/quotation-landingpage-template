"""add destination media_prefix column

Revision ID: 20260821_27
Revises: 20260820_26
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260821_27"
down_revision = "20260820_26"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("destination_catalog", sa.Column("media_prefix", sa.String(1024), nullable=True))


def downgrade() -> None:
    op.drop_column("destination_catalog", "media_prefix")
