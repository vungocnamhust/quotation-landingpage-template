from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class NotificationItemSchema(BaseModel):
    id: str
    source_service: str
    source_event_id: str
    notification_type: str
    recipient_email: str
    recipient_profile_id: str | None = None
    brand_id: str | None = None
    title: str
    body: str
    severity: str
    action_url: str | None = None
    aggregate_type: str | None = None
    aggregate_id: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime


class NotificationListResponseSchema(BaseModel):
    items: list[NotificationItemSchema]
    total: int
    unread_count: int
    limit: int
    offset: int


class UnreadCountResponseSchema(BaseModel):
    unread_count: int


class MarkReadResponseSchema(BaseModel):
    success: bool
    notification_id: str
    is_read: bool


class MarkAllReadResponseSchema(BaseModel):
    success: bool
    marked_count: int
    unread_count: int = 0


class IngestEventResponseSchema(BaseModel):
    success: bool
    event_id: str
    notifications_created: int
