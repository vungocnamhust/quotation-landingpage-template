"""Pydantic schemas for Standalone Quotation Agent Workflow matching Spec 36."""

from __future__ import annotations

from typing import Any, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, model_validator
from pydantic import Field as pydantic_Field


class FrozenModel(BaseModel):
    """Base model configured to ignore extra fields for robustness on the landing page API."""

    model_config = ConfigDict(frozen=True, extra="ignore")


# --- Helpers & Shared Schema components ---


class Duration(FrozenModel):
    days: int
    nights: int
    label: str


class TravelDates(FrozenModel):
    startDate: str
    endDate: str
    displayText: str


class GuestComposition(FrozenModel):
    adults: int
    children: int
    totalGuests: int
    childrenAges: List[int]
    displayText: str


class TextSection(FrozenModel):
    heading: str
    paragraphs: List[str]


class ItineraryDay(FrozenModel):
    dayNumber: int = pydantic_Field(
        ge=1, description="Day number in the itinerary, starting from 1."
    )
    destination: str = pydantic_Field(description="Destination or primary location for this day.")
    summary: str = pydantic_Field(
        description=(
            "Luxury, cinematic summary describing the atmosphere and conceptual pacing of the day."
        )
    )
    mainInclusions: str = pydantic_Field(
        description="Key inclusions listed in a premium narrative format."
    )
    senseOfPace: str = pydantic_Field(
        description=(
            "Description of the pacing for the day (e.g. relaxed, "
            "immersive, active) in a premium tone."
        )
    )
    dining: str = pydantic_Field(
        description="Dining arrangements or notes, including halal context if relevant."
    )


class LandingpageHeroSection(FrozenModel):
    headline: str = pydantic_Field(
        description="Emotionally-charged headline suitable for landingpage hero section."
    )
    subtitle: str = pydantic_Field(
        description="Elegant brief subtitle capturing the invitation and character of the journey."
    )


class LandingpageContent(FrozenModel):
    heroSection: LandingpageHeroSection
    visualDescription: str = pydantic_Field(
        description=(
            "Atmospheric description suitable for visualizing or illustrating the landingpage."
        )
    )


