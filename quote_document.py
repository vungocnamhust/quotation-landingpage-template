from __future__ import annotations

from html import escape, unescape
from html.parser import HTMLParser
from typing import Annotated, Any, Dict, List, Literal, Optional, Union
import re
from urllib.parse import urlparse

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, TypeAdapter, field_validator, model_validator
from schemas.quote_document.brand import (
    AssetSelectionResult,
    BrandContentPolicy,
    BrandProfile,
    GenerationStatus,
    QuoteBaseModel,
)

SECTION_TYPES = (
    "hero",
    "overview_letter",
    "route_map",
    "itinerary",
    "hotel_plan",
    "pricing",
    "inclusions_exclusions",
    "booking_terms",
    "designer",
    "finalization",
)


class QuoteAssetRef(QuoteBaseModel):
    assetId: str = ""
    r2Key: str = ""
    url: str = ""
    status: str = "ready"
    altText: str = ""
    source: Literal["manual", "auto", "theme", ""] = ""
    resolverVersion: str = ""


class QuoteListItem(QuoteBaseModel):
    id: str
    text: str = ""


from schemas.v2.content_blocks import (
    BulletListContentBlock,
    CalloutContentBlock,
    ChecklistGroup,
    ChecklistGroupsContentBlock,
    ContentText,
    HTML_TAG_RE,
    ParagraphContentBlock,
    PaymentScheduleContentBlock,
    PaymentScheduleItem,
    QuoteContentBlock,
    QuoteTermItem,
    TermListContentBlock,
    TermListItem,
    TwoColumnListContentBlock,
    _ContentBlockModel,
    _HTML_TAG_RE,
    _SafeTermHtml,
    _content_text,
    sanitize_term_html,
    validate_quote_content_block,
)
from services.section_registry import (
    SECTION_REGISTRY,
    SECTION_TYPES,
    QuoteSection,
    SectionDefinition,
    SectionValidationError,
    build_default_sections,
    validate_quote_document_sections,
)
from adapters.legacy_rich_content import (
    LEGACY_RICH_DOCUMENT_FIELDS,
    build_rich_content_from_fact_sources,
    build_rich_content_from_legacy,
    legacy_html_to_plain_text,
    rich_content_values,
    strip_legacy_rich_document_fields,
)




class RendererAdapter(QuoteBaseModel):
    name: str
    supported_sections: List[str] = Field(default_factory=list)


class QuoteDocumentMeta(QuoteBaseModel):
    quotationId: str
    opportunityId: str = ""
    lang: str = "en"
    brandId: str = "vietnam_safar"
    version: int = 1
    template: str = "vietnam_luxury_brosure.html"
    revision: int = 1
    status: str = "draft"
    contentSchemaVersion: Literal[1] = 1
    contentProvenance: Dict[str, str] = Field(default_factory=dict)


class QuoteDocumentPresentation(QuoteBaseModel):
    renderer: Literal["quote-generator"] = "quote-generator"
    themeId: str = "brochure"
    layoutVersion: int = 1
    # Presentation-owned text only. Fact and content paths are never stored here.
    copyOverrides: Dict[str, str] = Field(default_factory=dict)
    # Quote-level display media takes precedence over fact/source media without
    # changing operational itinerary or stay facts.
    mediaOverrides: Dict[str, Any] = Field(default_factory=dict)
    # Audit data for deterministic defaults; public renderers ignore this.
    mediaDefaults: Dict[str, Any] = Field(default_factory=dict)
    identityOverrides: Dict[str, Any] = Field(default_factory=dict)


class QuoteDocumentBrand(QuoteBaseModel):
    name: str = ""
    domain: str = ""
    logo: QuoteAssetRef = Field(default_factory=QuoteAssetRef)
    colors: Dict[str, str] = Field(default_factory=dict)
    fonts: Dict[str, str] = Field(default_factory=dict)


class QuoteDocumentAssets(QuoteBaseModel):
    hero: QuoteAssetRef = Field(default_factory=QuoteAssetRef)
    itineraryDivider: QuoteAssetRef = Field(default_factory=QuoteAssetRef)
    staysDivider: QuoteAssetRef = Field(default_factory=QuoteAssetRef)
    hotelDivider: QuoteAssetRef = Field(default_factory=QuoteAssetRef)
    themeOrnaments: Dict[str, QuoteAssetRef] = Field(default_factory=dict)


class QuoteDocumentTraveler(QuoteBaseModel):
    customerName: str = ""
    guestProfile: str = ""
    travelStyle: str = ""
    nationality: str = ""
    adults: int = 0
    children: int = 0


