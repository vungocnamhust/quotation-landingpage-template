from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class Severity(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class EventType(str, Enum):
    # Quote Request events
    QUOTE_REQUEST_CREATED = "quote_request.created"
    QUOTE_REQUEST_ASSIGNED = "quote_request.assigned"
    QUOTE_REQUEST_EDITED = "quote_request.edited"
    QUOTE_REQUEST_CONVERTED = "quote_request.converted"

    # Quotation events
    QUOTATION_CREATED = "quotation.created"
    QUOTATION_UPDATED = "quotation.updated"
    QUOTATION_PUBLICATION_QUEUED = "quotation.publication.queued"
    QUOTATION_PUBLICATION_COMPLETED = "quotation.publication.completed"
    QUOTATION_PUBLICATION_FAILED = "quotation.publication.failed"
    QUOTATION_PDF_READY = "quotation.pdf.ready"

    # AI & Content Draft events
    AI_DRAFT_COMPLETED = "ai.draft.completed"
    AI_DRAFT_FAILED = "ai.draft.failed"

    # DMC Agentic AI events (Future)
    AGENTIC_PLANNING_COMPLETED = "agentic.planning.completed"
    AGENTIC_COST_OPTIMIZATION_ALERT = "agentic.cost_optimization.alert"
    AGENTIC_SUPPLIER_QUOTE_RECEIVED = "agentic.supplier_quote.received"

    # System & Generic
    SYSTEM_ANNOUNCEMENT = "system.announcement"


class IntegrationEvent(BaseModel):
    event_id: str = Field(description="Unique event ID for deduplication (e.g. UUIDv4 or evt_*)")
    source_service: str = Field(default="quotation-app", description="Source microservice name")
    event_type: str = Field(description="Domain event name, e.g. quotation.pdf.ready")
    event_version: int = Field(default=1)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    aggregate_type: str = Field(description="'quotation' | 'quote_request' | 'agentic_run'")
    aggregate_id: str = Field(description="Identifier of the aggregate")
    brand_id: str | None = None
    actor_email: str | None = None
    correlation_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