class JourneyGlance(FrozenModel):
    market: str = pydantic_Field(description="Target market or audience for the quotation.")
    guestProfile: str = pydantic_Field(
        description="Summary of the traveller profile or group type."
    )
    hotelStandard: str = pydantic_Field(description="Stated level of hotel accommodations.")
    mealPreference: str = pydantic_Field(
        description="Meal arrangement or anticipated dietary focus."
    )
    priceType: Literal["Indicative"] = pydantic_Field(
        description="Indicates this is NOT final pricing."
    )
    tourCode: str = pydantic_Field(
        description="Internal or external reference code for the itinerary."
    )
    domesticFlights: str = pydantic_Field(
        description="Describes if domestic flights are included, excluded, or quoted separately."
    )
    priceBasis: str = pydantic_Field(
        description="Basis on which indicative pricing is built (e.g., Twin/Double Sharing Basis)."
    )
    partnerNote: str = pydantic_Field(
        description="Sales/partner note about the nature or focus of the program."
    )
    validity: str = pydantic_Field(
        description="Loose generic statement on validity, subject to final confirmation."
    )

    @model_validator(mode="before")
    @classmethod
    def lenient_glance(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        defaults = {
            "market": "B2B",
            "guestProfile": "Standard Group",
            "hotelStandard": "5-star (Luxury)",
            "mealPreference": "Standard",
            "priceType": "Indicative",
            "tourCode": "TBD",
            "domesticFlights": "Not included",
            "priceBasis": "Twin/Double Sharing Basis",
            "partnerNote": "",
            "validity": "Subject to availability and confirmation",
        }
        for k, v in defaults.items():
            if k not in data or data[k] is None:
                data[k] = v
        return data


class WhyWorks(FrozenModel):
    privateFlexible: str = pydantic_Field(
        description="Short premium emotional paragraph on private and flexible nature."
    )
    comfort: str = pydantic_Field(
        description="Short premium emotional paragraph highlighting comfort aspects."
    )
    muslimFriendly: str = pydantic_Field(
        description="Short premium emotional paragraph highlighting dietary and special care preferences."
    )
    balancedHighlights: str = pydantic_Field(
        description=(
            "Short premium emotional paragraph on the program's "
            "balance and curation of journey highlights."
        )
    )

    @model_validator(mode="before")
    @classmethod
    def lenient_why(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        defaults = {
            "privateFlexible": "Fully private tour with flexible pacing to suit your needs.",
            "comfort": "Premium A/C vehicle transport and handpicked hotels.",
            "muslimFriendly": "Dietary requests, meal planning, and specific preferences are carefully coordinated.",
            "balancedHighlights": "Optimized itinerary balancing iconic sites with leisure time.",
        }
        for k, v in defaults.items():
            if k not in data or data[k] is None:
                data[k] = v
        return data


class HotelPlanHotel(FrozenModel):
    destination: str = pydantic_Field(description="City or primary overnight location.")
    checkInDate: str = pydantic_Field(description="Planned check-in date (YYYY-MM-DD format).")
    checkOutDate: str = pydantic_Field(description="Planned check-out date (YYYY-MM-DD format).")
    hotelArrangement: str = pydantic_Field(
        description="Narrative on the type and standard of hotel used (no specific/fake names)."
    )


class HotelPlan(FrozenModel):
    hotels: List[HotelPlanHotel] = pydantic_Field(
        description="Detailed assumptions for each hotel stop."
    )
    roomNotes: str = pydantic_Field(
        description="Notes regarding rooming, adjoining needs, or preferences."
    )


class OptionalEnhancement(FrozenModel):
    title: str = pydantic_Field(description="Name of the optional enhancement or upsell offering.")
    status: Literal["Recommended", "On request", "Subject to availability"] = pydantic_Field(
        description="Status of the enhancement."
    )


class BookingTerms(FrozenModel):
    deposit: str = pydantic_Field(
        description="Generic placeholder wording on deposit requirements."
    )
    balance: str = pydantic_Field(description="Generic placeholder wording on balance payment.")
    cancellation: str = pydantic_Field(
        description="Generic placeholder wording on cancellation conditions."
    )
    confirmation: str = pydantic_Field(
        description="Generic placeholder wording on booking confirmation."
    )

    @model_validator(mode="before")
    @classmethod
    def lenient_terms(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        defaults = {
            "deposit": "As per standard booking policy.",
            "balance": "Payable prior to tour commencement.",
            "cancellation": "Subject to cancellation charges as per terms.",
            "confirmation": "Subject to availability upon payment.",
        }
        for k, v in defaults.items():
            if k not in data or data[k] is None:
                data[k] = v
        return data


class Finalization(FrozenModel):
    finalDetailsRequired: str = pydantic_Field(
        description=(
            "Operationally realistic list/statement of documents/details "
            "needed prior to travel, as appropriate."
        )
    )
    afterConfirmation: str = pydantic_Field(
        description="Description of key actions and support after booking confirmation."
    )

    @model_validator(mode="before")
    @classmethod
    def lenient_final(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        defaults = {
            "finalDetailsRequired": "Passport copies and flight details required for booking.",
            "afterConfirmation": "Our operations team will coordinate vouchers and guide details.",
        }
        for k, v in defaults.items():
            if k not in data or data[k] is None:
                data[k] = v
        return data


class PriceOption(FrozenModel):
    label: str = pydantic_Field(
        description="Label for this price option (e.g., 'Family Suite', 'Executive Villa')."
    )
    notes: str = pydantic_Field(
        description="Extra notes about this option's inclusions/exclusions."
    )
    amount: Optional[float] = pydantic_Field(
        description="Indicative amount in stated currency, may be null as placeholder."
    )


class Pricing(FrozenModel):
    currency: str = pydantic_Field(
        description="Currency of indicative pricing, e.g. USD, QAR, AED, EUR."
    )
    pricingTitle: str = pydantic_Field(
        description="Headline for the pricing section indicating its indicative nature."
    )
    basis: str = pydantic_Field(
        description="Statement clarifying the preliminary, non-final basis for this pricing."
    )
    priceOptions: List[PriceOption] = pydantic_Field(
        description="Array of skeleton price options (may be empty or null amounts)."
    )
    subtotal: Optional[float] = pydantic_Field(
        description="Subtotal for the quotation in indicated currency, null if unknown/pending."
    )
    discountTotal: Optional[float] = pydantic_Field(
        description="Total discount applied, null if not yet known"
    )
    taxTotal: Optional[float] = pydantic_Field(
        description="Total tax amount, null if not yet finalized."
    )
    grandTotal: Optional[float] = pydantic_Field(
        description="Grand total for the quotation, null if not finalized."
    )


class RetrievalStatus(FrozenModel):
    hotel: Literal["pending", "not_required"] = pydantic_Field(
        description="Status of hotel supplier retrieval step."
    )
    activity: Literal["pending", "not_required"] = pydantic_Field(
        description="Status of activity supplier retrieval step."
    )
    guide: Literal["pending", "not_required"] = pydantic_Field(
        description="Status of guide supplier retrieval step."
    )
    transfer: Literal["pending", "not_required"] = pydantic_Field(
        description="Status of transfer supplier retrieval step."
    )
    flight: Literal["pending", "not_required"] = pydantic_Field(
        description="Status of flight supplier retrieval step."
    )


class CandidateBlock(FrozenModel):
    block_id: str = pydantic_Field(description="Unique reference for the logical retrieval group.")
    service_type: Literal["hotel", "activity", "guide", "transfer", "flight"] = pydantic_Field(
        description="Type of service this block represents."
    )
    destination: str = pydantic_Field(description="Primary location or hub relevant to this block.")
    source_day_numbers: List[int] = pydantic_Field(
        description="Day numbers from itinerary to which this block relates."
    )


class TourQuotationPayload(FrozenModel):
    quotationNarrative: str = pydantic_Field(
        description=(
            "Luxury cinematic narrative overview of the quoted journey, "
            "styled for B2B landingpage, evoking an elegant and "
            "emotionally resonant travel experience."
        )
    )
    programOverview: Optional[TextSection] = pydantic_Field(
        default=None, description="Optional program overview section containing paragraphs."
    )
    landingpageContent: LandingpageContent
    journeyGlance: JourneyGlance
    whyWorks: WhyWorks
    itinerary: List[ItineraryDay] = pydantic_Field(
        description=(
            "Sequential structured itinerary, day by day, each with "
            "cinematic and operational context."
        )
    )
    hotelPlan: HotelPlan
    optionalEnhancements: List[OptionalEnhancement] = pydantic_Field(
        description="Array of premium optional enhancements fitting the guest context."
    )
    bookingTerms: BookingTerms
    finalization: Finalization
    pricing: Union[Pricing, dict, Any] = pydantic_Field(
        description="Pricing can be Pricing model or calculated pricing context dictionary."
    )
    retrievalStatus: RetrievalStatus
    candidateBlocks: List[CandidateBlock] = pydantic_Field(
        description="Guidance for grouped supplier/service lookup, one per logical service group."
    )
    inclusions: Optional[List[str]] = pydantic_Field(
        default=None, description="Optional list of inclusions."
    )
    exclusions: Optional[List[str]] = pydantic_Field(
        default=None, description="Optional list of exclusions."
    )
    # Extra field allowed for API validation
    quotationNumber: Optional[str] = pydantic_Field(
        default=None, description="Optional quotation reference code."
    )

    @model_validator(mode="before")
    @classmethod
    def lenient_payload(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # 1. Handle missing/empty metadata lists and dicts
        if "retrievalStatus" not in data or data["retrievalStatus"] is None:
            data["retrievalStatus"] = {
                "hotel": "pending",
                "activity": "pending",
                "guide": "pending",
                "transfer": "pending",
                "flight": "pending",
            }
        elif isinstance(data["retrievalStatus"], dict):
            # Ensure all required keys exist
            rs = data["retrievalStatus"]
            for key in ["hotel", "activity", "guide", "transfer", "flight"]:
                if key not in rs or rs[key] is None:
                    rs[key] = "pending"
            data["retrievalStatus"] = rs

        if "candidateBlocks" not in data or data["candidateBlocks"] is None:
            data["candidateBlocks"] = []
        if "optionalEnhancements" not in data or data["optionalEnhancements"] is None:
            data["optionalEnhancements"] = []

        # 2. Normalize pricing
        pricing = data.get("pricing")
        if pricing is not None:
            if isinstance(pricing, dict):
                # If it has "totalPriceUsd", it is custom pricing engine output; keep as dict.
                # If it does not have "totalPriceUsd", it is standard pricing; coerce/normalize it.
                if "totalPriceUsd" not in pricing:
                    if "currency" not in pricing or pricing["currency"] is None:
                        pricing["currency"] = "USD"
                    if "pricingTitle" not in pricing or pricing["pricingTitle"] is None:
                        pricing["pricingTitle"] = "PRICE QUOTATION – B2B NET INDICATIVE"
                    if "basis" not in pricing or pricing["basis"] is None:
                        pricing["basis"] = "B2B net indicative"
                    if "priceOptions" not in pricing or pricing["priceOptions"] is None:
                        pricing["priceOptions"] = []

                    price_opts = []
                    for opt in pricing.get("priceOptions", []):
                        if isinstance(opt, dict):
                            if "label" not in opt or opt["label"] is None:
                                opt["label"] = "Standard Option"
                            if "notes" not in opt or opt["notes"] is None:
                                opt["notes"] = ""
                            if "amount" not in opt:
                                opt["amount"] = None
                            price_opts.append(opt)
                    pricing["priceOptions"] = price_opts
                    data["pricing"] = pricing

        return data


# --- Extract Candidate Block Schemas (Kept for alignment/reference) ---


class PaxComposition(FrozenModel):
    adults: int
    children: int


class HotelBrief(FrozenModel):
    block_id: str
    task: Literal["hotel_search", "cruise_search"]
    destination: str
    checkin: str
    checkout: str
    nights: int
    pax: PaxComposition
    star_options: List[int]
    halal_required: bool
    special_requirements: List[str]
    search_query: str


class ActivityBrief(FrozenModel):
    block_id: str
    task: Literal["activity_search"]
    area: str
    date: str
    activities: List[str]
    pax: PaxComposition
    halal_required: bool
    special_requirements: List[str]
    search_query: str


class GuideBrief(FrozenModel):
    block_id: str
    task: Literal["guide_search"]
    destination: str
    dates: List[str]
    days: int
    language: str
    pax: PaxComposition
    search_query: str


class FlightBrief(FrozenModel):
    block_id: str
    task: Literal["flight_search"]
    from_city: str
    from_iata: str
    to_city: str
    to_iata: str
    date: str
    pax: PaxComposition
    search_query: str


class TransferBrief(FrozenModel):
    block_id: str
    task: Literal["transfer_search"]
    transfer_type: Literal["airport_pickup", "airport_dropoff", "intercity", "day_trip_return"]
    from_loc: str = pydantic_Field(alias="from")
    to_loc: str = pydantic_Field(alias="to")
    date: str
    pax: PaxComposition
    vehicle_requirement: Literal["4-seat", "7-seat", "16-seat", "29-seat", "45-seat"]
    search_query: str

    model_config = {"populate_by_name": True, "frozen": True, "extra": "ignore"}


class Wave1(FrozenModel):
    hotels: List[HotelBrief]
    activities: List[ActivityBrief]
    guides: List[GuideBrief]
    flights: List[FlightBrief]


class QuotationPayload(FrozenModel):
    """Output format of Extract Candidate Block."""

    wave1: Wave1
    wave2_transfers: List[TransferBrief]


# --- Extract Candidate Block New Schemas ---


class ServiceBlockPax(FrozenModel):
    adults: int
    children: int
    children_ages: List[int]
    total: int


class ServiceBlockRequirements(FrozenModel):
    halal_required: bool
    private_required: bool
    budget_tier: str
    special_notes: List[str]


class ServiceBlockSearch(FrozenModel):
    query: str
    source_preference: List[str]
    max_candidates: int


class ServiceBlockHotel(FrozenModel):
    checkin: str
    checkout: str
    nights: int
    star_level: List[int]
    room_count: int
    rooming: str
    room_category: str
    bedding_type: str
    connecting_required: bool
    extra_bed_required: bool
    breakfast_required: bool
    meal_plan: str
    early_checkin_needed: bool
    late_checkout_needed: bool
    vip_treatment: bool
    passport_required_days_before: int
    hotel_style: List[str]


class ServiceBlockTransfer(FrozenModel):
    transfer_type: str
    from_location: str
    to_location: str
    date: str
    pickup_time: Optional[str] = None
    flight_number: Optional[str] = None
    vehicle_requirement: str
    vehicle_class: str
    seats: int
    luggage_count: int
    distance_km_estimate: Optional[float] = None
    duration_hours_estimate: Optional[float] = None
    toll_included: bool
    parking_fee_included: bool
    driver_allowance_needed: bool
    overnight_allowance_needed: bool


class ServiceBlockActivityItem(FrozenModel):
    activity_item_id: str
    name: str
    category: str


class ServiceBlockActivity(FrozenModel):
    date: str
    activity_type: str
    activity_items: List[ServiceBlockActivityItem]
    start_time_preference: str
    duration_hours_preference: int
    private_group_required: bool
    entrance_fees_required: bool
    meal_included_required: bool
    halal_meal_required: bool
    child_friendly_required: bool
    mobility_level: str
    weather_sensitive: bool
    pickup_dropoff_required: bool


class ServiceBlockGuide(FrozenModel):
    guide_type: str
    language_required: str
    secondary_language_preferred: str
    dates: List[str]
    total_days: int
    working_hours_per_day: int
    overtime_allowed: bool
    overtime_rate_required: bool
    license_required: bool
    market_experience_required: List[str]
    gender_preference: Optional[str] = None
    meal_allowance_included: bool
    transport_for_guide_included: bool


class ServiceBlockFlight(FrozenModel):
    flight_type: str
    from_city: str
    to_city: str
    from_airport: str
    to_airport: str
    date: str
    departure_time_preference: str
    airline_preference: List[str]
    cabin_class: str
    checked_baggage_required: bool
    baggage_kg_per_person: int
    seat_together_required: bool
    refundable_required: bool
    changeable_required: bool
    passport_required: bool
    date_of_birth_required: bool


class ServiceBlock(FrozenModel):
    block_id: str
    quotation_id: str
    service_type: Literal["hotel", "transfer", "activity", "guide", "flight"]
    source_day_numbers: List[int]
    source_dates: List[str]
    destination: str
    area: str
    pax: ServiceBlockPax
    requirements: ServiceBlockRequirements
    search: ServiceBlockSearch
    status: str
    hotel: Optional[ServiceBlockHotel] = None
    transfer: Optional[ServiceBlockTransfer] = None
    activity: Optional[ServiceBlockActivity] = None
    guide: Optional[ServiceBlockGuide] = None
    flight: Optional[ServiceBlockFlight] = None


# --- Service Retrieval Results Schemas ---


class CandidateSupplier(FrozenModel):
    supplier_id: Optional[str] = None
    name: str
    type: str
    source_url: str
    source_type: Literal["internal_file", "web", "api", "manual", "estimate"]
    contact: Optional[str] = None


class CandidateService(FrozenModel):
    name: str
    destination: str
    date_start: str
    date_end: str
    quantity: int
    unit: str
    description: str


class CostBreakdownItem(FrozenModel):
    label: str
    amount: float


class CandidatePricing(FrozenModel):
    currency: str
    unit_price: float
    unit: str
    cost_breakdown: List[CostBreakdownItem]
    net_cost: float
    markup_rule: Optional[str] = None
    markup_amount: Optional[float] = None
    sell_price: Optional[float] = None
    tax: Optional[float] = None
    fees: Optional[float] = None
    commission: Optional[float] = None
    total_estimate: float


class CandidateAvailability(FrozenModel):
    status: Literal["available", "on_request", "limited", "unavailable", "sold_out"]
    inventory_status: Optional[str] = None
    booking_deadline: Optional[str] = None
    cutoff_date: Optional[str] = None
    cancellation_policy: Optional[str] = None


class CandidateQuality(FrozenModel):
    confidence: Literal["low", "medium", "high"]
    fit_score: float = pydantic_Field(ge=0, le=1)
    reasons: List[str]


class CandidateOps(FrozenModel):
    requires_human_review: bool
    missing_fields: List[str]
    retrieved_at: str
    retrieval_agent: str
    version: str


class CandidateHotelDetails(FrozenModel):
    hotel_name: str
    star_level: int = pydantic_Field(ge=1, le=7)
    room_type: str
    room_count: int = pydantic_Field(ge=1)
    bedding_type: str
    room_size_sqm: int = pydantic_Field(ge=1)
    breakfast_included: bool
    meal_plan: str
    extra_bed_available: bool
    connecting_rooms_available: bool
    checkin_time: str
    checkout_time: str
    early_checkin_available: bool
    late_checkout_available: bool
    child_policy: str
    location_area: str
    hotel_style: List[str]
    images: List[str]


class HotelCandidate(FrozenModel):
    candidate_id: str
    block_id: str
    service_type: Literal["hotel"]
    rank: int = pydantic_Field(ge=1, le=3)
    supplier: CandidateSupplier
    service: CandidateService
    pricing: CandidatePricing
    availability: CandidateAvailability
    quality: CandidateQuality
    ops: CandidateOps
    hotel: CandidateHotelDetails


class HotelSearchResult(FrozenModel):
    candidates: List[HotelCandidate]


class CandidateActivityItem(FrozenModel):
    name: str
    category: str


class CandidateActivityDetails(FrozenModel):
    activity_type: str
    operator_name: str
    activity_items: List[CandidateActivityItem]
    duration_hours: int = pydantic_Field(ge=0)
    private_group: bool
    pickup_included: bool
    meal_included: bool
    halal_meal_available: bool
    entrance_fees_included: bool
    entrance_fee_breakdown: List[str]
    child_policy: str
    weather_sensitive: bool
    mobility_level: str
    images: List[str]


class ActivityCandidate(FrozenModel):
    candidate_id: str
    block_id: str
    service_type: Literal["activity"]
    rank: int = pydantic_Field(ge=1, le=3)
    supplier: CandidateSupplier
    service: CandidateService
    pricing: CandidatePricing
    availability: CandidateAvailability
    quality: CandidateQuality
    ops: CandidateOps
    activity: CandidateActivityDetails


class ActivitySearchResult(FrozenModel):
    candidates: List[ActivityCandidate]


class CandidateGuideDetails(FrozenModel):
    guide_name: Optional[str] = None
    guide_type: Literal["local_guide", "tour_leader", "city_guide", "specialized_guide"]
    language: str
    secondary_language: Optional[str] = None
    license_number: Optional[str] = None
    market_experience: List[
        Literal["GCC", "family", "luxury", "FIT", "GIT", "muslim-friendly", "adventure", "culture"]
    ]
    working_hours_per_day: int = pydantic_Field(ge=1, le=16)
    overtime_rate: Optional[float] = None
    meal_allowance_included: bool
    transport_included: bool
    guide_gender: Optional[Literal["male", "female"]] = None
    guide_style: List[
        Literal[
            "friendly",
            "storytelling",
            "formal",
            "luxury_service",
            "family-oriented",
            "educational",
            "relaxed",
        ]
    ]


class GuideCandidate(FrozenModel):
    candidate_id: str
    block_id: str
    service_type: Literal["guide"]
    rank: int = pydantic_Field(ge=1, le=3)
    supplier: CandidateSupplier
    service: CandidateService
    pricing: CandidatePricing
    availability: CandidateAvailability
    quality: CandidateQuality
    ops: CandidateOps
    guide: CandidateGuideDetails


class GuideSearchResult(FrozenModel):
    candidates: List[GuideCandidate]


class CandidateTransferDetails(FrozenModel):
    transfer_type: Literal["airport_pickup", "airport_dropoff", "point_to_point"]
    vehicle_type: str
    vehicle_class: str
    operator_name: str
    pickup_location: str
    dropoff_location: str
    pickup_time: Optional[str] = None
    estimated_duration_hours: float = pydantic_Field(ge=0)
    estimated_distance_km: float = pydantic_Field(ge=0)
    luggage_capacity: str
    driver_language: str
    meet_and_greet_included: bool
    toll_included: bool
    parking_fee_included: bool
    fuel_included: bool
    driver_allowance_included: bool


class TransferCandidate(FrozenModel):
    candidate_id: str
    block_id: str
    service_type: Literal["transfer"]
    rank: int = pydantic_Field(ge=1, le=3)
    supplier: CandidateSupplier
    service: CandidateService
    pricing: CandidatePricing
    availability: CandidateAvailability
    quality: CandidateQuality
    ops: CandidateOps
    transfer: CandidateTransferDetails


class TransportationCostEstimate(FrozenModel):
    candidates: List[TransferCandidate]
