"""Normalize executable Impact Center targets without altering legacy quotations."""

from alembic import op
import sqlalchemy as sa


revision = "20260823_33"
down_revision = "20260823_32"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quotation_version_impact_targets",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("impact_id", sa.BigInteger(), sa.ForeignKey("quotation_version_impacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quotation_id", sa.String(length=64), sa.ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage", sa.String(length=16), nullable=False),
        sa.Column("scope", sa.String(length=128), nullable=False),
        sa.Column("target_path", sa.String(length=255), nullable=False),
        sa.Column("treatment", sa.String(length=32), nullable=False),
        sa.Column("affected_fields_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("generation_eligible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("generation_selected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("execution_status", sa.String(length=24), nullable=False, server_default="not_requested"),
        sa.Column("draft_id", sa.String(length=64), sa.ForeignKey("quotation_content_drafts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("accepted_by_profile_id", sa.String(length=64), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("impact_id", "stage", "scope", "target_path", name="uq_quotation_version_impact_target_path"),
    )
    op.create_index("ix_quotation_version_impact_targets_quotation_status", "quotation_version_impact_targets", ["quotation_id", "execution_status"])


def downgrade() -> None:
    op.drop_index("ix_quotation_version_impact_targets_quotation_status", table_name="quotation_version_impact_targets")
    op.drop_table("quotation_version_impact_targets")
