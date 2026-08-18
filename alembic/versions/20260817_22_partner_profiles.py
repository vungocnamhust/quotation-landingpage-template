"""create partner profiles table and add partner_id to quote_requests"""

from alembic import op
import sqlalchemy as sa

revision = "20260817_22"
down_revision = "20260814_21"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "partner_profiles",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("contact_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("phone", sa.String(length=64), server_default="", nullable=False),
        sa.Column("market", sa.String(length=64), nullable=True),
        sa.Column("tier", sa.String(length=32), server_default="Standard", nullable=True),
        sa.Column("default_commission_rate", sa.Float(), server_default="10.0", nullable=False),
        sa.Column("preferred_currency", sa.String(length=16), server_default="USD", nullable=False),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_partner_profiles_email"),
    )
    op.create_index("ix_partner_profiles_active_company", "partner_profiles", ["is_active", "company_name"], unique=False)
    op.create_index("ix_partner_profiles_email", "partner_profiles", ["email"], unique=False)

    with op.batch_alter_table("quote_requests") as batch_op:
        batch_op.add_column(sa.Column("partner_id", sa.String(length=64), nullable=True))
        batch_op.create_foreign_key(
            "fk_quote_requests_partner_id_partner_profiles",
            "partner_profiles",
            ["partner_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_quote_requests_partner_id", ["partner_id"], unique=False)


def downgrade():
    with op.batch_alter_table("quote_requests") as batch_op:
        batch_op.drop_index("ix_quote_requests_partner_id")
        batch_op.drop_constraint("fk_quote_requests_partner_id_partner_profiles", type_="foreignkey")
        batch_op.drop_column("partner_id")

    op.drop_index("ix_partner_profiles_email", table_name="partner_profiles")
    op.drop_index("ix_partner_profiles_active_company", table_name="partner_profiles")
    op.drop_table("partner_profiles")
