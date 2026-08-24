"""Add Content action-plan persistence from the migration-34 baseline."""
from alembic import op
import sqlalchemy as sa


revision = "20260824_35"
down_revision = "20260823_34"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quotation_content_action_plans",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("quotation_id", sa.String(length=64), sa.ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("predecessor_quotation_id", sa.String(length=64), sa.ForeignKey("quotations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("facts_hash", sa.String(length=64), nullable=False),
        sa.Column("plan_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("accepted_by_profile_id", sa.String(length=64), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acceptance_note", sa.String(length=1000), nullable=True),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("quotation_id", "plan_hash", name="uq_quotation_content_action_plan_hash"),
    )
    op.create_index("ix_quotation_content_action_plans_quotation_status", "quotation_content_action_plans", ["quotation_id", "status"], unique=False)
    op.create_table(
        "quotation_content_actions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("plan_id", sa.String(length=64), sa.ForeignKey("quotation_content_action_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quotation_id", sa.String(length=64), sa.ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action_key", sa.String(length=255), nullable=False),
        sa.Column("scope", sa.String(length=128), nullable=False),
        sa.Column("entity_key", sa.String(length=255), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("automation_policy", sa.String(length=16), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("input_facts_hash", sa.String(length=64), nullable=False),
        sa.Column("predecessor_quotation_id", sa.String(length=64), sa.ForeignKey("quotations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("inherited_reference_status", sa.String(length=24), nullable=False, server_default="unavailable"),
        sa.Column("action_metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("draft_id", sa.String(length=64), sa.ForeignKey("quotation_content_drafts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("applied_document_revision", sa.Integer(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("executed_by_profile_id", sa.String(length=64), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("plan_id", "action_key", name="uq_quotation_content_action_plan_key"),
    )
    op.create_index("ix_quotation_content_actions_quotation_state", "quotation_content_actions", ["quotation_id", "state"], unique=False)
    op.create_index("ix_quotation_content_actions_plan_policy", "quotation_content_actions", ["plan_id", "automation_policy"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_quotation_content_actions_plan_policy", table_name="quotation_content_actions")
    op.drop_index("ix_quotation_content_actions_quotation_state", table_name="quotation_content_actions")
    op.drop_table("quotation_content_actions")
    op.drop_index("ix_quotation_content_action_plans_quotation_status", table_name="quotation_content_action_plans")
    op.drop_table("quotation_content_action_plans")
