"""add owner-first quotation workspace pagination index

Revision ID: 20260806_13
Revises: 20260806_12
"""
from alembic import op
import sqlalchemy as sa


revision = "20260806_13"
down_revision = "20260806_12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_quotations_designer_updated_id",
        "quotations",
        ["designer_profile_id", sa.text("updated_at DESC"), sa.text("id DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_quotations_designer_updated_id", table_name="quotations")
