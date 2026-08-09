from __future__ import annotations

from html import escape, unescape
from html.parser import HTMLParser
from typing import Annotated, Any, Dict, List, Literal, Optional, Union
import re
from urllib.parse import urlparse

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, TypeAdapter, field_validator, model_validator


class QuoteBaseModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


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


class BrandContentPolicy(QuoteBaseModel):
    tone: str = ""
    vocabulary: List[str] = Field(default_factory=list)
    avoid: List[str] = Field(default_factory=list)
    legal_default: str = ""
    image_style: str = ""


class BrandProfile(QuoteBaseModel):
    brand_id: str
    display_name: str
    domain: str = ""
    logo: str = ""
    colors: Dict[str, str] = Field(default_factory=dict)
    fonts: Dict[str, str] = Field(default_factory=dict)
    content_policy: BrandContentPolicy = Field(default_factory=BrandContentPolicy)


class GenerationStatus(QuoteBaseModel):
    narrative: Literal["generated", "fallback", "manual"] = "fallback"
    assets: Literal["generated", "fallback", "manual"] = "fallback"
    warnings: List[str] = Field(default_factory=list)


class AssetSelectionResult(QuoteBaseModel):
    hero: str = ""
    destinations: Dict[str, List[str]] = Field(default_factory=dict)
    hotels: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    dividers: Dict[str, str] = Field(default_factory=dict)


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


