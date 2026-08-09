"""canonical publication revisions and current alias state

Revision ID: 20260806_08
Revises: 20260805_07
"""
from alembic import op
import sqlalchemy as sa

revision = "20260806_08"
down_revision = "20260805_07"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("quotation_publications", sa.Column("document_revision", sa.Integer(), server_default="1", nullable=False))
    op.add_column("quotation_publications", sa.Column("status", sa.String(32), server_default="published", nullable=False))
    op.add_column("quotation_publications", sa.Column("is_current", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("quotation_publications", sa.Column("restored_from_version", sa.Integer(), nullable=True))
    op.execute("CREATE UNIQUE INDEX uq_quotation_publications_current ON quotation_publications (quotation_id, lang) WHERE is_current")

def downgrade() -> None:
    op.execute("DROP INDEX uq_quotation_publications_current")
    op.drop_column("quotation_publications", "restored_from_version")
    op.drop_column("quotation_publications", "is_current")
    op.drop_column("quotation_publications", "status")
    op.drop_column("quotation_publications", "document_revision")
