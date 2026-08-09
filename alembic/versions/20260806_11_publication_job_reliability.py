"""forward-only V2 publication job reliability

Revision ID: 20260806_11
Revises: 20260806_10
"""
from alembic import op
import sqlalchemy as sa


revision = "20260806_11"
down_revision = "20260806_10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("publication_jobs", sa.Column("event_key", sa.String(128), nullable=True))
    op.add_column("publication_jobs", sa.Column("locked_by", sa.String(128), nullable=True))
    op.add_column("publication_jobs", sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")))
    op.execute("UPDATE publication_jobs SET event_key = job_type WHERE event_key IS NULL")
    op.alter_column("publication_jobs", "event_key", nullable=False)
    op.drop_constraint("uq_publication_jobs_release_type", "publication_jobs", type_="unique")
    op.create_unique_constraint("uq_publication_jobs_release_type_event", "publication_jobs", ["release_id", "job_type", "event_key"])
    op.create_check_constraint("ck_publication_jobs_type", "publication_jobs", "job_type IN ('render_pdf', 'purge_cache')")
    op.create_check_constraint("ck_publication_jobs_status", "publication_jobs", "status IN ('queued', 'running', 'succeeded', 'failed')")
    op.create_check_constraint("ck_publication_targets_status", "publication_targets", "status IN ('draft', 'published', 'unpublished')")
    op.create_check_constraint("ck_publication_releases_status", "publication_releases", "status IN ('staging', 'published', 'superseded', 'failed')")


def downgrade() -> None:
    op.drop_constraint("ck_publication_releases_status", "publication_releases", type_="check")
    op.drop_constraint("ck_publication_targets_status", "publication_targets", type_="check")
    op.drop_constraint("ck_publication_jobs_status", "publication_jobs", type_="check")
    op.drop_constraint("ck_publication_jobs_type", "publication_jobs", type_="check")
    op.drop_constraint("uq_publication_jobs_release_type_event", "publication_jobs", type_="unique")
    op.create_unique_constraint("uq_publication_jobs_release_type", "publication_jobs", ["release_id", "job_type"])
    op.drop_column("publication_jobs", "payload_json")
    op.drop_column("publication_jobs", "locked_by")
    op.drop_column("publication_jobs", "event_key")
