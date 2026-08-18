"""create quote request revisions table and add revision tracking to quote_requests"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260817_23"
down_revision = "20260817_22"
branch_labels = None
depends_on = None

json_variant = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade():
    # 1. Add current_revision & updated_by_profile_id columns to quote_requests
    with op.batch_alter_table("quote_requests") as batch_op:
        batch_op.add_column(sa.Column("current_revision", sa.Integer(), server_default="1", nullable=False))
        batch_op.add_column(sa.Column("updated_by_profile_id", sa.String(length=64), nullable=True))
        batch_op.create_foreign_key(
            "fk_quote_requests_updated_by_profile_id",
            "travel_designer_profiles",
            ["updated_by_profile_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_quote_requests_updated_by", ["updated_by_profile_id"], unique=False)

    # 2. Create quote_request_revisions table
    op.create_table(
        "quote_request_revisions",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, primary_key=True),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("customer_name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("market", sa.String(length=64), nullable=True),
        sa.Column("preferred_contact", sa.String(length=32), nullable=True),
        sa.Column("destinations", json_variant, nullable=False),
        sa.Column("start_date", sa.String(length=32), nullable=True),
        sa.Column("end_date", sa.String(length=32), nullable=True),
        sa.Column("raw_dates_text", sa.String(length=255), nullable=True),
        sa.Column("adults", sa.Integer(), nullable=True),
        sa.Column("children", sa.Integer(), nullable=True),
        sa.Column("kid_ages", json_variant, nullable=False),
        sa.Column("children_details", sa.String(length=255), nullable=True),
        sa.Column("travel_style", sa.String(length=64), nullable=True),
        sa.Column("special_requirements", sa.String(length=2000), nullable=True),
        sa.Column("payload_json", json_variant, nullable=False),
        sa.Column("change_summary", sa.String(length=500), nullable=True),
        sa.Column("change_source", sa.String(length=64), server_default="initial_intake", nullable=False),
        sa.Column("created_by_profile_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["quote_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_profile_id"], ["travel_designer_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_quote_request_revisions_request_rev",
        "quote_request_revisions",
        ["request_id", "revision"],
        unique=True,
    )
    op.create_index(
        "ix_quote_request_revisions_created_at",
        "quote_request_revisions",
        ["created_at"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_quote_request_revisions_created_at", table_name="quote_request_revisions")
    op.drop_index("ix_quote_request_revisions_request_rev", table_name="quote_request_revisions")
    op.drop_table("quote_request_revisions")

    with op.batch_alter_table("quote_requests") as batch_op:
        batch_op.drop_index("ix_quote_requests_updated_by")
        batch_op.drop_constraint("fk_quote_requests_updated_by_profile_id", type_="foreignkey")
        batch_op.drop_column("updated_by_profile_id")
        batch_op.drop_column("current_revision")
