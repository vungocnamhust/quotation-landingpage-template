from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from core.rules.catalog_vocab import OCCUPANCY_BASIS, PRICE_FOR, RATE_BASIS, UNIT
from schemas.v2.product import ChargeUnit
from schemas.v2.supplier import (
    SupplierCancellationPolicySchema,
    SupplierChildPolicySchema,
    SupplierPaymentTermsSchema,
)

OccupancyBasis = Literal["sgl", "dbl", "twn", "trpl", "quad", "na"]
PriceFor = Literal["adult", "child", "infant", "room", "vehicle", "guide", "group", "unit"]
RateBasis = Literal["net", "gross_commissionable"]
LifecycleStatus = Literal["draft", "active", "superseded", "expired"]
ReviewStatus = Literal["needs_review", "verified"]
DocumentType = Literal["rate_sheet", "contract", "amendment", "quotation", "promotion", "manual_note"]
Channel = Literal["email", "zalo", "whatsapp", "portal", "in_person", "internal"]

assert set(OccupancyBasis.__args__) == OCCUPANCY_BASIS
assert set(PriceFor.__args__) == PRICE_FOR
assert set(RateBasis.__args__) == RATE_BASIS
assert set(ChargeUnit.__args__) == UNIT

_MAX_BLACKOUTS = 30
_MAX_SUPPLEMENTS = 30
_MAX_LINES = 60


class BlackoutWindowSchema(BaseModel):
    """One entry of ``blackout_json`` — reason-tagged excluded date range."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    from_date: date = Field(alias="from")
    to_date: date = Field(alias="to")
    reason: str = Field(default="", max_length=120)

    @model_validator(mode="after")
    def _validate_range(self) -> "BlackoutWindowSchema":
        if self.from_date > self.to_date:
            raise ValueError("blackout 'from' must be <= 'to'")
        return self


class SupplementSchema(BaseModel):
    """Phụ lục A — one entry of ``supplements_json`` (T7)."""

    model_config = ConfigDict(extra="ignore")

    label: str = Field(min_length=1, max_length=120)
    applies_from: date
    applies_to: date
    amount_minor: int = Field(ge=0)
    price_for: PriceFor
    mandatory: bool = False
    note: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _validate_range(self) -> "SupplementSchema":
        if self.applies_from > self.applies_to:
            raise ValueError("supplement applies_from must be <= applies_to")
        return self


class RatePriceLineBaseSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    price_for: PriceFor
    occupancy_basis: OccupancyBasis = "na"
    unit: ChargeUnit
    tier_min_pax: int | None = Field(default=None, ge=1)
    tier_max_pax: int | None = Field(default=None, ge=1)
    amount_minor: int = Field(ge=0)
    note: str | None = Field(default=None, max_length=500)
    sort_order: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _validate_tier(self) -> "RatePriceLineBaseSchema":
        if self.tier_min_pax is not None and self.tier_max_pax is not None:
            if self.tier_min_pax > self.tier_max_pax:
                raise ValueError("tier_min_pax must be <= tier_max_pax")
        return self


class RatePriceLineCreateSchema(RatePriceLineBaseSchema):
    pass


class RatePriceLineResponseSchema(RatePriceLineBaseSchema):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int


class RateSourceCreateSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    supplier_id: str = Field(min_length=1, max_length=64)
    document_type: DocumentType = "manual_note"
    channel: Channel = "internal"
    file_ref: str | None = Field(default=None, max_length=255)
    effective_from: date | None = None
    effective_to: date | None = None
    received_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=2000)


class RateSourceResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    supplier_id: str
    document_type: str
    channel: str
    file_ref: str | None
    effective_from: date | None
    effective_to: date | None
    received_at: datetime | None
    notes: str | None


class RateAggregateBaseSchema(BaseModel):
    """Shared header fields for create/supersede/update payloads."""

    model_config = ConfigDict(extra="ignore")

    currency: str | None = Field(default=None, min_length=3, max_length=3)
    rate_basis: RateBasis
    commission_pct: int | None = Field(default=None, ge=0, le=10000)
    valid_from: date
    valid_to: date
    season_name: str | None = Field(default=None, max_length=120)
    blackout_json: list[BlackoutWindowSchema] = Field(default_factory=list, max_length=_MAX_BLACKOUTS)
    min_pax: int | None = Field(default=None, ge=1)
    max_pax: int | None = Field(default=None, ge=1)
    tax_included: bool = False
    tax_pct: int | None = Field(default=None, ge=0, le=10000)
    supplements_json: list[SupplementSchema] = Field(default_factory=list, max_length=_MAX_SUPPLEMENTS)
    inclusions_json: list[str] = Field(default_factory=list)
    exclusions_json: list[str] = Field(default_factory=list)
    payment_terms_json: SupplierPaymentTermsSchema | None = None
    cancellation_policy_json: SupplierCancellationPolicySchema | None = None
    child_policy_json: SupplierChildPolicySchema | None = None
    source_reference: str | None = Field(default=None, max_length=255)
    source_id: str | None = Field(default=None, max_length=64)
    source: RateSourceCreateSchema | None = None
    lines: list[RatePriceLineCreateSchema] = Field(default_factory=list, max_length=_MAX_LINES)

    @model_validator(mode="after")
    def _validate_boundaries(self) -> "RateAggregateBaseSchema":
        if self.valid_to < self.valid_from:
            raise ValueError("valid_to must be >= valid_from")
        if self.min_pax is not None and self.max_pax is not None and self.min_pax > self.max_pax:
            raise ValueError("min_pax must be <= max_pax")
        for blackout in self.blackout_json:
            if not (self.valid_from <= blackout.from_date and blackout.to_date <= self.valid_to):
                raise ValueError("blackout_json windows must be within [valid_from, valid_to]")
        for supplement in self.supplements_json:
            if not (self.valid_from <= supplement.applies_from and supplement.applies_to <= self.valid_to):
                raise ValueError("supplements_json applies range must be within [valid_from, valid_to]")
        return self


class RateCreateSchema(RateAggregateBaseSchema):
    product_id: str = Field(min_length=1, max_length=64)


class RateUpdateSchema(RateAggregateBaseSchema):
    """Full-replace payload — only accepted while the rate is 'draft' (§1.5)."""


class RateSupersedeSchema(RateAggregateBaseSchema):
    """Payload for the new version created by POST /rates/{id}/supersede."""


class RateResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: str
    currency: str
    rate_basis: str
    commission_pct: int | None
    valid_from: date
    valid_to: date
    season_name: str | None
    blackout_json: list[dict]
    min_pax: int | None
    max_pax: int | None
    tax_included: bool
    tax_pct: int | None
    supplements_json: list[dict]
    inclusions_json: list[str]
    exclusions_json: list[str]
    payment_terms_json: dict | None
    cancellation_policy_json: dict | None
    child_policy_json: dict | None
    version: int
    supersedes_rate_id: str | None
    lifecycle_status: str
    review_status: str
    validation_flags_json: list[str]
    source_id: str | None
    source_reference: str | None
    created_at: datetime
    updated_at: datetime
    lines: list[RatePriceLineResponseSchema] = Field(default_factory=list)
    source: RateSourceResponseSchema | None = None
    resolved_payment_terms_json: dict | None = None
    resolved_cancellation_policy_json: dict | None = None
    resolved_child_policy_json: dict | None = None
    inherited_from_supplier: dict[str, bool] = Field(default_factory=dict)


class RateListResponseSchema(BaseModel):
    items: list[RateResponseSchema]
    total: int
