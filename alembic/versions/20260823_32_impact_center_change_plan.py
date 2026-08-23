"""Persist the concrete change plan and generation audit shown by Impact Center."""

from alembic import op
import sqlalchemy as sa


revision = "20260823_32"
down_revision = "20260822_31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("quotation_version_impacts") as batch_op:
        batch_op.add_column(sa.Column("entity_key", sa.String(length=255), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("operation", sa.String(length=32), nullable=False, server_default="changed"))
        batch_op.add_column(sa.Column("old_value_json", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("new_value_json", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("generation_eligible", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("generation_selected", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("generation_status", sa.String(length=24), nullable=False, server_default="not_requested"))


def downgrade() -> None:
    with op.batch_alter_table("quotation_version_impacts") as batch_op:
        batch_op.drop_column("generation_status")
        batch_op.drop_column("generation_selected")
        batch_op.drop_column("generation_eligible")
        batch_op.drop_column("new_value_json")
        batch_op.drop_column("old_value_json")
        batch_op.drop_column("operation")
        batch_op.drop_column("entity_key")
