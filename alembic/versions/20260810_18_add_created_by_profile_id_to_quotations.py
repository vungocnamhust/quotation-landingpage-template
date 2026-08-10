"""add created_by_profile_id to quotations"""

from alembic import op
import sqlalchemy as sa


revision = "20260810_18"
down_revision = "20260810_17"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "quotations",
        sa.Column("created_by_profile_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_quotations_created_by_profile_id",
        "quotations",
        ["created_by_profile_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_quotations_created_by_profile_id",
        "quotations",
        "travel_designer_profiles",
        ["created_by_profile_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        "UPDATE quotations SET created_by_profile_id = designer_profile_id WHERE created_by_profile_id IS NULL AND designer_profile_id IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_constraint("fk_quotations_created_by_profile_id", "quotations", type_="foreignkey")
    op.drop_index("ix_quotations_created_by_profile_id", table_name="quotations")
    op.drop_column("quotations", "created_by_profile_id")
