"""remove check_in and check_out from accommodation_profiles

Revision ID: 20260817_24
Revises: 20260817_23
Create Date: 2026-08-17
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260817_24"
down_revision = "20260817_23"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("accommodation_profiles") as batch_op:
        batch_op.drop_column("check_in")
        batch_op.drop_column("check_out")


def downgrade() -> None:
    with op.batch_alter_table("accommodation_profiles") as batch_op:
        batch_op.add_column(sa.Column("check_in", sa.String(32), nullable=True))
        batch_op.add_column(sa.Column("check_out", sa.String(32), nullable=True))
