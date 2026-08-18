"""create quote requests table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql, sqlite

revision = "20260814_21"
down_revision = "20260812_20"
branch_labels = None
depends_on = None

json_variant = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade():
    op.create_table(
        "quote_requests",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="new", nullable=False),
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
        sa.Column("created_by_profile_id", sa.String(length=64), nullable=True),
        sa.Column("linked_quotation_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_profile_id"], ["travel_designer_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["linked_quotation_id"], ["quotations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quote_requests_status_created_at", "quote_requests", ["status", "created_at"], unique=False)
    op.create_index("ix_quote_requests_role_created_at", "quote_requests", ["role", "created_at"], unique=False)
    op.create_index("ix_quote_requests_customer_email", "quote_requests", ["email"], unique=False)
    op.create_index("ix_quote_requests_linked_quotation_id", "quote_requests", ["linked_quotation_id"], unique=False)


def downgrade():
    op.drop_index("ix_quote_requests_linked_quotation_id", table_name="quote_requests")
    op.drop_index("ix_quote_requests_customer_email", table_name="quote_requests")
    op.drop_index("ix_quote_requests_role_created_at", table_name="quote_requests")
    op.drop_index("ix_quote_requests_status_created_at", table_name="quote_requests")
    op.drop_table("quote_requests")
