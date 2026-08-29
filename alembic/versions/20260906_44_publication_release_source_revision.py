"""source_base_revision on publication_releases for idempotent publish replay"""

from alembic import op
import sqlalchemy as sa

revision = "20260906_44"
down_revision = "20260905_43"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "publication_releases",
        sa.Column("source_base_revision", sa.Integer(), nullable=True),
    )
    op.execute(
        "UPDATE publication_releases SET source_base_revision = document_revision "
        "WHERE source_base_revision IS NULL"
    )
    op.alter_column("publication_releases", "source_base_revision", nullable=False)
    op.create_index(
        "uq_publication_releases_target_source_revision",
        "publication_releases",
        ["target_id", "source_base_revision"],
        unique=True,
        postgresql_where=sa.text("status != 'failed'"),
        sqlite_where=sa.text("status != 'failed'"),
    )


def downgrade() -> None:
    op.drop_index("uq_publication_releases_target_source_revision", table_name="publication_releases")
    op.drop_column("publication_releases", "source_base_revision")