class QuoteDocumentTrip(QuoteBaseModel):
    title: str = ""
    lede: str = ""
    durationText: str = ""
    routeText: str = ""
    travelDates: str = ""
    quotationNumber: str = ""
    priceBasis: str = ""


class QuoteDocumentNarrative(QuoteBaseModel):
    coverKicker: str = ""
    heroMeta1: str = ""
    heroMeta2: str = ""
    journeyOverviewTitle: str = ""
    letterHighlight: str = ""
    letterGreeting: str = ""
    letterIntro: str = ""
    letterBody2: str = ""
    letterOutro: str = ""
    letterSignOff: str = ""
    letterSender: str = ""
    footerText: str = ""


class QuoteDocumentRouteSegment(QuoteBaseModel):
    id: str
    destinationId: str = ""
    dayStart: int | None = None
    dayEnd: int | None = None
    displayName: str = ""
    daysLabel: str = ""
    nightsLabel: str = ""
    hotelName: str = ""
    hotelDateRange: str = ""
    hotelImage: QuoteAssetRef = Field(default_factory=QuoteAssetRef)
    mapSegmentDesc: str = ""
    mapSegmentDuration: str = ""
    coords: List[Any] = Field(default_factory=list)


class QuoteDocumentRoute(QuoteBaseModel):
    title: str = ""
    description: str = ""
    staySegments: List[QuoteDocumentRouteSegment] = Field(default_factory=list)


class QuoteDocumentDayImages(QuoteBaseModel):
    hero: QuoteAssetRef = Field(default_factory=QuoteAssetRef)
    small1: QuoteAssetRef = Field(default_factory=QuoteAssetRef)
    small2: QuoteAssetRef = Field(default_factory=QuoteAssetRef)
    carousel: List[QuoteAssetRef] = Field(default_factory=list)


class QuoteDocumentDestinationRef(QuoteBaseModel):
    id: str
    name: str = ""
    slug: str = ""
    coordinates: List[float] | None = None
    mediaPrefix: str | None = None
    defaultMediaPrefix: str | None = None


class QuoteDocumentItineraryDay(QuoteBaseModel):
    id: str
    dayNumber: int
    dayDate: str = ""
    segmentCity: str = ""
    destinationRef: QuoteDocumentDestinationRef | None = None
    overnightRef: QuoteDocumentDestinationRef | None = None
    title: str = ""
    description: List[str] = Field(default_factory=list)
    overnight: str = ""
    meals: List[str] = Field(default_factory=list)
    activities: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    labelHighlights: str = "Highlights:"
    labelNotes: str = "Notes:"
    layoutType: str = "single"
    images: QuoteDocumentDayImages = Field(default_factory=QuoteDocumentDayImages)


class QuoteDocumentItinerary(QuoteBaseModel):
    title: str = ""
    description: str = ""
    days: List[QuoteDocumentItineraryDay] = Field(default_factory=list)


class QuoteDocumentHotel(QuoteBaseModel):
    id: str
    city: str = ""
    name: str = ""
    introduction: str = ""
    hotelDate: str = ""
    tel: str = ""
    roomType: str = ""
    destinationRef: QuoteDocumentDestinationRef | None = None
    hotelImage: QuoteAssetRef = Field(default_factory=QuoteAssetRef)
    roomImage: QuoteAssetRef = Field(default_factory=QuoteAssetRef)


class QuoteDocumentStays(QuoteBaseModel):
    hotels: List[QuoteDocumentHotel] = Field(default_factory=list)
    roomNotes: str = ""


