from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Channel(str, Enum):
    INAPP_SSE = "INAPP_SSE"
    EMAIL = "EMAIL"
    WEBHOOK = "WEBHOOK"


class DeliveryStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SENT = "SENT"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    DEAD = "DEAD"


@dataclass
class DeliveryItem:
    id: str
    notification_id: str
    channel: Channel
    status: DeliveryStatus = DeliveryStatus.PENDING
    attempts: int = 0
    max_attempts: int = 5
    next_attempt_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_error: str | None = None
    sent_at: datetime | None = None


@dataclass
class NotificationItem:
    id: str
    source_service: str
    source_event_id: str
    notification_type: str
    recipient_email: str
    title: str
    body: str
    severity: str
    recipient_profile_id: str | None = None
    brand_id: str | None = None
    action_url: str | None = None
    aggregate_type: str | None = None
    aggregate_id: str | None = None
    metadata_json: dict[str, Any] = field(default_factory=dict)
    is_read: bool = False
    read_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deliveries: list[DeliveryItem] = field(default_factory=list)
