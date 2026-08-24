"""Pydantic contracts for Actionable Content Plan endpoints."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ContentActionResponse(BaseModel):
    id: str
    scope: str
    entityKey: str
    reasonCode: str
    automationPolicy: str
    state: str
    inheritedReferenceStatus: str
    draftId: str | None
    appliedDocumentRevision: int | None
    metadata: dict[str, Any]


class ContentActionPlanResponse(BaseModel):
    id: str
    quotationId: str
    predecessorQuotationId: str | None
    factsHash: str
    status: str
    acceptanceNote: str | None
    actions: list[ContentActionResponse]


class AcceptContentActionPlanRequest(BaseModel):
    note: str = Field(default="Accepted in Impact Center.", min_length=1, max_length=1000)


class ExecuteContentActionsRequest(BaseModel):
    planId: str = Field(min_length=1, max_length=64)
    actionIds: list[str] = Field(min_length=1, max_length=100)
    writingStyle: Literal["storytelling", "detailed"] = "storytelling"


class BypassContentActionsRequest(ExecuteContentActionsRequest):
    expectedRevision: int = Field(ge=1)


class ContentActionExecutionResponse(BaseModel):
    planId: str
    actionIds: list[str]
    draftIds: list[str]
    documentRevision: int
    mode: Literal["auto", "bypass"]
