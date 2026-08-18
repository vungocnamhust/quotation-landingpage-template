from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.types import JSON_VARIANT
from notification.infrastructure.db.base import NotificationBase


class Notification(NotificationBase):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint(
            "source_service",
            "source_event_id",
            "notification_type",
            "recipient_email",
            name="uq_notification_dedupe",
        ),
        Index(
            "ix_notifications_recipient_inbox",
            "recipient_email",
            "is_read",
            "created_at",
        ),
        Index("ix_notifications_brand_created", "brand_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_service: Mapped[str] = mapped_column(String(64), nullable=False, default="quotation-app", server_default="quotation-app")
    source_event_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    notification_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    recipient_profile_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    recipient_email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    brand_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(String(1000), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="info", server_default="info")
    action_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    aggregate_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    aggregate_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict)

    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    deliveries: Mapped[list[NotificationDelivery]] = relationship(
        "NotificationDelivery",
        back_populates="notification",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class NotificationDelivery(NotificationBase):
    __tablename__ = "notification_deliveries"
    __table_args__ = (
        UniqueConstraint("notification_id", "channel", name="uq_delivery_channel"),
        Index("ix_deliveries_pending", "status", "next_attempt_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    notification_id: Mapped[str] = mapped_column(
        ForeignKey("notifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False)  # INAPP_SSE, EMAIL, WEBHOOK
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", server_default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=5, server_default="5")
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    notification: Mapped[Notification] = relationship(
        "Notification",
        back_populates="deliveries",
    )


class NotificationPreference(NotificationBase):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("recipient_email", "channel", "notification_category", name="uq_recipient_channel_category"),
        Index("ix_preferences_recipient", "recipient_email"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    recipient_email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    notification_category: Mapped[str] = mapped_column(String(64), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
