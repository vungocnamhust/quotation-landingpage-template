from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from core.rules.catalog_vocab import CATEGORY, TIME_BASIS, UNIT

Category = Literal[
    "accommodation",
    "transportation",
    "ticket",
    "flights",
    "guide",
    "guide_expense",
    "experience",
    "meal",
    "visa",
    "others",
]
ChargeUnit = Literal["room", "person", "vehicle", "group", "ticket", "flight_seat", "visa_case", "set"]
TimeBasis = Literal["night", "day", "trip"]

assert set(Category.__args__) == CATEGORY  # keep Literal and vocab SSOT in sync
assert set(ChargeUnit.__args__) == UNIT
assert set(TimeBasis.__args__) == TIME_BASIS

CategoryAttributeValue = str | int | bool
_MAX_CATEGORY_ATTRIBUTES = 20
_MAX_ATTRIBUTE_KEY_LENGTH = 48


def _validate_category_attributes(value: dict[str, CategoryAttributeValue]) -> dict[str, CategoryAttributeValue]:
    if len(value) > _MAX_CATEGORY_ATTRIBUTES:
        raise ValueError(f"category_attributes accepts at most {_MAX_CATEGORY_ATTRIBUTES} keys.")
    for key in value:
        if not key or len(key) > _MAX_ATTRIBUTE_KEY_LENGTH:
            raise ValueError(f"category_attributes key '{key}' must be 1-{_MAX_ATTRIBUTE_KEY_LENGTH} chars.")
    return value


class ProductBaseSchema(BaseModel):
    supplier_id: str | None = Field(default=None, max_length=64)
    property_id: str | None = Field(default=None, max_length=64)
    destination_id: str = Field(min_length=1, max_length=64)
    category: Category
    subcategory: str | None = Field(default=None, max_length=48)
    subcategory_note: str | None = Field(default=None, max_length=120)
    supplier_product_name: str | None = Field(default=None, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    unit: ChargeUnit | None = None
    time_basis: TimeBasis | None = None
    default_min_pax: int | None = Field(default=None, ge=1)
    default_max_pax: int | None = Field(default=None, ge=1)
    category_attributes: dict[str, CategoryAttributeValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_boundaries(self) -> "ProductBaseSchema":
        if self.default_min_pax is not None and self.default_max_pax is not None:
            if self.default_min_pax > self.default_max_pax:
                raise ValueError("default_min_pax must be <= default_max_pax")
        if self.property_id is not None and self.category != "accommodation":
            raise ValueError("property_id may only be set when category == 'accommodation'")
        if self.subcategory_note is not None and not (self.subcategory or "").startswith("other_"):
            raise ValueError("subcategory_note is only meaningful when subcategory is an other_* value")
        _validate_category_attributes(self.category_attributes)
        return self


class ProductCreateSchema(ProductBaseSchema):
    model_config = ConfigDict(extra="ignore")


class ProductUpdateSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    supplier_id: str | None = Field(default=None, max_length=64)
    property_id: str | None = Field(default=None, max_length=64)
    destination_id: str | None = Field(default=None, min_length=1, max_length=64)
    category: Category | None = None
    subcategory: str | None = Field(default=None, max_length=48)
    subcategory_note: str | None = Field(default=None, max_length=120)
    supplier_product_name: str | None = Field(default=None, max_length=255)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    unit: ChargeUnit | None = None
    time_basis: TimeBasis | None = None
    default_min_pax: int | None = Field(default=None, ge=1)
    default_max_pax: int | None = Field(default=None, ge=1)
    category_attributes: dict[str, CategoryAttributeValue] | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def _validate_boundaries(self) -> "ProductUpdateSchema":
        if self.default_min_pax is not None and self.default_max_pax is not None:
            if self.default_min_pax > self.default_max_pax:
                raise ValueError("default_min_pax must be <= default_max_pax")
        if self.subcategory_note is not None and not (self.subcategory or "").startswith("other_"):
            raise ValueError("subcategory_note is only meaningful when subcategory is an other_* value")
        if self.category_attributes is not None:
            _validate_category_attributes(self.category_attributes)
        return self


class ProductResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    supplier_id: str | None
    property_id: str | None
    destination_id: str
    category: str
    subcategory: str | None
    subcategory_note: str | None
    supplier_product_name: str | None
    title: str
    unit: str
    time_basis: str
    default_min_pax: int | None
    default_max_pax: int | None
    category_attributes: dict[str, CategoryAttributeValue]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProductListResponseSchema(BaseModel):
    items: list[ProductResponseSchema]
    total: int
