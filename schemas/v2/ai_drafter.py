"""V2 AI Service Drafter request/response schemas (15.7 §1.6).

Request schemas alias to camelCase (matching ``schemas/catalog_ingest.py``'s convention);
response schemas stay snake_case — the frontend bridges through its own adapter layer.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from schemas.service_draft import DayDraftResult
from schemas.trip_profile import TripProfile

RunStatus = Literal["succeeded", "partial", "failed"]


class DraftDaySpecSchema(BaseModel):
    """Day -> destination/date anchor supplied by the caller (15.7 does not reach into the
    facts pipeline to rebuild the itinerary — the frontend already has it from the display/
    workspace view this dialog opens from)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    day_number: int = Field(alias="dayNumber", ge=1)
    destination_id: str = Field(alias="destinationId", min_length=1)
    service_date: date = Field(alias="serviceDate")


class AnalyzeRequestSchema(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    raw_text: str = Field(alias="rawText", min_length=1)


class AnalyzeResponseSchema(BaseModel):
    run_id: str
    trip_profile: TripProfile
    fallback_used: bool
    confidence_notes: list[str]


class DraftRequestSchema(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    run_id: str = Field(alias="runId")
    trip_profile: TripProfile = Field(alias="tripProfile")
    days: list[DraftDaySpecSchema] = Field(min_length=1)
    day_numbers: list[int] | None = Field(default=None, alias="dayNumbers")
    base_costing_revision: int = Field(alias="baseCostingRevision", ge=0)


class DraftDayOutcomeSchema(BaseModel):
    day_number: int
    lines_created: int
    draft: DayDraftResult | None = None
    error: str | None = None


class DraftResponseSchema(BaseModel):
    run_id: str
    status: RunStatus
    days_done: list[int]
    days_failed: list[int]
    day_outcomes: list[DraftDayOutcomeSchema]
    created_line_ids: list[str]
    manual_review_count: int


class AiRunSummarySchema(BaseModel):
    id: str
    agent_name: str
    status: RunStatus
    idempotency_key: str
    stats: dict[str, Any]
    created_at: str


class AiRunListResponseSchema(BaseModel):
    runs: list[AiRunSummarySchema]
