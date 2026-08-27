"""Booking (15.6) — Booking + BookingLine + BusinessCodeCounter, one aggregate."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260904_42"
down_revision = "20260902_40"
branch_labels = None
depends_on = None

_JSON_VARIANT = sa.JSON().with_variant(JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "bookings",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="capella"),
        sa.Column("quotation_id", sa.String(length=64), sa.ForeignKey("quotations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("sheet_id", sa.String(length=64), sa.ForeignKey("costing_sheets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("booking_code", sa.String(length=24), nullable=False, unique=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("deposit_received_at", sa.Date(), nullable=False),
        sa.Column("customer_balance_due_date", sa.Date(), nullable=True),
        sa.Column("party_label_snapshot", sa.String(length=255), nullable=True),
        sa.Column("travel_start_date", sa.Date(), nullable=True),
        sa.Column("travel_end_date", sa.Date(), nullable=True),
        sa.Column("booking_revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("idempotency_key", sa.String(length=64), nullable=True),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("updated_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_bookings_tenant_id", "bookings", ["tenant_id"], unique=False)
    op.create_index(
        "uq_bookings_quotation_id_active",
        "bookings",
        ["quotation_id"],
        unique=True,
        postgresql_where=sa.text("status != 'cancelled'"),
        sqlite_where=sa.text("status != 'cancelled'"),
    )
    op.create_index(
        "uq_bookings_idempotency_key",
        "bookings",
        ["tenant_id", sa.text("coalesce(idempotency_key, '')")],
        unique=True,
    )

    op.create_table(
        "booking_lines",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="capella"),
        sa.Column("booking_id", sa.String(length=64), sa.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "source_service_line_id", sa.String(length=64), sa.ForeignKey("service_lines.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("supplier_id_snapshot", sa.String(length=64), nullable=True),
        sa.Column("supplier_name_snapshot", sa.String(length=255), nullable=True),
        sa.Column("supplier_contact_snapshot_json", _JSON_VARIANT, nullable=True),
        sa.Column("title_snapshot", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=24), nullable=False),
        sa.Column("service_date", sa.Date(), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("time_basis", sa.String(length=16), nullable=False),
        sa.Column("qty_unit", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("qty_time", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_cost_minor_snapshot", sa.BigInteger(), nullable=False),
        sa.Column("cost_currency_snapshot", sa.String(length=3), nullable=False),
        sa.Column("fx_rate_ppm_snapshot", sa.BigInteger(), nullable=True),
        sa.Column("sell_minor_snapshot", sa.BigInteger(), nullable=False),
        sa.Column("payment_terms_snapshot_json", _JSON_VARIANT, nullable=True),
        sa.Column("cancellation_policy_snapshot_json", _JSON_VARIANT, nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="to_request"),
        sa.Column("request_by_date", sa.Date(), nullable=True),
        sa.Column("penalty_free_until", sa.Date(), nullable=True),
        sa.Column("deposit_due_date", sa.Date(), nullable=True),
        sa.Column("balance_due_date", sa.Date(), nullable=True),
        sa.Column("supplier_ref", sa.String(length=64), nullable=True),
        sa.Column("voucher_ref", sa.String(length=24), nullable=True, unique=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.String(length=500), nullable=True),
        sa.Column("cancel_penalty_minor", sa.BigInteger(), nullable=True),
        sa.Column("assignee_email", sa.String(length=320), nullable=True),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("transition_idempotency_key", sa.String(length=64), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("updated_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_booking_lines_tenant_id", "booking_lines", ["tenant_id"], unique=False)
    op.create_index(
        "ix_booking_lines_status_request_by", "booking_lines", ["tenant_id", "status", "request_by_date"], unique=False
    )
    op.create_index("ix_booking_lines_booking_sort", "booking_lines", ["booking_id", "sort_order"], unique=False)
    op.create_index(
        "uq_booking_lines_source_service_line_active",
        "booking_lines",
        ["source_service_line_id"],
        unique=True,
        postgresql_where=sa.text("status != 'cancelled'"),
        sqlite_where=sa.text("status != 'cancelled'"),
    )

    op.create_table(
        "business_code_counters",
        sa.Column("tenant_id", sa.String(length=64), primary_key=True),
        sa.Column("code_type", sa.String(length=16), primary_key=True),
        sa.Column("year", sa.Integer(), primary_key=True),
        sa.Column("last_value", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("business_code_counters")

    op.drop_index("uq_booking_lines_source_service_line_active", table_name="booking_lines")
    op.drop_index("ix_booking_lines_booking_sort", table_name="booking_lines")
    op.drop_index("ix_booking_lines_status_request_by", table_name="booking_lines")
    op.drop_index("ix_booking_lines_tenant_id", table_name="booking_lines")
    op.drop_table("booking_lines")

    op.drop_index("uq_bookings_idempotency_key", table_name="bookings")
    op.drop_index("uq_bookings_quotation_id_active", table_name="bookings")
    op.drop_index("ix_bookings_tenant_id", table_name="bookings")
    op.drop_table("bookings")
