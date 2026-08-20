from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class RoomingSuggestionItemSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    en: str = Field(min_length=1, max_length=255)
    vi: str | None = Field(default=None, max_length=255)
    ar: str | None = Field(default=None, max_length=255)
    code: str | None = Field(default=None, max_length=64)


class RoomingHeuristicRuleBaseSchema(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=255)
    min_adults: int = Field(default=1, ge=1)
    max_adults: int | None = Field(default=None, ge=1)
    min_children: int = Field(default=0, ge=0)
    max_children: int | None = Field(default=None, ge=0)
    min_infants: int = Field(default=0, ge=0)
    max_infants: int | None = Field(default=None, ge=0)
    kid_age_condition: Literal["ANY", "ALL_UNDER_12", "ANY_12_AND_ABOVE", "NO_KIDS"] = Field(default="ANY")
    suggestions: list[dict[str, Any]] = Field(default_factory=list)
    min_rooms_formula: str | None = Field(default=None, max_length=64)
    priority: int = Field(default=0)
    is_active: bool = Field(default=True)


class RoomingHeuristicRuleCreateSchema(RoomingHeuristicRuleBaseSchema):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(min_length=2, max_length=64)


class RoomingHeuristicRuleUpdateSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=255)
    min_adults: int | None = Field(default=None, ge=1)
    max_adults: int | None = Field(default=None, ge=1)
    min_children: int | None = Field(default=None, ge=0)
    max_children: int | None = Field(default=None, ge=0)
    min_infants: int | None = Field(default=None, ge=0)
    max_infants: int | None = Field(default=None, ge=0)
    kid_age_condition: Literal["ANY", "ALL_UNDER_12", "ANY_12_AND_ABOVE", "NO_KIDS"] | None = None
    suggestions: list[dict[str, Any]] | None = None
    min_rooms_formula: str | None = Field(default=None, max_length=64)
    priority: int | None = None
    is_active: bool | None = None


class RoomingHeuristicRuleResponseSchema(RoomingHeuristicRuleBaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class RoomingHeuristicsListResponseSchema(BaseModel):
    items: list[RoomingHeuristicRuleResponseSchema]
    total: int


class RoomingEvaluationRequestSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    adults: int = Field(default=2, ge=1)
    children: int = Field(default=0, ge=0)
    kid_ages: list[int] = Field(default_factory=list)
    infants: int = Field(default=0, ge=0)
    lang: str = Field(default="en", max_length=8)


class RoomingEvaluationResponseSchema(BaseModel):
    matched_rule_id: str | None = None
    matched_rule_name: str | None = None
    min_estimated_rooms: int
    suggestions: list[str]
