"""add stable globally unique public fallback URLs

Revision ID: 20260810_17
Revises: 20260809_16
Create Date: 2026-08-10
"""

from alembic import op
import sqlalchemy as sa


revision = "20260810_17"
down_revision = "20260809_16"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("publication_targets", sa.Column("fallback_slug", sa.String(length=128), nullable=True))
    # Deterministic tokens make this migration repeatable and preserve every
    # existing target/release pointer without requiring a republish.
    op.execute(
        "UPDATE publication_targets "
        "SET fallback_slug = 'p-' || substr(md5('fallback:' || id), 1, 32) "
        "WHERE fallback_slug IS NULL"
    )
    op.alter_column("publication_targets", "fallback_slug", nullable=False)
    op.create_unique_constraint("uq_publication_targets_fallback_slug", "publication_targets", ["fallback_slug"])


def downgrade() -> None:
    op.drop_constraint("uq_publication_targets_fallback_slug", "publication_targets", type_="unique")
    op.drop_column("publication_targets", "fallback_slug")
