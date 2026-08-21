"""add signature_initial to travel designer profiles

Revision ID: 20260822_29
Revises: 20260821_28
Create Date: 2026-08-22

"""
from alembic import op
import sqlalchemy as sa


revision = "20260822_29"
down_revision = "20260821_28"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "travel_designer_profiles",
        sa.Column(
            "signature_initial",
            sa.String(length=255),
            nullable=True,
            comment="Free-form calligraphy characters for the handwritten signature glyph (e.g. 'Nam H.', 'V'). NULL = no glyph rendered.",
        ),
    )


def downgrade() -> None:
    op.drop_column("travel_designer_profiles", "signature_initial")
