from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    url: str = ""
    status: str = "ready"


class QuoteListItem(QuoteBaseModel):
    id: str
    text: str = ""


class QuoteTermItem(QuoteBaseModel):
    id: str
    key: str = ""
    label: str = ""
    body: str = ""


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
    category: str = ""
    name: str = ""
    perPersonText: str = ""
    totalText: str = ""
    isTotal: bool = False
    isConfirmedMainOption: bool = False
    isAlternativeOption: bool = False


class QuoteDocumentPricing(QuoteBaseModel):
    kicker: str = ""
    title: str = ""
    description: str = ""
    ctaLabel: str = ""
    conditions: List[QuoteListItem] = Field(default_factory=list)
    options: List[QuoteDocumentPricingOption] = Field(default_factory=list)


class QuoteDocumentBookingTerms(QuoteBaseModel):
    kicker: str = ""
    title: str = ""
    description: str = ""
    items: List[QuoteTermItem] = Field(default_factory=list)


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


class QuoteDocumentFinalization(QuoteBaseModel):
    requiredTitle: str = "Final Details Required"
    afterConfirmationTitle: str = "After Confirmation"
    requiredItems: List[QuoteListItem] = Field(default_factory=list)
    afterConfirmation: List[QuoteListItem] = Field(default_factory=list)


class QuoteDocumentLayout(QuoteBaseModel):
    sections: List[QuoteSection] = Field(default_factory=list)


class QuoteDocumentV1(QuoteBaseModel):
    meta: QuoteDocumentMeta
    brand: QuoteDocumentBrand = Field(default_factory=QuoteDocumentBrand)
    assets: QuoteDocumentAssets = Field(default_factory=QuoteDocumentAssets)
    traveler: QuoteDocumentTraveler = Field(default_factory=QuoteDocumentTraveler)
    trip: QuoteDocumentTrip = Field(default_factory=QuoteDocumentTrip)
    narrative: QuoteDocumentNarrative = Field(default_factory=QuoteDocumentNarrative)
    route: QuoteDocumentRoute = Field(default_factory=QuoteDocumentRoute)
    itinerary: QuoteDocumentItinerary = Field(default_factory=QuoteDocumentItinerary)
    stays: QuoteDocumentStays = Field(default_factory=QuoteDocumentStays)
    pricing: QuoteDocumentPricing = Field(default_factory=QuoteDocumentPricing)
    inclusions: List[QuoteListItem] = Field(default_factory=list)
    exclusions: List[QuoteListItem] = Field(default_factory=list)
    bookingTerms: QuoteDocumentBookingTerms = Field(default_factory=QuoteDocumentBookingTerms)
    designer: QuoteDocumentDesigner = Field(default_factory=QuoteDocumentDesigner)
    finalization: QuoteDocumentFinalization = Field(default_factory=QuoteDocumentFinalization)
    layout: QuoteDocumentLayout = Field(default_factory=QuoteDocumentLayout)
    generationStatus: GenerationStatus = Field(default_factory=GenerationStatus)
    viewOverrides: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {"web": {}, "pdf": {}}
    )

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


class TripFactDay(QuoteBaseModel):
    day_number: int
    destination: str = ""
    summary: str = ""
    overnight: str = ""
    meals: List[str] = Field(default_factory=list)
    display_title: str = ""
    highlights: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    sense_of_pace: str = ""
    display_date: str = ""
    label_highlights: str = "Highlights:"
    label_notes: str = "Notes:"


class CreateQuoteTripFacts(QuoteBaseModel):
    title: str = ""
    subtitle: str = ""
    destinations: List[str] = Field(default_factory=list)
    start_date: str = ""
    end_date: str = ""
    duration_days: int = 0
    duration_nights: int = 0
    itinerary: List[TripFactDay] = Field(default_factory=list)
    special_requirements: List[str] = Field(default_factory=list)
    display_route_text: str = ""
    display_travel_dates: str = ""
    hero_meta_1: str = ""
    hero_meta_2: str = ""
    footer_text: str = ""
    overview_title: str = ""
    journey_overview_title: str = ""
    letter_highlight: str = ""
    letter_greeting: str = ""
    letter_intro: str = ""
    letter_body: str = ""
    letter_outro: str = ""
    letter_sign_off: str = ""
    letter_sender: str = ""
    route_title: str = ""
    route_description: str = ""
    itinerary_title: str = ""
    itinerary_description: str = ""
    cover_kicker: str = ""


class CreateQuotePricingOptionFact(QuoteBaseModel):
    category: str = ""
    name: str = ""
    per_person_text: str = ""
    total_text: str = ""
    is_total: bool = False
    is_confirmed_main_option: bool = False
    is_alternative_option: bool = False