class _SafeTermHtml(HTMLParser):
    allowed_tags = {"p", "ul", "ol", "li", "strong", "em", "br", "a"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in self.allowed_tags:
            return
        if tag != "a":
            self.parts.append(f"<{tag}>")
            return
        href = next((value or "" for name, value in attrs if name == "href"), "")
        parsed = urlparse(href)
        if parsed.scheme not in {"http", "https", "mailto"}:
            self.parts.append("<a>")
            return
        self.parts.append(f'<a href="{escape(href, quote=True)}">')

    def handle_endtag(self, tag: str) -> None:
        if tag in self.allowed_tags and tag != "br":
            self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        self.parts.append(escape(data))


def sanitize_term_html(value: str) -> str:
    parser = _SafeTermHtml()
    parser.feed(value)
    parser.close()
    return "".join(parser.parts)


class QuoteTermItem(QuoteBaseModel):
    id: str
    key: str = ""
    label: str = ""
    body: str = ""

    @field_validator("body")
    @classmethod
    def sanitize_body(cls, value: str) -> str:
        return sanitize_term_html(value)


class QuoteSection(QuoteBaseModel):
    id: str
    type: Literal[
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
    ]
    enabled: bool = True
    order: int = 0
    props: Dict[str, Any] = Field(default_factory=dict)


class SectionDefinition(QuoteBaseModel):
    type: str
    label: str
    props_schema: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    editor_schema: Dict[str, Any] = Field(default_factory=dict)
    web_anchor: str = ""
    pdf_anchor: str = ""
    required_document_paths: List[str] = Field(default_factory=list)
    allow_multiple: bool = False


class SectionValidationError(QuoteBaseModel):
    sectionId: str
    sectionType: str
    code: str
    message: str
    path: str


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
    hotelDivider: QuoteAssetRef = Field(default_factory=QuoteAssetRef)
    themeOrnaments: Dict[str, QuoteAssetRef] = Field(default_factory=dict)


class QuoteDocumentTraveler(QuoteBaseModel):
    customerName: str = ""
    guestProfile: str = ""
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


class QuoteDocumentItineraryDay(QuoteBaseModel):
    id: str
    dayNumber: int
    dayDate: str = ""
    segmentCity: str = ""
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


class _ContentBlockModel(QuoteBaseModel):
    """Base class for the canonical, layout-independent content block union."""

    model_config = ConfigDict(extra="forbid")


def _content_text(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("Content text cannot be blank.")
    if len(normalized) > 4000:
        raise ValueError("Content block strings cannot exceed 4,000 characters.")
    if "<" in normalized or ">" in normalized:
        raise ValueError("Rich content blocks cannot contain HTML.")
    return normalized


ContentText = Annotated[str, BeforeValidator(_content_text), Field(min_length=1, max_length=4000)]


class ParagraphContentBlock(_ContentBlockModel):
    type: Literal["paragraph"]
    text: ContentText


class BulletListContentBlock(_ContentBlockModel):
    type: Literal["bulletList"]
    items: List[ContentText] = Field(min_length=1, max_length=40)


class TwoColumnListContentBlock(_ContentBlockModel):
    type: Literal["twoColumnList"]
    leftTitle: ContentText
    leftItems: List[ContentText] = Field(default_factory=list, max_length=40)
    rightTitle: ContentText
    rightItems: List[ContentText] = Field(default_factory=list, max_length=40)

    @model_validator(mode="after")
    def require_a_column_item(self) -> "TwoColumnListContentBlock":
        if not self.leftItems and not self.rightItems:
            raise ValueError("A twoColumnList block requires at least one column item.")
        return self


class TermListItem(_ContentBlockModel):
    label: ContentText
    body: ContentText


class TermListContentBlock(_ContentBlockModel):
    type: Literal["termList"]
    items: List[TermListItem] = Field(min_length=1, max_length=24)


class PaymentScheduleItem(_ContentBlockModel):
    label: ContentText
    body: ContentText


class PaymentScheduleContentBlock(_ContentBlockModel):
    type: Literal["paymentSchedule"]
    items: List[PaymentScheduleItem] = Field(min_length=1, max_length=24)


class CalloutContentBlock(_ContentBlockModel):
    type: Literal["callout"]
    text: ContentText


class ChecklistGroup(_ContentBlockModel):
    title: ContentText
    items: List[ContentText] = Field(min_length=1, max_length=40)



class ChecklistGroupsContentBlock(_ContentBlockModel):
    type: Literal["checklistGroups"]
    groups: List[ChecklistGroup] = Field(min_length=1, max_length=12)


QuoteContentBlock = Annotated[
    Union[
        ParagraphContentBlock,
        BulletListContentBlock,
        TwoColumnListContentBlock,
        TermListContentBlock,
        PaymentScheduleContentBlock,
        CalloutContentBlock,
        ChecklistGroupsContentBlock,
    ],
    Field(discriminator="type"),
]
_QUOTE_CONTENT_BLOCK_ADAPTER = TypeAdapter(QuoteContentBlock)


def validate_quote_content_block(value: Any) -> Any:
    """Validate one canonical block; used for generated, patched, and migrated values."""
    return _QUOTE_CONTENT_BLOCK_ADAPTER.validate_python(value)


class QuoteDocumentContentSection(QuoteBaseModel):
    blocks: List[QuoteContentBlock] = Field(default_factory=list)


class QuoteDocumentContent(QuoteBaseModel):
    sections: Dict[str, QuoteDocumentContentSection] = Field(default_factory=dict)


_LEGACY_HTML_TAG_RE = re.compile(r"</?([a-zA-Z0-9]+)(?:\s[^>]*)?>")
_LEGACY_HTML_ALLOWED_TAGS = {"p", "ul", "ol", "li", "strong", "em", "br", "a"}


class _LegacyHtmlText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"p", "li", "br"} and self.parts:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def value(self) -> str:
        return "\n".join(line.strip() for line in "".join(self.parts).splitlines() if line.strip()).strip()


def legacy_html_to_plain_text(value: str) -> str:
    """Strict migration-only conversion; unsupported markup is a hard cutoff."""
    for match in _LEGACY_HTML_TAG_RE.finditer(value):
        if match.group(1).lower() not in _LEGACY_HTML_ALLOWED_TAGS:
            raise ValueError(f"Unsupported legacy HTML tag <{match.group(1)}>")
    parser = _LegacyHtmlText()
    parser.feed(unescape(value))
    parser.close()
    return parser.value()


def build_rich_content_from_legacy(value: Dict[str, Any]) -> Dict[str, Any]:
    """Migration-only conversion of allowlisted legacy markup.

    Runtime creation and rendering must use ``build_rich_content_from_fact_sources``;
    keeping this function separate prevents legacy HTML from silently re-entering
    the canonical document after cutover.
    """
    def legacy_plain(item: Any) -> str:
        raw = str(item.get("text") if isinstance(item, dict) else item or "").strip()
        return legacy_html_to_plain_text(raw) if raw else ""

    inclusions = [legacy_plain(item) for item in value.get("inclusions") or []]
    exclusions = [legacy_plain(item) for item in value.get("exclusions") or []]
    terms = value.get("bookingTerms") if isinstance(value.get("bookingTerms"), dict) else {}
    finalization = value.get("finalization") if isinstance(value.get("finalization"), dict) else {}
    term_items = [
        {"label": str(item.get("label") or item.get("key") or "").strip(), "body": legacy_html_to_plain_text(str(item.get("body") or ""))}
        for item in terms.get("items") or [] if isinstance(item, dict)
    ]
    term_items = [item for item in term_items if item["label"] and item["body"]]
    required = [legacy_plain(item) for item in finalization.get("requiredItems") or []]
    after = [legacy_plain(item) for item in finalization.get("afterConfirmation") or []]
    sections: Dict[str, Any] = {}
    if inclusions or exclusions:
        sections["inclusions_exclusions"] = {"blocks": [{"type": "twoColumnList", "leftTitle": "Inclusions", "leftItems": [item for item in inclusions if item], "rightTitle": "Exclusions", "rightItems": [item for item in exclusions if item]}]}
    booking_blocks: list[dict[str, Any]] = []
    if str(terms.get("description") or "").strip():
        booking_blocks.append({"type": "paragraph", "text": legacy_html_to_plain_text(str(terms.get("description") or ""))})
    if term_items:
        booking_blocks.append({"type": "termList", "items": term_items})
    if booking_blocks:
        sections["booking_terms"] = {"blocks": booking_blocks}
    groups = []
    if required:
        groups.append({"title": legacy_plain(finalization.get("requiredTitle") or "Final Details Required"), "items": required})
    if after:
        groups.append({"title": legacy_plain(finalization.get("afterConfirmationTitle") or "After Confirmation"), "items": after})
    if groups:
        sections["finalization"] = {"blocks": [{"type": "checklistGroups", "groups": groups}]}
    return {"sections": sections}


LEGACY_RICH_DOCUMENT_FIELDS = ("inclusions", "exclusions", "bookingTerms", "finalization")


def strip_legacy_rich_document_fields(value: Dict[str, Any]) -> Dict[str, Any]:
    """Remove retired rich-content fields after the one-time migration."""
    normalized = dict(value)
    for field in LEGACY_RICH_DOCUMENT_FIELDS:
        normalized.pop(field, None)
    return normalized


def build_rich_content_from_fact_sources(value: Dict[str, Any]) -> Dict[str, Any]:
    """Materialize structured presentation blocks from approved Fact values only.

    This boundary accepts plain factual/legal source strings, never HTML. It is
    intentionally deterministic: no editorial text is copied from trip facts.
    """
    inclusions = [str(item.get("text") if isinstance(item, dict) else item or "").strip() for item in value.get("inclusions") or []]
    exclusions = [str(item.get("text") if isinstance(item, dict) else item or "").strip() for item in value.get("exclusions") or []]
    terms = value.get("bookingTerms") if isinstance(value.get("bookingTerms"), dict) else {}
    finalization = value.get("finalization") if isinstance(value.get("finalization"), dict) else {}

    def plain(value: Any) -> str:
        return _content_text(str(value or ""))

    sections: Dict[str, Any] = {}
    if inclusions or exclusions:
        sections["inclusions_exclusions"] = {"blocks": [{
            "type": "twoColumnList",
            "leftTitle": "Inclusions",
            "leftItems": [plain(item) for item in inclusions if item],
            "rightTitle": "Exclusions",
            "rightItems": [plain(item) for item in exclusions if item],
        }]}

    booking_blocks: list[dict[str, Any]] = []
    if str(terms.get("description") or "").strip():
        booking_blocks.append({"type": "paragraph", "text": plain(terms.get("description"))})
    term_items = [
        {"label": plain(item.get("label") or item.get("key")), "body": plain(item.get("body"))}
        for item in terms.get("items") or []
        if isinstance(item, dict) and (item.get("label") or item.get("key")) and item.get("body")
    ]
    if term_items:
        booking_blocks.append({"type": "termList", "items": term_items})
    if booking_blocks:
        sections["booking_terms"] = {"blocks": booking_blocks}

    required = [str(item.get("text") if isinstance(item, dict) else item or "").strip() for item in finalization.get("requiredItems") or []]
    after = [str(item.get("text") if isinstance(item, dict) else item or "").strip() for item in finalization.get("afterConfirmation") or []]
    groups = []
    if required:
        groups.append({"title": plain(finalization.get("requiredTitle") or "Final Details Required"), "items": [plain(item) for item in required if item]})
    if after:
        groups.append({"title": plain(finalization.get("afterConfirmationTitle") or "After Confirmation"), "items": [plain(item) for item in after if item]})
    if groups:
        sections["finalization"] = {"blocks": [{"type": "checklistGroups", "groups": groups}]}
    return {"sections": sections}


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
    per_traveler_amount_minor: int = Field(gt=0)
    group_total_amount_minor: int = Field(gt=0)

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
    designer_signature: str | None = None
    designer_kicker: str | None = None
    designer_quote: str | None = None
    designer_experience: str | None = None
    designer_title: str | None = None
    cta_body: str | None = None


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


def build_default_sections() -> List[QuoteSection]:
    return [
        QuoteSection(id="hero", type="hero", enabled=True, order=1),
        QuoteSection(id="overview_letter", type="overview_letter", enabled=True, order=2),
        QuoteSection(id="route_map", type="route_map", enabled=True, order=3),
        QuoteSection(id="itinerary", type="itinerary", enabled=True, order=4),
        QuoteSection(id="hotel_plan", type="hotel_plan", enabled=True, order=5),
        QuoteSection(id="pricing", type="pricing", enabled=True, order=6),
        QuoteSection(id="inclusions_exclusions", type="inclusions_exclusions", enabled=True, order=7),
        QuoteSection(id="booking_terms", type="booking_terms", enabled=True, order=8),
        QuoteSection(id="designer", type="designer", enabled=True, order=9),
        QuoteSection(id="finalization", type="finalization", enabled=True, order=10),
    ]


SECTION_REGISTRY: Dict[str, SectionDefinition] = {
    "hero": SectionDefinition(
        type="hero",
        label="Hero",
        web_anchor="hero",
        pdf_anchor="hero",
        # V2 canonical documents store selected media as an approved R2 key.
        # A public release resolves that key to a branded opaque media URL, so
        # requiring a pre-resolved external URL would reject a valid V2 asset.
        required_document_paths=["trip.title", "trip.lede", "assets.hero"],
        editor_schema={"fields": ["trip.title", "trip.lede", "assets.hero"]},
    ),
    "overview_letter": SectionDefinition(
        type="overview_letter",
        label="Overview Letter",
        web_anchor="overview_letter",
        pdf_anchor="overview_letter",
        required_document_paths=["narrative.letterIntro", "narrative.letterBody2"],
        editor_schema={"fields": ["narrative.letterGreeting", "narrative.letterIntro", "narrative.letterBody2", "narrative.letterOutro"]},
    ),
    "route_map": SectionDefinition(
        type="route_map",
        label="Route Map",
        web_anchor="route_map",
        pdf_anchor="route_map",
        required_document_paths=["route.staySegments"],
        editor_schema={"fields": ["route.title", "route.description", "route.staySegments"]},
    ),
    "itinerary": SectionDefinition(
        type="itinerary",
        label="Itinerary",
        web_anchor="itinerary",
        pdf_anchor="itinerary",
        required_document_paths=["itinerary.days"],
        editor_schema={"fields": ["itinerary.title", "itinerary.description", "itinerary.days"]},
    ),
    "hotel_plan": SectionDefinition(
        type="hotel_plan",
        label="Hotel Plan",
        web_anchor="hotel_plan",
        pdf_anchor="hotel_plan",
        required_document_paths=["stays.hotels"],
        editor_schema={"fields": ["stays.hotels", "stays.roomNotes"]},
    ),
    "pricing": SectionDefinition(
        type="pricing",
        label="Pricing",
        web_anchor="pricing",
        pdf_anchor="pricing",
        required_document_paths=["pricing.options"],
        editor_schema={"fields": ["pricing.conditions", "pricing.options"]},
    ),
    "inclusions_exclusions": SectionDefinition(
        type="inclusions_exclusions",
        label="Inclusions & Exclusions",
        web_anchor="inclusions_exclusions",
        pdf_anchor="inclusions_exclusions",
        required_document_paths=["content.sections.inclusions_exclusions.blocks"],
        editor_schema={"fields": ["content.sections.inclusions_exclusions.blocks"]},
    ),
    "booking_terms": SectionDefinition(
        type="booking_terms",
        label="Booking Terms",
        web_anchor="booking_terms",
        pdf_anchor="booking_terms",
        required_document_paths=["content.sections.booking_terms.blocks"],
        editor_schema={"fields": ["content.sections.booking_terms.blocks"]},
    ),
    "designer": SectionDefinition(
        type="designer",
        label="Designer",
        web_anchor="designer",
        pdf_anchor="designer",
        required_document_paths=["designer.name"],
        editor_schema={"fields": ["designer.name", "designer.signature", "designer.title", "designer.experience", "designer.quote", "designer.phone", "designer.email", "designer.image"]},
    ),
    "finalization": SectionDefinition(
        type="finalization",
        label="Finalization",
        web_anchor="finalization",
        pdf_anchor="finalization",
        required_document_paths=["content.sections.finalization.blocks"],
        editor_schema={"fields": ["content.sections.finalization.blocks"]},
    ),
}


def _path_exists(payload: Any, path: str) -> bool:
    current = payload
    for part in path.split("."):
        if isinstance(current, BaseModel):
            current = getattr(current, part, None)
            continue
        if isinstance(current, dict):
            current = current.get(part)
            continue
        if isinstance(current, list):
            if not part.isdigit():
                return bool(current)
            index = int(part)
            current = current[index] if 0 <= index < len(current) else None
            continue
        return False
    if isinstance(current, list):
        return len(current) > 0
    if isinstance(current, BaseModel):
        current = current.model_dump(mode="json")
    if isinstance(current, dict) and {"assetId", "r2Key", "url"}.intersection(current):
        return bool(current.get("assetId") or current.get("r2Key") or current.get("url"))
    return current not in (None, "", {}, [])


def validate_quote_document_sections(document: QuoteDocumentV1 | dict[str, Any]) -> List[SectionValidationError]:
    errors: List[SectionValidationError] = []
    if isinstance(document, dict):
        raw_sections = (((document.get("layout") or {}).get("sections")) if isinstance(document.get("layout"), dict) else None) or []
        seen_types: Dict[str, str] = {}
        for index, raw_section in enumerate(raw_sections):
            if not isinstance(raw_section, dict):
                errors.append(
                    SectionValidationError(
                        sectionId=f"section-{index + 1}",
                        sectionType="",
                        code="invalid_section_payload",
                        message="Each section must be an object payload.",
                        path=f"layout.sections.{index}",
                    )
                )
                continue
            section_type = str(raw_section.get("type") or "")
            section_id = str(raw_section.get("id") or section_type or f"section-{index + 1}")
            definition = SECTION_REGISTRY.get(section_type)
            if definition is None:
                errors.append(
                    SectionValidationError(
                        sectionId=section_id,
                        sectionType=section_type,
                        code="unknown_section_type",
                        message=f"Section type '{section_type}' is not registered.",
                        path=f"layout.sections.{index}.type",
                    )
                )
                continue
            if not definition.allow_multiple and section_type in seen_types:
                errors.append(
                    SectionValidationError(
                        sectionId=section_id,
                        sectionType=section_type,
                        code="duplicate_section_type",
                        message=f"Section type '{section_type}' can only appear once.",
                        path=f"layout.sections.{index}.type",
                    )
                )
            else:
                seen_types[section_type] = section_id
        if errors:
            return errors

    quote_document = document if isinstance(document, QuoteDocumentV1) else QuoteDocumentV1.model_validate(document)
    seen_types: Dict[str, str] = {}

    for index, section in enumerate(quote_document.layout.sections):
        definition = SECTION_REGISTRY.get(section.type)
        path_prefix = f"layout.sections.{index}"
        if definition is None:
            errors.append(
                SectionValidationError(
                    sectionId=section.id,
                    sectionType=section.type,
                    code="unknown_section_type",
                    message=f"Section type '{section.type}' is not registered.",
                    path=f"{path_prefix}.type",
                )
            )
            continue
        if not definition.allow_multiple and section.type in seen_types:
            errors.append(
                SectionValidationError(
                    sectionId=section.id,
                    sectionType=section.type,
                    code="duplicate_section_type",
                    message=f"Section type '{section.type}' can only appear once.",
                    path=f"{path_prefix}.type",
                )
            )
        else:
            seen_types[section.type] = section.id
        if not definition.web_anchor or not definition.pdf_anchor:
            errors.append(
                SectionValidationError(
                    sectionId=section.id,
                    sectionType=section.type,
                    code="missing_renderer_anchor",
                    message=f"Section type '{section.type}' is missing a web/pdf renderer anchor.",
                    path=f"{path_prefix}.type",
                )
            )
        allowed_props = set(definition.props_schema.keys())
        extra_props = sorted(set(section.props.keys()) - allowed_props)
        if extra_props:
            errors.append(
                SectionValidationError(
                    sectionId=section.id,
                    sectionType=section.type,
                    code="invalid_props",
                    message=f"Section type '{section.type}' does not accept props: {', '.join(extra_props)}.",
                    path=f"{path_prefix}.props",
                )
            )
        if not section.enabled:
            continue
        for required_path in definition.required_document_paths:
            if not _path_exists(quote_document, required_path):
                errors.append(
                    SectionValidationError(
                        sectionId=section.id,
                        sectionType=section.type,
                        code="missing_required_document_data",
                        message=f"Section type '{section.type}' requires '{required_path}' to be populated.",
                        path=required_path,
                    )
                )
    return errors