class QuoteDocumentPricingOption(QuoteBaseModel):
    id: str
    label: str = ""
    currency: str = ""
    perTravelerAmountMinor: int | None = None
    groupTotalAmountMinor: int | None = None
    # Release snapshots created before the typed V2 pricing contract retain
    # their already-formatted values. New V2 writes never populate these.
    legacyPerPersonText: str = ""
    legacyTotalText: str = ""
    isConfirmedMainOption: bool = False
    isAlternativeOption: bool = False

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_option(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        normalized.setdefault("label", normalized.get("name") or normalized.get("category") or "")
        legacy_per_person = str(normalized.get("perPersonText") or "")
        legacy_total = str(normalized.get("totalText") or "")
        normalized.setdefault("legacyPerPersonText", legacy_per_person)
        normalized.setdefault("legacyTotalText", legacy_total)
        normalized.setdefault("isConfirmedMainOption", bool(normalized.pop("confirmedMainOption", False)))
        normalized.setdefault("isAlternativeOption", bool(normalized.pop("alternativeOption", False)))
        if not normalized.get("currency"):
            currency_match = re.search(r"\b(USD|VND|EUR|GBP|AUD)\b", f"{legacy_per_person} {legacy_total}", re.IGNORECASE)
            normalized["currency"] = currency_match.group(1).upper() if currency_match else ""
        return normalized


class QuoteDocumentPricing(QuoteBaseModel):
    kicker: str = ""
    title: str = ""
    description: str = ""
    ctaLabel: str = ""
    conditions: List[QuoteListItem] = Field(default_factory=list)
    options: List[QuoteDocumentPricingOption] = Field(default_factory=list)


class QuoteDocumentContentSection(QuoteBaseModel):
    blocks: List[QuoteContentBlock] = Field(default_factory=list)


class QuoteDocumentContent(QuoteBaseModel):
    sections: Dict[str, QuoteDocumentContentSection] = Field(default_factory=dict)



class QuoteDocumentDesigner(QuoteBaseModel):
    name: str = ""
    subtitle: str = ""
    kicker: str = ""
    signature: str = ""
    experience: str = ""
    quote: str = ""
    title: str = ""
    ctaBody: str = ""
    phone: str = ""
    email: str = ""
    image: QuoteAssetRef = Field(default_factory=QuoteAssetRef)
    # Calligraphy characters for the handwritten signature glyph in the letter section.
    signatureInitial: str | None = None


class QuoteDocumentLayout(QuoteBaseModel):
    sections: List[QuoteSection] = Field(default_factory=list)


class QuoteDocumentV1(QuoteBaseModel):
    meta: QuoteDocumentMeta
    presentation: QuoteDocumentPresentation = Field(default_factory=QuoteDocumentPresentation)
    brand: QuoteDocumentBrand = Field(default_factory=QuoteDocumentBrand)
    assets: QuoteDocumentAssets = Field(default_factory=QuoteDocumentAssets)
    traveler: QuoteDocumentTraveler = Field(default_factory=QuoteDocumentTraveler)
    trip: QuoteDocumentTrip = Field(default_factory=QuoteDocumentTrip)
    narrative: QuoteDocumentNarrative = Field(default_factory=QuoteDocumentNarrative)
    route: QuoteDocumentRoute = Field(default_factory=QuoteDocumentRoute)
    itinerary: QuoteDocumentItinerary = Field(default_factory=QuoteDocumentItinerary)
    stays: QuoteDocumentStays = Field(default_factory=QuoteDocumentStays)
    pricing: QuoteDocumentPricing = Field(default_factory=QuoteDocumentPricing)
    designer: QuoteDocumentDesigner = Field(default_factory=QuoteDocumentDesigner)
    content: QuoteDocumentContent = Field(default_factory=QuoteDocumentContent)
    layout: QuoteDocumentLayout = Field(default_factory=QuoteDocumentLayout)
    generationStatus: GenerationStatus = Field(default_factory=GenerationStatus)
    viewOverrides: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {"web": {}, "pdf": {}}
    )

    @model_validator(mode="before")
    @classmethod
    def require_rich_content_schema(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        legacy_rich_keys = {"inclusions", "exclusions", "bookingTerms", "finalization"}
        present_legacy_keys = sorted(legacy_rich_keys.intersection(normalized))
        if present_legacy_keys:
            raise ValueError(
                "Legacy rich document fields are not allowed after cutover: "
                + ", ".join(present_legacy_keys)
                + ". Run scripts/migrate_v2_rich_content.py before loading this document."
            )
        content = normalized.get("content")
        if not isinstance(content, dict) or not isinstance(content.get("sections"), dict):
            raise ValueError("content.sections is required; run the V2 rich-content migration before cutover.")
        meta = dict(normalized.get("meta") or {})
        if meta.get("contentSchemaVersion") != 1:
            raise ValueError("meta.contentSchemaVersion=1 is required; run the V2 rich-content migration before cutover.")
        normalized["meta"] = meta
        return normalized

    @model_validator(mode="after")
    def ensure_layout_defaults(self) -> "QuoteDocumentV1":
        if not self.layout.sections:
            self.layout.sections = build_default_sections()
        else:
            normalized: List[QuoteSection] = []
            seen_ids: set[str] = set()
            for index, section in enumerate(sorted(self.layout.sections, key=lambda item: item.order or 0), 1):
                if section.type not in SECTION_TYPES:
                    continue
                if section.id in seen_ids:
                    section.id = f"{section.type}-{index}"
                seen_ids.add(section.id)
                section.order = index
                normalized.append(section)
            self.layout.sections = normalized or build_default_sections()
        return self


def rich_content_values(document: QuoteDocumentV1) -> Dict[str, Any]:
    """Extract renderer/legacy projections exclusively from typed blocks.

    This is intentionally a projection, never a fallback to retired document
    fields. V2 renderers consume the blocks directly; the legacy Jinja bridge
    uses this only while it remains a separate rendering surface.
    """
    sections = document.content.sections
    inclusions: list[str] = []
    exclusions: list[str] = []
    for block in sections.get("inclusions_exclusions", QuoteDocumentContentSection()).blocks:
        if block.type == "twoColumnList":
            inclusions.extend(block.leftItems)
            exclusions.extend(block.rightItems)

    booking_description = ""
    booking_items: list[dict[str, str]] = []
    for block in sections.get("booking_terms", QuoteDocumentContentSection()).blocks:
        if block.type == "paragraph" and not booking_description:
            booking_description = block.text
        elif block.type in {"termList", "paymentSchedule"}:
            booking_items.extend({"label": item.label, "body": item.body} for item in block.items)

    groups: list[dict[str, Any]] = []
    for block in sections.get("finalization", QuoteDocumentContentSection()).blocks:
        if block.type == "checklistGroups":
            groups.extend({"title": group.title, "items": list(group.items)} for group in block.groups)

    return {
        "inclusions": inclusions,
        "exclusions": exclusions,
        "bookingDescription": booking_description,
        "bookingItems": booking_items,
        "finalizationGroups": groups,
    }


class TripFactDay(QuoteBaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    day_number: int | None = None
    destination: str | None = None
    summary: str | None = None
    overnight: str | None = None
    meals: List[str] = Field(default_factory=list)
    highlights: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    sense_of_pace: str | None = None
    display_date: str | None = None


class CreateQuoteTripFacts(QuoteBaseModel):
    """Authoritative trip inputs only; editorial brochure copy lives in Content."""

    model_config = ConfigDict(extra="forbid")

    destinations: List[str] = Field(default_factory=list)
    start_date: str | None = None
    end_date: str | None = None
    duration_days: int | None = None
    duration_nights: int | None = None
    itinerary: List[TripFactDay] = Field(default_factory=list)
    special_requirements: List[str] = Field(default_factory=list)
    display_route_text: str | None = None
    display_travel_dates: str | None = None


SUPPORTED_PRICING_CURRENCIES = {"USD", "VND", "EUR", "GBP", "AUD"}


class CreateQuotePricingOptionFact(QuoteBaseModel):
    """Typed commercial option accepted by V2 Facts and Intake writes."""

    model_config = ConfigDict(extra="forbid")

    id: str = ""
    label: str = Field(min_length=1, max_length=160)
    currency: str
    per_traveler_amount_minor: int | None = Field(default=None, gt=0)
    group_total_amount_minor: int = Field(gt=0)
    per_adult_amount_minor: int | None = None
    per_child_amount_minor: int | None = None

    @model_validator(mode="before")
    @classmethod
    def sync_pricing_amounts(cls, data: Any) -> Any:
        if isinstance(data, dict):
            traveler_val = data.get("per_traveler_amount_minor")
            adult_val = data.get("per_adult_amount_minor")
            if traveler_val is None and adult_val is not None:
                data["per_traveler_amount_minor"] = adult_val
            elif adult_val is None and traveler_val is not None:
                data["per_adult_amount_minor"] = traveler_val
        return data

    @field_validator("per_traveler_amount_minor")
    @classmethod
    def require_positive_per_traveler(cls, value: int | None) -> int:
        if value is None or value <= 0:
            raise ValueError("per_traveler_amount_minor must be greater than 0")
        return value

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Pricing option label is required.")
        return normalized

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in SUPPORTED_PRICING_CURRENCIES:
            raise ValueError("Pricing option currency is unsupported.")
        return normalized


class CreateQuotePricingFacts(QuoteBaseModel):
    model_config = ConfigDict(extra="forbid")

    conditions: List[str] = Field(default_factory=list)
    options: List[CreateQuotePricingOptionFact] = Field(default_factory=list, max_length=4)


class CreateQuoteCustomerFacts(QuoteBaseModel):
    customer_name: str | None = None
    adults: int | None = None
    children: int | None = None
    nationality: str | None = None
    guest_profile: str | None = None
    travel_style: str | None = None
    market: str | None = None
    party_label: str | None = None
    greeting_name: str | None = None


class CreateQuoteHotelFact(QuoteBaseModel):
    accommodation_id: str | None = None
    destination: str | None = None
    name: str | None = None
    room_type: str | None = None
    check_in: str | None = None
    check_out: str | None = None
    intro: str | None = None
    phone: str | None = None
    display_city: str | None = None
    display_date: str | None = None
    hotel_asset: str | None = None
    room_asset: str | None = None


class CreateQuoteFactMediaSlot(QuoteBaseModel):
    fieldId: str = Field(min_length=1)
    value: Any


class CreateQuoteServiceFacts(QuoteBaseModel):
    hotels: List[CreateQuoteHotelFact] = Field(default_factory=list)
    inclusions: List[str] = Field(default_factory=list)
    exclusions: List[str] = Field(default_factory=list)
    room_notes: str | None = None


class CreateQuoteBookingTermFact(QuoteBaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str | None = None
    label: str | None = None
    body: str | None = None

    @field_validator("label", "body")
    @classmethod
    def require_plain_fact_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if "<" in normalized or ">" in normalized:
            raise ValueError("Booking/payment fact text must be plain text; migrate legacy HTML before cutover.")
        if len(normalized) > 4000:
            raise ValueError("Booking/payment fact text cannot exceed 4,000 characters.")
        return normalized


class CreateQuoteBookingFacts(QuoteBaseModel):
    title: str | None = None
    description: str | None = None
    items: List[CreateQuoteBookingTermFact] = Field(default_factory=list)


class CreateQuoteFinalizationFacts(QuoteBaseModel):
    required_title: str | None = None
    after_confirmation_title: str | None = None
    required_items: List[str] = Field(default_factory=list)
    after_confirmation_items: List[str] = Field(default_factory=list)


class CreateQuoteDesignerFacts(QuoteBaseModel):
    seller_subtitle: str | None = None
    designer_signature: str | None = "TRAVEL DESIGNER"
    designer_kicker: str | None = "YOUR JOURNEY DESIGNER"
    designer_quote: str | None = "I believe the desire to travel is contagious—and it is my privilege to turn that inspiration into thoughtfully designed journeys filled with meaningful experiences, authentic connections, and lasting memories"
    designer_experience: str | None = "Present throughout the planning, quietly working behind the journey."
    designer_title: str | None = "Let Us Shape the Final Details Together"
    cta_body: str | None = ""


class CreateQuoteSource(QuoteBaseModel):
    kind: Literal["manual", "dmc_handoff"] = "manual"
    handoff_id: str | None = None


class CreateQuotePresentationOptions(QuoteBaseModel):
    # template_id remains accepted only so old editor payloads can be migrated.
    template_id: str | None = None
    renderer: Literal["quote-generator"] = "quote-generator"
    theme_id: str = "brochure"
    layout_version: int = 1
    travel_designer_id: str | None = None


class CreateQuoteRequestV1(QuoteBaseModel):
    source: CreateQuoteSource = Field(default_factory=CreateQuoteSource)
    opportunity_id: str | None = None
    brand_id: str | None = None
    lang: str | None = None
    trip_facts: CreateQuoteTripFacts = Field(default_factory=CreateQuoteTripFacts)
    pricing_facts: CreateQuotePricingFacts = Field(default_factory=CreateQuotePricingFacts)
    customer_facts: CreateQuoteCustomerFacts = Field(default_factory=CreateQuoteCustomerFacts)
    service_facts: CreateQuoteServiceFacts = Field(default_factory=CreateQuoteServiceFacts)
    booking_facts: CreateQuoteBookingFacts = Field(default_factory=CreateQuoteBookingFacts)
    finalization_facts: CreateQuoteFinalizationFacts = Field(default_factory=CreateQuoteFinalizationFacts)
    designer_facts: CreateQuoteDesignerFacts = Field(default_factory=CreateQuoteDesignerFacts)
    factMediaSlots: List[CreateQuoteFactMediaSlot] = Field(default_factory=list)
    presentation_options: CreateQuotePresentationOptions = Field(default_factory=CreateQuotePresentationOptions)
    content_overrides: Dict[str, Any] = Field(default_factory=dict)
    asset_overrides: Dict[str, Any] = Field(default_factory=dict)
    generation_options: Dict[str, Any] = Field(default_factory=dict)
    retrieval_refs: List[Dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_language(self) -> "CreateQuoteRequestV1":
        return self



