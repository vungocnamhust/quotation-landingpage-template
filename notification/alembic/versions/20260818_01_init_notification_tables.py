"""init notification tables

Revision ID: 20260818_01
Revises: None
Create Date: 2026-08-18 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from db.types import JSON_VARIANT


revision = "20260818_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("source_service", sa.String(length=64), server_default="quotation-app", nullable=False),
        sa.Column("source_event_id", sa.String(length=64), nullable=False),
        sa.Column("notification_type", sa.String(length=64), nullable=False),
        sa.Column("recipient_profile_id", sa.String(length=64), nullable=True),
        sa.Column("recipient_email", sa.String(length=320), nullable=False),
        sa.Column("brand_id", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.String(length=1000), nullable=False),
        sa.Column("severity", sa.String(length=16), server_default="info", nullable=False),
        sa.Column("action_url", sa.String(length=512), nullable=True),
        sa.Column("aggregate_type", sa.String(length=64), nullable=True),
        sa.Column("aggregate_id", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", JSON_VARIANT, nullable=False),
        sa.Column("is_read", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_service",
            "source_event_id",
            "notification_type",
            "recipient_email",
            name="uq_notification_dedupe",
        ),
    )
    op.create_index("ix_notifications_source_event_id", "notifications", ["source_event_id"])
    op.create_index("ix_notifications_notification_type", "notifications", ["notification_type"])
    op.create_index("ix_notifications_recipient_profile_id", "notifications", ["recipient_profile_id"])
    op.create_index("ix_notifications_recipient_email", "notifications", ["recipient_email"])
    op.create_index("ix_notifications_brand_id", "notifications", ["brand_id"])
    op.create_index("ix_notifications_aggregate_type", "notifications", ["aggregate_type"])
    op.create_index("ix_notifications_aggregate_id", "notifications", ["aggregate_id"])
    op.create_index(
        "ix_notifications_recipient_inbox",
        "notifications",
        ["recipient_email", "is_read", "created_at"],
    )
    op.create_index("ix_notifications_brand_created", "notifications", ["brand_id", "created_at"])

    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("notification_id", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="5", nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_error", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["notification_id"], ["notifications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("notification_id", "channel", name="uq_delivery_channel"),
    )
    op.create_index("ix_notification_deliveries_notification_id", "notification_deliveries", ["notification_id"])
    op.create_index("ix_deliveries_pending", "notification_deliveries", ["status", "next_attempt_at"])

    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("recipient_email", sa.String(length=320), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("notification_category", sa.String(length=64), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recipient_email", "channel", "notification_category", name="uq_recipient_channel_category"),
    )
    op.create_index("ix_preferences_recipient", "notification_preferences", ["recipient_email"])


def downgrade() -> None:
    op.drop_table("notification_preferences")
    op.drop_table("notification_deliveries")
    op.drop_table("notifications")
