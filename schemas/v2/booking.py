"""V2 booking schemas (15.6) — header + FROZEN/LIVE line snapshot + board."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from schemas.v2.supplier import SupplierCancellationPolicySchema, SupplierContactSchema, SupplierPaymentTermsSchema

BookingLineStatus = Literal["to_request", "requested", "confirmed", "delivered", "cancelled"]
BookingHeaderStatus = Literal["active", "completed", "cancelled"]
BookingHeaderMutableStatus = Literal["completed"]
BookingLineUrgency = Literal["overdue", "due_soon", "ok"]


class BookingCreateSchema(BaseModel):
    """Body for ``POST /bookings`` — deposit landed, snapshot the whole sheet."""

    model_config = ConfigDict(extra="ignore")

    quotation_id: str = Field(min_length=1, max_length=64)
    deposit_received_at: date
    customer_balance_due_date: date | None = None


class BookingHeaderUpdateSchema(BaseModel):
    """Body for ``PUT /bookings/{booking_id}``."""

    model_config = ConfigDict(extra="forbid")

    base_booking_revision: int = Field(ge=0)
    customer_balance_due_date: date | None = None
    status: BookingHeaderMutableStatus | None = None
    notes: str | None = Field(default=None, max_length=2000)


class BookingLineTransitionSchema(BaseModel):
    """Body for ``POST /bookings/{booking_id}/lines/{line_id}/transition``."""

    model_config = ConfigDict(extra="ignore")

    base_booking_revision: int = Field(ge=0)
    to: BookingLineStatus
    supplier_ref: str | None = Field(default=None, max_length=64)
    cancel_reason: str | None = Field(default=None, max_length=500)


class BookingLineOpsUpdateSchema(BaseModel):
    """Body for ``PUT /bookings/{booking_id}/lines/{line_id}`` — LIVE fields only.

    ``extra="forbid"``: a payload naming a FROZEN column (e.g.
    ``unit_cost_minor_snapshot``) must 422 explicitly (plan §1.6), not be
    silently dropped.
    """

    model_config = ConfigDict(extra="forbid")

    base_booking_revision: int = Field(ge=0)
    request_by_date: date | None = None
    assignee_email: str | None = Field(default=None, max_length=320)
    notes: str | None = Field(default=None, max_length=2000)
    supplier_ref: str | None = Field(default=None, max_length=64)


class BookingAddLineSchema(BaseModel):
    """Body for ``POST /bookings/{booking_id}/lines`` — amendment."""

    model_config = ConfigDict(extra="ignore")

    base_booking_revision: int = Field(ge=0)
    service_line_id: str = Field(min_length=1, max_length=64)


class BookingCancelSchema(BaseModel):
    """Body for ``POST /bookings/{booking_id}/cancel``."""

    model_config = ConfigDict(extra="ignore")

    base_booking_revision: int = Field(ge=0)
    reason: str = Field(min_length=1, max_length=500)


class BookingLineResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    booking_id: str
    source_service_line_id: str

    supplier_id_snapshot: str | None
    supplier_name_snapshot: str | None
    supplier_contact_snapshot_json: SupplierContactSchema | None
    title_snapshot: str
    category: str
    service_date: date | None
    unit: str
    time_basis: str
    qty_unit: int
    qty_time: int
    unit_cost_minor_snapshot: int
    cost_currency_snapshot: str
    fx_rate_ppm_snapshot: int | None
    sell_minor_snapshot: int
    payment_terms_snapshot_json: SupplierPaymentTermsSchema | None
    cancellation_policy_snapshot_json: SupplierCancellationPolicySchema | None

    status: BookingLineStatus
    request_by_date: date | None
    penalty_free_until: date | None
    deposit_due_date: date | None
    balance_due_date: date | None
    supplier_ref: str | None
    voucher_ref: str | None
    confirmed_at: datetime | None
    cancelled_at: datetime | None
    cancel_reason: str | None
    cancel_penalty_minor: int | None
    assignee_email: str | None
    notes: str | None
    sort_order: int
    created_at: datetime
    updated_at: datetime

    urgency: BookingLineUrgency | None = None


class BookingResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    quotation_id: str
    sheet_id: str
    booking_code: str
    status: BookingHeaderStatus
    deposit_received_at: date
    customer_balance_due_date: date | None
    party_label_snapshot: str | None
    travel_start_date: date | None
    travel_end_date: date | None
    booking_revision: int
    notes: str | None
    created_at: datetime
    updated_at: datetime


class BookingDetailResponseSchema(BaseModel):
    booking: BookingResponseSchema
    lines: list[BookingLineResponseSchema] = Field(default_factory=list)
    cash_flow_warnings: list[str] = Field(default_factory=list)


class BookingBoardItemSchema(BaseModel):
    line: BookingLineResponseSchema
    booking_id: str
    booking_code: str
    booking_revision: int
    quotation_id: str
    party_label_snapshot: str | None
    travel_start_date: date | None
    travel_end_date: date | None
    customer_balance_due_date: date | None
    cash_flow_warning: bool = False


class BookingBoardResponseSchema(BaseModel):
    items: list[BookingBoardItemSchema] = Field(default_factory=list)
