from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SupplierType = Literal["direct", "dmc", "wholesaler", "bedbank", "ota", "freelancer", "gov", "other"]
SupplierPreferredStatus = Literal["preferred", "recommended", "standard", "backup", "do_not_use"]
SupplierQualityTier = Literal["ultra_luxury", "luxury", "premium", "standard", "value"]
PaymentMethod = Literal["bank_transfer", "cash", "card", "other"]


class SupplierContactSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    person: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=64)
    whatsapp: str | None = Field(default=None, max_length=64)
    zalo: str | None = Field(default=None, max_length=64)
    website: str | None = Field(default=None, max_length=255)


class SupplierPaymentTermsSchema(BaseModel):
    """Phụ lục A.1"""

    model_config = ConfigDict(extra="ignore")

    deposit_percent: int | None = Field(default=None, ge=0, le=100)
    deposit_due_days_after_confirm: int | None = Field(default=None, ge=0)
    balance_due_days_before_service: int | None = Field(default=None, ge=0)
    method: PaymentMethod | None = None
    note: str | None = Field(default=None, max_length=500)


class SupplierCancellationTierSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    days_before_service_min: int = Field(ge=0)
    penalty_percent: int = Field(ge=0, le=100)


class SupplierCancellationPolicySchema(BaseModel):
    """Phụ lục A.2"""

    model_config = ConfigDict(extra="ignore")

    tiers: list[SupplierCancellationTierSchema] = Field(default_factory=list)
    no_show_penalty_percent: int = Field(default=100, ge=0, le=100)
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _validate_tiers(self) -> "SupplierCancellationPolicySchema":
        ordered = sorted(self.tiers, key=lambda tier: tier.days_before_service_min, reverse=True)
        seen_days: set[int] = set()
        previous_penalty: int | None = None
        for tier in ordered:
            if tier.days_before_service_min in seen_days:
                raise ValueError("cancellation tiers must not overlap on days_before_service_min")
            seen_days.add(tier.days_before_service_min)
            if previous_penalty is not None and tier.penalty_percent < previous_penalty:
                raise ValueError("cancellation penalty_percent must increase as days_before_service_min decreases")
            previous_penalty = tier.penalty_percent
        return self


class SupplierChildAgeBandSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    age_min: int = Field(ge=0, le=17)
    age_max: int = Field(ge=0, le=17)
    charge_percent: int = Field(ge=0, le=100)

    @model_validator(mode="after")
    def _validate_range(self) -> "SupplierChildAgeBandSchema":
        if self.age_min > self.age_max:
            raise ValueError("age_min must be <= age_max")
        return self


class SupplierChildPolicySchema(BaseModel):
    """Phụ lục A.3"""

    model_config = ConfigDict(extra="ignore")

    bands: list[SupplierChildAgeBandSchema] = Field(default_factory=list)
    infant_age_max: int | None = Field(default=None, ge=0, le=3)
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _validate_bands(self) -> "SupplierChildPolicySchema":
        ordered = sorted(self.bands, key=lambda band: band.age_min)
        previous_max: int | None = None
        for band in ordered:
            if previous_max is not None and band.age_min <= previous_max:
                raise ValueError("child_policy bands must not overlap in age range")
            previous_max = band.age_max
        return self


class SupplierBaseSchema(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    supplier_type: SupplierType
    country: str | None = Field(default=None, max_length=64)
    city: str | None = Field(default=None, max_length=64)
    destination_id: str | None = Field(default=None, max_length=64)
    default_currency: str = Field(min_length=3, max_length=3)
    preferred_status: SupplierPreferredStatus = "standard"
    quality_tier: SupplierQualityTier | None = None
    contact_json: SupplierContactSchema = Field(default_factory=SupplierContactSchema)
    payment_terms_json: SupplierPaymentTermsSchema | None = None
    cancellation_policy_json: SupplierCancellationPolicySchema | None = None
    child_policy_json: SupplierChildPolicySchema | None = None
    bank_details_ref: str | None = Field(default=None, max_length=255)
    tax_code: str | None = Field(default=None, max_length=64)
    credit_terms_days: int = Field(default=0, ge=0)
    internal_notes: str | None = Field(default=None, max_length=2000)


class SupplierCreateSchema(SupplierBaseSchema):
    model_config = ConfigDict(extra="ignore")


class SupplierUpdateSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    supplier_type: SupplierType | None = None
    country: str | None = Field(default=None, max_length=64)
    city: str | None = Field(default=None, max_length=64)
    destination_id: str | None = Field(default=None, max_length=64)
    default_currency: str | None = Field(default=None, min_length=3, max_length=3)
    preferred_status: SupplierPreferredStatus | None = None
    quality_tier: SupplierQualityTier | None = None
    contact_json: SupplierContactSchema | None = None
    payment_terms_json: SupplierPaymentTermsSchema | None = None
    cancellation_policy_json: SupplierCancellationPolicySchema | None = None
    child_policy_json: SupplierChildPolicySchema | None = None
    bank_details_ref: str | None = Field(default=None, max_length=255)
    tax_code: str | None = Field(default=None, max_length=64)
    credit_terms_days: int | None = Field(default=None, ge=0)
    internal_notes: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None


class SupplierResponseSchema(SupplierBaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SupplierListResponseSchema(BaseModel):
    items: list[SupplierResponseSchema]
    total: int