class CreateQuotePricingFacts(QuoteBaseModel):
    currency: str = "USD"
    total_budget: Optional[float] = None
    price_basis: str = "Indicative pricing, subject to reconfirmation"
    option_label: str = "Main option"
    kicker: str = ""
    display_title: str = ""
    display_subtitle: str = ""
    cta_label: str = ""
    conditions: List[str] = Field(default_factory=list)
    options: List[CreateQuotePricingOptionFact] = Field(default_factory=list)


class CreateQuoteCustomerFacts(QuoteBaseModel):
    customer_name: str = ""
    adults: int = 2
    children: int = 0
    nationality: str = ""
    guest_profile: str = ""
    market: str = ""
    party_label: str = ""
    greeting_name: str = ""


class CreateQuoteHotelFact(QuoteBaseModel):
    destination: str = ""
    name: str = ""
    room_type: str = ""
    check_in: str = ""
    check_out: str = ""
    intro: str = ""
    phone: str = ""
    display_city: str = ""
    display_date: str = ""
    hotel_asset: str = ""
    room_asset: str = ""


class CreateQuoteServiceFacts(QuoteBaseModel):
    hotels: List[CreateQuoteHotelFact] = Field(default_factory=list)
    inclusions: List[str] = Field(default_factory=list)
    exclusions: List[str] = Field(default_factory=list)
    room_notes: str = ""


class CreateQuoteBookingTermFact(QuoteBaseModel):
    key: str = ""
    label: str = ""
    body: str = ""


class CreateQuoteBookingFacts(QuoteBaseModel):
    title: str = ""
    description: str = ""
    items: List[CreateQuoteBookingTermFact] = Field(default_factory=list)


class CreateQuoteFinalizationFacts(QuoteBaseModel):
    required_title: str = ""
    after_confirmation_title: str = ""
    required_items: List[str] = Field(default_factory=list)
    after_confirmation_items: List[str] = Field(default_factory=list)


class CreateQuoteSellerFacts(QuoteBaseModel):
    seller_name: str = ""
    seller_subtitle: str = ""
    seller_email: str = ""
    seller_phone: str = ""
    contact_web: str = ""
    designer_name: str = ""
    designer_signature: str = ""
    designer_kicker: str = ""
    designer_quote: str = ""
    designer_experience: str = ""
    designer_title: str = ""
    cta_body: str = ""
    designer_email: str = ""
    designer_phone: str = ""


class CreateQuoteRequestV1(QuoteBaseModel):
    opportunity_id: str = ""
    brand_id: str = "vietnam_safar"
    lang: str = "en"
    trip_facts: CreateQuoteTripFacts = Field(default_factory=CreateQuoteTripFacts)
    pricing_facts: CreateQuotePricingFacts = Field(default_factory=CreateQuotePricingFacts)
    customer_facts: CreateQuoteCustomerFacts = Field(default_factory=CreateQuoteCustomerFacts)
    service_facts: CreateQuoteServiceFacts = Field(default_factory=CreateQuoteServiceFacts)
    booking_facts: CreateQuoteBookingFacts = Field(default_factory=CreateQuoteBookingFacts)
    finalization_facts: CreateQuoteFinalizationFacts = Field(default_factory=CreateQuoteFinalizationFacts)
    seller_facts: CreateQuoteSellerFacts = Field(default_factory=CreateQuoteSellerFacts)
    retrieval_refs: List[Dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_language(self) -> "CreateQuoteRequestV1":
        if self.lang not in {"en", "vi", "ar"}:
            self.lang = "en"
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
        required_document_paths=["trip.title", "trip.lede", "assets.hero.url"],
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
        editor_schema={"fields": ["pricing.kicker", "pricing.title", "pricing.description", "pricing.conditions", "pricing.options"]},
    ),
    "inclusions_exclusions": SectionDefinition(
        type="inclusions_exclusions",
        label="Inclusions & Exclusions",
        web_anchor="inclusions_exclusions",
        pdf_anchor="inclusions_exclusions",
        required_document_paths=["inclusions", "exclusions"],
        editor_schema={"fields": ["inclusions", "exclusions"]},
    ),
    "booking_terms": SectionDefinition(
        type="booking_terms",
        label="Booking Terms",
        web_anchor="booking_terms",
        pdf_anchor="booking_terms",
        required_document_paths=["bookingTerms.items"],
        editor_schema={"fields": ["bookingTerms.kicker", "bookingTerms.title", "bookingTerms.description", "bookingTerms.items"]},
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
        required_document_paths=["finalization.requiredItems", "finalization.afterConfirmation"],
        editor_schema={"fields": ["finalization.requiredTitle", "finalization.afterConfirmationTitle", "finalization.requiredItems", "finalization.afterConfirmation"]},
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
