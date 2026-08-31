"""AI Platform bootstrap (ai_runs) + Interactive Ingestion Co-Pilot staging (ingestion_batches) — 15.8."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260907_45"
down_revision = "20260906_44"
branch_labels = None
depends_on = None

_JSON_VARIANT = sa.JSON().with_variant(JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "ai_runs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="capella"),
        sa.Column("agent_name", sa.String(length=48), nullable=False),
        sa.Column("anchor_type", sa.String(length=24), nullable=False),
        sa.Column("anchor_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("input_ref_json", _JSON_VARIANT, nullable=False, server_default="{}"),
        sa.Column("output_json", _JSON_VARIANT, nullable=False, server_default="{}"),
        sa.Column("stats_json", _JSON_VARIANT, nullable=False, server_default="{}"),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("updated_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "uq_ai_runs_anchor_idempotency_key",
        "ai_runs",
        ["tenant_id", "anchor_type", "anchor_id", "idempotency_key"],
        unique=True,
    )
    op.create_index("ix_ai_runs_tenant_agent_created", "ai_runs", ["tenant_id", "agent_name", "created_at"], unique=False)
    op.create_index("ix_ai_runs_anchor", "ai_runs", ["anchor_type", "anchor_id"], unique=False)

    op.create_table(
        "ingestion_batches",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="capella"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="draft"),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("source_channel", sa.String(length=16), nullable=False),
        sa.Column("source_document_type", sa.String(length=24), nullable=False),
        sa.Column("payload_json", _JSON_VARIANT, nullable=False, server_default="{}"),
        sa.Column("resolution_json", _JSON_VARIANT, nullable=True),
        sa.Column("conversation_json", _JSON_VARIANT, nullable=False, server_default="[]"),
        sa.Column("operator_edits_json", _JSON_VARIANT, nullable=False, server_default="{}"),
        sa.Column("commit_result_json", _JSON_VARIANT, nullable=True),
        sa.Column("error_json", _JSON_VARIANT, nullable=True),
        sa.Column("batch_revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("updated_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "uq_ingestion_batches_tenant_idempotency_key",
        "ingestion_batches",
        ["tenant_id", "idempotency_key"],
        unique=True,
    )
    op.create_index(
        "ix_ingestion_batches_tenant_status_created",
        "ingestion_batches",
        ["tenant_id", "status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ingestion_batches_tenant_status_created", table_name="ingestion_batches")
    op.drop_index("uq_ingestion_batches_tenant_idempotency_key", table_name="ingestion_batches")
    op.drop_table("ingestion_batches")

    op.drop_index("ix_ai_runs_anchor", table_name="ai_runs")
    op.drop_index("ix_ai_runs_tenant_agent_created", table_name="ai_runs")
    op.drop_index("uq_ai_runs_anchor_idempotency_key", table_name="ai_runs")
    op.drop_table("ai_runs")
