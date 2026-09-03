"""V2 AP reconciliation schemas (15.9) — supplier invoices, voucher matching, payments.

Request bodies accept camelCase (client convention) via ``Field(alias=...)`` +
``populate_by_name=True``. Responses stay snake_case like every other V2
surface (16.3 F-15/D7 precedent, see schemas/v2/costing.py) — no by-alias
serialization.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.rules.finance_rules import INVOICE_STATUSES, LINE_TYPES, MATCH_STATUSES, PAYMENT_METHODS

InvoiceStatus = Literal["draft", "received", "matched", "disputed", "approved", "paid", "void"]
LineType = Literal["service", "adjustment", "penalty", "fee"]
MatchStatus = Literal["unmatched", "auto_matched", "manual_matched", "waived", "disputed"]
PaymentMethod = Literal["bank_transfer", "cash", "card", "other"]

assert set(InvoiceStatus.__args__) == set(INVOICE_STATUSES)  # keep Literal vocab in sync with core rules
assert set(LineType.__args__) == set(LINE_TYPES)
assert set(MatchStatus.__args__) == set(MATCH_STATUSES)
assert set(PaymentMethod.__args__) == set(PAYMENT_METHODS)

_MAX_LINES_PER_INVOICE = 500


class SupplierInvoiceCreateSchema(BaseModel):
    """Body for ``POST /ap/invoices`` — always created as ``draft``."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    supplier_id: str = Field(alias="supplierId", min_length=1, max_length=64)
    invoice_number: str | None = Field(default=None, alias="invoiceNumber", max_length=64)
    invoice_date: date = Field(alias="invoiceDate")
    due_date: date | None = Field(default=None, alias="dueDate")
    currency: str = Field(min_length=3, max_length=3)
    gross_total_minor: int = Field(alias="grossTotalMinor", ge=0)
    tax_minor: int = Field(default=0, alias="taxMinor", ge=0)
    file_ref: str | None = Field(default=None, alias="fileRef", max_length=255)
    notes: str | None = Field(default=None, max_length=2000)


