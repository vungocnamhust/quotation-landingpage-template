"""CatalogIngestPayload + Clarification + ResolutionPlan (15.8 §1.6).

These are the typed shapes exchanged between the Extractor/Resolver agents and the ingestion
services. Extractor output is verbatim ``*_text`` fields (never a computed amount, date, or
policy shape) plus a mandatory ``source_quote`` per candidate — parsing into typed minor-unit
amounts, ISO dates/season windows, and the 15.1 cancellation-policy shape happens exclusively
in ``core/rules/ingest_parser.py``, never here and never by the LLM.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from core.rules.catalog_vocab import CATEGORY, OCCUPANCY_BASIS, PRICE_FOR, RATE_BASIS, TIME_BASIS, UNIT

CategoryHint = Literal[
    "accommodation", "transportation", "ticket", "flights", "guide",
    "guide_expense", "experience", "meal", "visa", "others",
]
UnitHint = Literal["room", "person", "vehicle", "group", "ticket", "flight_seat", "visa_case", "set"]
TimeBasisHint = Literal["night", "day", "trip"]
OccupancyHint = Literal["sgl", "dbl", "twn", "trpl", "quad", "na"]
PriceForHint = Literal["adult", "child", "infant", "room", "vehicle", "guide", "group", "unit"]
RateBasisHint = Literal["net", "gross_commissionable"]

assert set(CategoryHint.__args__) == CATEGORY
assert set(UnitHint.__args__) == UNIT
assert set(TimeBasisHint.__args__) == TIME_BASIS
assert set(OccupancyHint.__args__) == OCCUPANCY_BASIS
assert set(PriceForHint.__args__) == PRICE_FOR
assert set(RateBasisHint.__args__) == RATE_BASIS

_MAX_SOURCE_QUOTE = 200
_MAX_ITEMS = 40


class SourceQuotedModel(BaseModel):
    """Every candidate the Extractor emits must carry a verbatim excerpt of the raw text."""

    model_config = ConfigDict(extra="ignore")

    source_quote: str = Field(min_length=1, max_length=_MAX_SOURCE_QUOTE)


class SupplierCandidate(SourceQuotedModel):
    name_text: str = Field(min_length=1, max_length=255)
    type_hint: str | None = Field(default=None, max_length=64)
    destination_text: str | None = Field(default=None, max_length=255)
    contact_text: str | None = Field(default=None, max_length=500)


class ProductCandidate(SourceQuotedModel):
    title_text: str = Field(min_length=1, max_length=255)
    category_hint: CategoryHint | None = None
    subcategory_hint: str | None = Field(default=None, max_length=48)
    unit_hint: UnitHint | None = None
    time_basis_hint: TimeBasisHint | None = None
    destination_text: str | None = Field(default=None, max_length=255)


class PriceLineCandidate(SourceQuotedModel):
    price_for_hint: PriceForHint | None = None
    occupancy_hint: OccupancyHint | None = None
    tier_pax_text: str | None = Field(default=None, max_length=64)
    amount_text: str = Field(min_length=1, max_length=64)
    currency_text: str | None = Field(default=None, max_length=16)


class SupplementCandidate(SourceQuotedModel):
    label_text: str = Field(min_length=1, max_length=120)
    amount_text: str = Field(min_length=1, max_length=64)
    currency_text: str | None = Field(default=None, max_length=16)
    applies_text: str | None = Field(default=None, max_length=120)


class RateGroupCandidate(SourceQuotedModel):
    product_title_text: str = Field(min_length=1, max_length=255)
    validity_text: str = Field(min_length=1, max_length=120)
    rate_basis_hint: RateBasisHint | None = None
    price_lines: list[PriceLineCandidate] = Field(default_factory=list, max_length=_MAX_ITEMS)
    supplements: list[SupplementCandidate] = Field(default_factory=list, max_length=_MAX_ITEMS)
    blackout_text: str | None = Field(default=None, max_length=255)
    policy_text: str | None = Field(default=None, max_length=1000)


class UnresolvedItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    description: str = Field(min_length=1, max_length=300)
    reason: str | None = Field(default=None, max_length=200)
    source_quote: str | None = Field(default=None, max_length=_MAX_SOURCE_QUOTE)
    # JSON-pointer into the payload this item came from, when known — lets a clarification
    # answer be applied at exactly the right spot. None for extractor-level items that don't
    # map to one specific field (e.g. "covers more than one supplier").
    target_path: str | None = Field(default=None, max_length=255)


class DocMeta(BaseModel):
    model_config = ConfigDict(extra="ignore")

    detected_language: str | None = Field(default=None, max_length=8)
    document_type_guess: str | None = Field(default=None, max_length=64)
    note: str | None = Field(default=None, max_length=300)


class CatalogIngestPayload(BaseModel):
    """Extractor output — verbatim text candidates only, no computed values (15.8 chốt #3)."""

    model_config = ConfigDict(extra="ignore")

    supplier: SupplierCandidate | None = None
    products: list[ProductCandidate] = Field(default_factory=list, max_length=_MAX_ITEMS)
    rate_groups: list[RateGroupCandidate] = Field(default_factory=list, max_length=_MAX_ITEMS)
    unresolved: list[UnresolvedItem] = Field(default_factory=list, max_length=_MAX_ITEMS)
    covers_multiple_suppliers: bool = False
    doc_meta: DocMeta = Field(default_factory=DocMeta)


# --------------------------------------------------------------------------------------- Q&A

class Clarification(BaseModel):
    """One resolver question. ``target_path`` is a JSON pointer into the payload/edits overlay
    so an answer can be applied at exactly the right spot and re-parsed locally."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1, max_length=64)
    question: str = Field(min_length=1, max_length=_MAX_SOURCE_QUOTE)
    blocking: bool = True
    source_quote: str | None = Field(default=None, max_length=_MAX_SOURCE_QUOTE)
    options: list[str] | None = Field(default=None, max_length=10)
    target_path: str = Field(min_length=1, max_length=255)


# ---------------------------------------------------------------------------- Resolution plan

ResolutionEntityType = Literal["supplier", "product", "rate"]
ResolutionAction = Literal["create", "update", "supersede_rate", "skip_duplicate", "needs_input"]


class ResolutionEntry(BaseModel):
    """One per-entity proposal from the Resolver — advisory only. ``resolution_service`` (code)
    re-verifies every entry deterministically before anything is staged as ``ready``
    (15.8 chốt #5): ``matched_id`` is only trusted when it is in the run's allowlist."""

    model_config = ConfigDict(extra="ignore")

    entity_ref: str = Field(
        min_length=1,
        max_length=255,
        description=(
            "JSON-pointer style reference to the payload item this entry is about: "
            "'/supplier' for the supplier, '/products/{index}' for a products[] item, "
            "'/rate_groups/{index}' for a rate_groups[] item — e.g. '/products/0'."
        ),
    )
    entity_type: ResolutionEntityType
    action: ResolutionAction
    matched_id: str | None = Field(default=None, max_length=64)
    evidence: str = Field(min_length=1, max_length=160)
    clarifications: list[Clarification] = Field(default_factory=list, max_length=10)


class ResolutionPlan(BaseModel):
    model_config = ConfigDict(extra="ignore")

    entries: list[ResolutionEntry] = Field(default_factory=list, max_length=_MAX_ITEMS)


# ------------------------------------------------------------------------------ API contracts
# (15.8 §1.7 — 7 operations). Requests use camelCase aliases (repo convention); responses stay
# snake_case, mirroring costing's ApplyPricingResponseSchema (16.3 F-15/D7).

SourceChannel = Literal["email", "zalo", "whatsapp", "portal", "in_person", "internal"]
SourceDocumentType = Literal["rate_sheet", "contract", "amendment", "quotation", "promotion", "manual_note"]
IngestionBatchStatus = Literal["draft", "needs_clarification", "ready", "committed", "rejected", "archived"]


class IngestionBatchCreateRequestSchema(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    raw_text: str = Field(alias="rawText", min_length=1)
    source_channel: SourceChannel = Field(alias="sourceChannel")
    source_document_type: SourceDocumentType = Field(alias="sourceDocumentType")


class IngestionBatchAnswersRequestSchema(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    answers: dict[str, Any] = Field(default_factory=dict)
    base_batch_revision: int = Field(alias="baseBatchRevision", ge=0)


class IngestionBatchEditsRequestSchema(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    edits: dict[str, Any] = Field(default_factory=dict)
    base_batch_revision: int = Field(alias="baseBatchRevision", ge=0)


class IngestionBatchCommitRequestSchema(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    base_batch_revision: int = Field(alias="baseBatchRevision", ge=0)
    acknowledge_unresolved: bool = Field(default=False, alias="acknowledgeUnresolved")


class IngestionBatchRejectRequestSchema(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    base_batch_revision: int = Field(alias="baseBatchRevision", ge=0)
    reason: str | None = Field(default=None, max_length=500)


class IngestionBatchResponseSchema(BaseModel):
    id: str
    status: IngestionBatchStatus
    raw_text: str
    source_channel: str
    source_document_type: str
    payload: dict[str, Any]
    parsed: dict[str, Any]
    resolution: dict[str, Any] | None
    conversation: list[Any]
    operator_edits: dict[str, Any]
    commit_result: dict[str, Any] | None
    error: dict[str, Any] | None
    batch_revision: int
    created_at: datetime
    updated_at: datetime


class IngestionBatchSummarySchema(BaseModel):
    id: str
    status: IngestionBatchStatus
    source_channel: str
    source_document_type: str
    unresolved_count: int
    products_count: int
    rate_groups_count: int
    created_at: datetime
    updated_at: datetime


class IngestionBatchListResponseSchema(BaseModel):
    items: list[IngestionBatchSummarySchema]
    total: int
