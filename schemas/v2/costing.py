"""V2 costing schemas (15.4) — dual-track workbench: sheet + lines + summary."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from core.rules.catalog_vocab import CATEGORY, SUBCATEGORY_BY_CATEGORY, TIME_BASIS, UNIT

BookingStatus = Literal["quoted", "on_hold", "to_request", "requested", "confirmed", "delivered", "cancelled"]
LineSource = Literal["manual", "ai_draft"]

_MAX_LINES_PER_SHEET = 500


class CostingSheetCreateSchema(BaseModel):
    """Body for ``POST /costing-sheets`` — exactly one anchor (chốt #1)."""

    model_config = ConfigDict(extra="ignore")

    request_id: str | None = Field(default=None, min_length=1, max_length=64)
    quotation_id: str | None = Field(default=None, min_length=1, max_length=64)
    currency: str | None = Field(default=None, min_length=3, max_length=3)

    @model_validator(mode="after")
    def _validate_single_anchor(self) -> "CostingSheetCreateSchema":
        if bool(self.request_id) == bool(self.quotation_id):
            raise ValueError("Exactly one of request_id or quotation_id is required.")
        return self


class CostingSettingsUpdateSchema(BaseModel):
    """Body for ``PUT /costing-sheets/{id}/settings``."""

    model_config = ConfigDict(extra="ignore")

    base_costing_revision: int = Field(ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    markup_rate_bps: int | None = Field(default=None, ge=0)
    rounding_increment_minor: int | None = Field(default=None, ge=0)


class AttachQuotationSchema(BaseModel):
    """Body for ``POST /costing-sheets/{id}/attach-quotation``."""

    model_config = ConfigDict(extra="ignore")

    quotation_id: str = Field(min_length=1, max_length=64)


class ServiceLineWriteSchema(BaseModel):
    """Shared shape for create/update — catalog pick XOR manual entry.

    Catalog pick: ``product_id`` + ``rate_id`` + ``price_line_id`` — server
    re-validates the rate/price-line and snapshots cost/unit/title from it.
    Manual entry: no ``product_id`` — ``category``/``title``/``unit``/
    ``time_basis``/``unit_cost_minor``/``cost_currency`` must be supplied directly.
    """

    model_config = ConfigDict(extra="ignore")

    base_costing_revision: int = Field(ge=0)

    day_number: int | None = Field(default=None, ge=1)
    service_date: date | None = None
    category: str | None = None
    subcategory: str | None = None
    title: str | None = Field(default=None, max_length=255)

    supplier_id: str | None = Field(default=None, max_length=64)
    product_id: str | None = Field(default=None, max_length=64)
    # Named ``rate_id`` here (the domain concept the client picks from) but
    # persisted/echoed back as ``tariff_id`` — see ServiceLineResponseSchema
    # below. This is a deliberate, frozen split, not drift (16.3 F-27):
    # ``service_lines.tariff_id`` is #D0's frozen LLM output contract
    # (14.0-dmc-catalog-and-booking-model.md §2.7, spec §6.1) and must not be
    # renamed. Do not "fix" this by unifying the names.
    rate_id: str | None = Field(default=None, max_length=64)
    price_line_id: int | None = None

    unit: str | None = None
    time_basis: str | None = None
    qty_unit: int = Field(default=1, ge=1)
    qty_time: int = Field(default=1, ge=1)

    unit_cost_minor: int | None = Field(default=None, ge=0)
    cost_currency: str | None = Field(default=None, min_length=3, max_length=3)
    fx_rate_ppm: int | None = Field(default=None, ge=1)
    sell_override_minor: int | None = Field(default=None, ge=0)

    note: str | None = Field(default=None, max_length=2000)
    sort_order: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _validate_catalog_xor_manual(self) -> "ServiceLineWriteSchema":
        is_catalog_pick = bool(self.product_id)
        if is_catalog_pick:
            if not self.rate_id or self.price_line_id is None:
                raise ValueError("rate_id and price_line_id are required when product_id is set.")
        else:
            if not self.category or not self.title or not self.unit or not self.time_basis:
                raise ValueError("category, title, unit and time_basis are required for a manual line.")
            if self.unit_cost_minor is None or not self.cost_currency:
                raise ValueError("unit_cost_minor and cost_currency are required for a manual line.")
            if self.category not in CATEGORY:
                raise ValueError(f"Unknown category '{self.category}'.")
            if self.unit not in UNIT:
                raise ValueError(f"Unknown unit '{self.unit}'.")
            if self.time_basis not in TIME_BASIS:
                raise ValueError(f"Unknown time_basis '{self.time_basis}'.")
            allowed_subcategories = SUBCATEGORY_BY_CATEGORY.get(self.category, frozenset())
            if self.subcategory is not None and self.subcategory not in allowed_subcategories:
                raise ValueError(f"Unknown subcategory '{self.subcategory}' for category '{self.category}'.")
        return self


class ServiceLineCreateSchema(ServiceLineWriteSchema):
    pass


class ServiceLineUpdateSchema(ServiceLineWriteSchema):
    pass


class ProductRefSchema(BaseModel):
    """Read-time enrichment — fuel for the handoff engine (§1.6), never persisted."""

    model_config = ConfigDict(extra="ignore")

    property_id: str | None = None
    destination_id: str | None = None
    destination_name: str | None = None
    iata_code: str | None = None


class ServiceLineResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sheet_id: str
    day_number: int | None
    service_date: date | None
    category: str
    subcategory: str | None
    title: str
    supplier_id: str | None
    product_id: str | None
    # Mirrors db.models.costing.ServiceLine.tariff_id verbatim (frozen #D0
    # contract, see the comment on ServiceLineWriteSchema.rate_id above) —
    # the write side calls the same value ``rate_id``. Frontend code should
    # bridge through lib/rules/costingAdapter.ts rather than reading this
    # field name directly.
    tariff_id: str | None
    price_line_id: int | None
    unit: str
    time_basis: str
    qty_unit: int
    qty_time: int
    unit_cost_minor: int
    cost_currency: str
    fx_rate_ppm: int | None
    sell_override_minor: int | None
    booking_status: BookingStatus
    source: LineSource
    note: str | None
    sort_order: int
    created_at: datetime
    updated_at: datetime

    cost_minor: int = 0
    sell_minor: int = 0
    product_ref: ProductRefSchema | None = None


class DayTotalSchema(BaseModel):
    day_number: int | None
    cost_minor: int
    sell_minor: int


class CategoryTotalSchema(BaseModel):
    category: str
    cost_minor: int
    sell_minor: int


class CostingSummarySchema(BaseModel):
    cost_total_minor: int
    sell_total_minor: int
    margin_minor: int
    margin_bps: int
    by_day: list[DayTotalSchema] = Field(default_factory=list)
    by_category: list[CategoryTotalSchema] = Field(default_factory=list)


class CostingSheetResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    quote_request_id: str | None
    quotation_id: str | None
    currency: str
    markup_rate_bps: int
    rounding_increment_minor: int
    costing_revision: int
    created_at: datetime
    updated_at: datetime


class CostingSheetFindResponseSchema(BaseModel):
    sheet: CostingSheetResponseSchema | None = None


class CostingWorkbenchResponseSchema(BaseModel):
    sheet: CostingSheetResponseSchema
    items: list[ServiceLineResponseSchema] = Field(default_factory=list)
    summary: CostingSummarySchema