class SupplierInvoiceUpdateSchema(BaseModel):
    """Body for ``PUT /ap/invoices/{id}`` — header edit and/or ``action`` (§5.5 #4)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    base_invoice_revision: int = Field(alias="baseInvoiceRevision", ge=0)
    action: Literal["record", "void"] | None = None

    invoice_number: str | None = Field(default=None, alias="invoiceNumber", max_length=64)
    invoice_date: date | None = Field(default=None, alias="invoiceDate")
    due_date: date | None = Field(default=None, alias="dueDate")
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    gross_total_minor: int | None = Field(default=None, alias="grossTotalMinor", ge=0)
    tax_minor: int | None = Field(default=None, alias="taxMinor", ge=0)
    file_ref: str | None = Field(default=None, alias="fileRef", max_length=255)
    notes: str | None = Field(default=None, max_length=2000)


class SupplierInvoiceLineWriteSchema(BaseModel):
    """One line in the ``PUT .../lines`` replace-set (§5.5 #5)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    line_type: LineType = Field(default="service", alias="lineType")
    booking_id: str | None = Field(default=None, alias="bookingId", max_length=64)
    voucher_ref: str | None = Field(default=None, alias="voucherRef", max_length=24)
    description: str = Field(min_length=1, max_length=500)
    amount_minor: int = Field(alias="amountMinor")
    sort_order: int = Field(default=0, alias="sortOrder", ge=0)


class SupplierInvoiceLinesUpsertSchema(BaseModel):
    """Body for ``PUT /ap/invoices/{id}/lines`` — replace-set (KISS, like rate draft)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    base_invoice_revision: int = Field(alias="baseInvoiceRevision", ge=0)
    lines: list[SupplierInvoiceLineWriteSchema] = Field(default_factory=list, max_length=_MAX_LINES_PER_INVOICE)


class MatchLineRequestSchema(BaseModel):
    """Body for ``POST .../lines/{line_id}/match`` (§5.5 #6)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    base_invoice_revision: int = Field(alias="baseInvoiceRevision", ge=0)
    mode: Literal["auto", "manual"] = "manual"
    booking_line_id: str | None = Field(default=None, alias="bookingLineId", max_length=64)
    voucher_ref: str | None = Field(default=None, alias="voucherRef", max_length=24)
    tolerance_bps: int = Field(default=0, alias="toleranceBps", ge=0)


class LineActionRequestSchema(BaseModel):
    """Body for ``POST .../lines/{line_id}/unmatch|waive|dispute`` (§5.5 #7)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    base_invoice_revision: int = Field(alias="baseInvoiceRevision", ge=0)
    note: str | None = Field(default=None, max_length=500)


class ApproveInvoiceRequestSchema(BaseModel):
    """Body for ``POST /ap/invoices/{id}/approve`` (§5.5 #8)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    base_invoice_revision: int = Field(alias="baseInvoiceRevision", ge=0)


class PaymentAllocationInputSchema(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    invoice_id: str = Field(alias="invoiceId", min_length=1, max_length=64)
    # Sign is validated against the payment's own sign in the pure rules (§12.3 H2) — a
    # schema-level validator has no access to the sibling payment amount, so this only
    # rejects the one thing that's wrong under either sign: exactly zero.
    amount_minor: int = Field(alias="amountMinor")

    @field_validator("amount_minor")
    @classmethod
    def _amount_minor_not_zero(cls, value: int) -> int:
        if value == 0:
            raise ValueError("amount_minor must not be zero.")
        return value


class RecordPaymentRequestSchema(BaseModel):
    """Body for ``POST /ap/payments`` (§5.5 #9) — nguyên tử payment + allocations."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    supplier_id: str = Field(alias="supplierId", min_length=1, max_length=64)
    paid_at: date = Field(alias="paidAt")
    currency: str = Field(min_length=3, max_length=3)
    amount_minor: int = Field(alias="amountMinor")
    fx_rate_ppm: int | None = Field(default=None, alias="fxRatePpm", ge=1)
    method: PaymentMethod
    reference: str | None = Field(default=None, max_length=128)
    notes: str | None = Field(default=None, max_length=2000)
    allocations: list[PaymentAllocationInputSchema] = Field(default_factory=list, min_length=1)

    @field_validator("amount_minor")
    @classmethod
    def _amount_minor_not_zero(cls, value: int) -> int:
        if value == 0:
            raise ValueError("amount_minor must not be zero.")
        return value


class SupplierInvoiceLineResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: str
    line_type: LineType
    booking_id: str | None
    booking_line_id: str | None
    voucher_ref: str | None
    description: str
    amount_minor: int
    expected_cost_minor: int | None
    variance_minor: int | None
    match_status: MatchStatus
    match_issues_json: list[str] = Field(default_factory=list)
    match_note: str | None
    sort_order: int
    created_at: datetime
    updated_at: datetime

    # Read-time enrichment (never persisted here) — sheet-currency variance view (§1.2).
    variance_sheet_minor: int | None = None


class ApPaymentAllocationResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    payment_id: str
    invoice_id: str
    amount_minor: int
    created_at: datetime

    # Read-time enrichment (§12.5 H4) — not a column; computed at payment time from the
    # invoice's matched lines and carried into the outbox payload + this response only.
    fx_variance_sheet_minor: int | None = None


class SupplierInvoiceResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    supplier_id: str
    invoice_number: str | None
    invoice_date: date
    received_at: datetime
    due_date: date | None
    currency: str
    gross_total_minor: int
    tax_minor: int
    status: InvoiceStatus
    invoice_revision: int
    file_ref: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    lines: list[SupplierInvoiceLineResponseSchema] = Field(default_factory=list)
    allocations: list[ApPaymentAllocationResponseSchema] = Field(default_factory=list)

    allocated_minor: int = 0
    balance_minor: int = 0


class SupplierInvoiceListItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    supplier_id: str
    invoice_number: str | None
    invoice_date: date
    due_date: date | None
    currency: str
    gross_total_minor: int
    status: InvoiceStatus
    matched_line_count: int = 0
    total_line_count: int = 0


class SupplierInvoiceListResponseSchema(BaseModel):
    items: list[SupplierInvoiceListItemSchema] = Field(default_factory=list)


class VoucherCandidateSchema(BaseModel):
    """A live booking_line candidate for matching, sourced from ``get_line_by_voucher_ref``."""

    model_config = ConfigDict(from_attributes=True)

    booking_line_id: str
    booking_id: str
    voucher_ref: str | None
    title_snapshot: str
    service_date: date | None
    status: str
    expected_cost_minor: int
    cost_currency_snapshot: str
    fx_rate_ppm_snapshot: int | None


class ApPaymentResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    supplier_id: str
    payment_code: str
    paid_at: date
    currency: str
    amount_minor: int
    fx_rate_ppm: int | None
    method: PaymentMethod
    reference: str | None
    notes: str | None
    created_at: datetime

    allocations: list[ApPaymentAllocationResponseSchema] = Field(default_factory=list)
