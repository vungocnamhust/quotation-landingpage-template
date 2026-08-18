from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class PartnerProfileBaseSchema(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    contact_name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=320)
    phone: str = Field(default="", max_length=64)
    market: str | None = Field(default=None, max_length=64)
    tier: str | None = Field(default="Standard", max_length=32)
    default_commission_rate: float = Field(default=10.0, ge=0.0, le=100.0)
    preferred_currency: str = Field(default="USD", max_length=16)
    notes: str | None = Field(default=None, max_length=2000)


class PartnerProfileCreateSchema(PartnerProfileBaseSchema):
    model_config = ConfigDict(extra="ignore")


class PartnerProfileUpdateSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    company_name: str | None = Field(default=None, min_length=1, max_length=255)
    contact_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: str | None = Field(default=None, min_length=3, max_length=320)
    phone: str | None = Field(default=None, max_length=64)
    market: str | None = Field(default=None, max_length=64)
    tier: str | None = Field(default=None, max_length=32)
    default_commission_rate: float | None = Field(default=None, ge=0.0, le=100.0)
    preferred_currency: str | None = Field(default=None, max_length=16)
    notes: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None


class PartnerProfileResponseSchema(PartnerProfileBaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PartnerProfileListResponseSchema(BaseModel):
    items: list[PartnerProfileResponseSchema]
    total: int
