"""allow only one active media-library sync run

Revision ID: 20260805_07
Revises: 20260805_06
"""

from alembic import op


revision = "20260805_07"
down_revision = "20260805_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE UNIQUE INDEX uq_media_library_sync_runs_active "
        "ON media_library_sync_runs ((1)) "
        "WHERE status IN ('queued', 'indexing', 'previewing')"
    )


def downgrade() -> None:
    op.execute("DROP INDEX uq_media_library_sync_runs_active")
