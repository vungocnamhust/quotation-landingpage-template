"""durable V2 publication jobs and release-current invariant

Revision ID: 20260806_10
Revises: 20260806_09
"""
from alembic import op
import sqlalchemy as sa

revision = "20260806_10"
down_revision = "20260806_09"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE UNIQUE INDEX uq_publication_releases_current ON publication_releases (target_id) WHERE is_current")
    op.create_table(
        "publication_jobs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("release_id", sa.String(64), sa.ForeignKey("publication_releases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("locked_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("artifact_key", sa.String(512)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("release_id", "job_type", name="uq_publication_jobs_release_type"),
    )
    op.create_index("ix_publication_jobs_claim", "publication_jobs", ["status", "next_run_at", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_publication_jobs_claim", table_name="publication_jobs")
    op.drop_table("publication_jobs")
    op.execute("DROP INDEX uq_publication_releases_current")
