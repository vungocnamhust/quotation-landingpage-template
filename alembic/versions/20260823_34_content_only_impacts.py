"""Refactor Impact Center persistence to Content-only target selection."""
from alembic import op
import sqlalchemy as sa

revision = "20260823_34"
down_revision = "20260823_33"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("quotation_version_impact_targets") as batch:
        batch.add_column(sa.Column("deep_link_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.create_table(
        "quotation_version_impact_acceptances",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("quotation_id", sa.String(length=64), sa.ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=False),
        sa.Column("selected_target_ids_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("resolution_note", sa.String(length=1000), nullable=False),
        sa.Column("accepted_by_profile_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("quotation_id", "idempotency_key", name="uq_quotation_impact_acceptance_idempotency"),
    )
    op.execute("""INSERT INTO quotation_version_impact_targets (impact_id, quotation_id, stage, scope, target_path, treatment, affected_fields_json, deep_link_json, generation_eligible, generation_selected, execution_status) SELECT i.id, i.quotation_id, 'content', i.scope, COALESCE(i.target_path, '/'), CASE WHEN i.generation_eligible THEN 'generation_candidate' ELSE 'preserved_review' END, '[]'::json, json_build_object('stage','content','section',i.scope,'focus',i.entity_key), i.generation_eligible, false, 'not_requested' FROM quotation_version_impacts i JOIN quotations q ON q.id=i.quotation_id WHERE q.quotation_family_id IS NOT NULL AND i.stage='content' AND NOT EXISTS (SELECT 1 FROM quotation_version_impact_targets t WHERE t.impact_id=i.id AND t.stage='content')""")
    op.execute("UPDATE quotation_version_impacts SET generation_selected=false, generation_status='not_requested' WHERE stage='design'")
    op.execute("DELETE FROM quotation_version_impact_targets WHERE stage='design'")


def downgrade() -> None:
    op.drop_table("quotation_version_impact_acceptances")
    with op.batch_alter_table("quotation_version_impact_targets") as batch:
        batch.drop_column("deep_link_json")
