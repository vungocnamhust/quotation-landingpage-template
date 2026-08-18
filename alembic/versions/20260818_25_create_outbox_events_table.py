"""create outbox_events table

Revision ID: 20260818_25
Revises: 20260817_24
Create Date: 2026-08-18 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from db.types import JSON_VARIANT


revision = "20260818_25"
down_revision = "20260817_24"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_id", sa.String(length=128), nullable=False),
        sa.Column("brand_id", sa.String(length=64), nullable=True),
        sa.Column("actor_email", sa.String(length=320), nullable=True),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("payload_json", JSON_VARIANT, nullable=False),
        sa.Column("status", sa.String(length=16), server_default="PENDING", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="5", nullable=False),
        sa.Column("last_error", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_outbox_events_pending", "outbox_events", ["status", "created_at"])
    op.create_index("ix_outbox_events_aggregate", "outbox_events", ["aggregate_type", "aggregate_id"])


def downgrade() -> None:
    op.drop_table("outbox_events")
