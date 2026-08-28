"""audit status in quote request revisions"""

from alembic import op
import sqlalchemy as sa

revision = "20260905_43"
down_revision = "20260904_42"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("quote_request_revisions", sa.Column("status", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("quote_request_revisions", "status")
