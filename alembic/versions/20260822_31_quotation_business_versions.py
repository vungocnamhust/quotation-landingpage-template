"""add immutable quotation business-versioning

Revision ID: 20260822_31
Revises: 20260822_30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260822_31"
down_revision = "20260822_30"
branch_labels = None
depends_on = None


json_variant = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    with op.batch_alter_table("quotations") as batch_op:
        batch_op.add_column(sa.Column("quotation_family_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("business_version", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("parent_quotation_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("source_request_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("source_request_revision", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_quotations_parent_quotation", "quotations", ["parent_quotation_id"], ["id"], ondelete="SET NULL")
        batch_op.create_index("ix_quotations_quotation_family_id", ["quotation_family_id"], unique=False)
        batch_op.create_index("ix_quotations_parent_quotation_id", ["parent_quotation_id"], unique=False)
        batch_op.create_index("ix_quotations_source_request_id", ["source_request_id"], unique=False)
        batch_op.create_unique_constraint("uq_quotations_family_business_version", ["quotation_family_id", "business_version"])
    op.create_index("ix_quotations_source_request_revision", "quotations", ["source_request_id", "source_request_revision"], unique=False)
    op.create_table(
        "quotation_version_facts",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("quotation_id", sa.String(length=64), nullable=False),
        sa.Column("canonical_facts_json", json_variant, nullable=False),
        sa.Column("resolved_facts_json", json_variant, nullable=False),
        sa.Column("facts_hash", sa.String(length=64), nullable=False),
        sa.Column("source_request_id", sa.String(length=64), nullable=True),
        sa.Column("source_request_revision", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["quotation_id"], ["quotations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("quotation_id", name="uq_quotation_version_facts_quotation"),
    )
    op.create_index("ix_quotation_version_facts_source_request", "quotation_version_facts", ["source_request_id", "source_request_revision"], unique=False)
    op.create_table(
        "quotation_version_impacts",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("quotation_id", sa.String(length=64), nullable=False),
        sa.Column("stage", sa.String(length=16), nullable=False),
        sa.Column("scope", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("source_path", sa.String(length=255), nullable=False),
        sa.Column("target_path", sa.String(length=255), nullable=True),
        sa.Column("explanation", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("resolution_note", sa.String(length=1000), nullable=True),
        sa.Column("resolved_by_profile_id", sa.String(length=64), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["quotation_id"], ["quotations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("quotation_id", "stage", "scope", "source_path", name="uq_quotation_version_impact_target"),
    )
    op.create_index("ix_quotation_version_impacts_quotation_status", "quotation_version_impacts", ["quotation_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_quotation_version_impacts_quotation_status", table_name="quotation_version_impacts")
    op.drop_table("quotation_version_impacts")
    op.drop_index("ix_quotation_version_facts_source_request", table_name="quotation_version_facts")
    op.drop_table("quotation_version_facts")
    op.drop_index("ix_quotations_source_request_revision", table_name="quotations")
    with op.batch_alter_table("quotations") as batch_op:
        batch_op.drop_constraint("uq_quotations_family_business_version", type_="unique")
        batch_op.drop_index("ix_quotations_source_request_id")
        batch_op.drop_index("ix_quotations_parent_quotation_id")
        batch_op.drop_index("ix_quotations_quotation_family_id")
        batch_op.drop_constraint("fk_quotations_parent_quotation", type_="foreignkey")
        batch_op.drop_column("source_request_revision")
        batch_op.drop_column("source_request_id")
        batch_op.drop_column("parent_quotation_id")
        batch_op.drop_column("business_version")
        batch_op.drop_column("quotation_family_id")
