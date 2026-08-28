from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class BasicItineraryDayInputSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    day_number: int | None = None
    destination: str | None = None
    destination_ref_id: str | None = None
    display_date: str | None = None
    summary: str | None = None
    overnight: str | None = None
    meals: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ServiceScopeInputSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    private_vehicle: str | None = None
    vehicle_preference: str | None = None
    guide_language: str | None = None
    guide_scope: str | None = None
    domestic_flights: str | None = None
    intl_flights: str | None = None
    rail_cruise: str | None = None
    transport_class: str | None = None
    meal_plan: str | None = None
    dining_level: str | None = None
    experiences_included: str | None = None
    optional_activities: str | None = None
    visa_fasttrack: str | None = None
    meet_assist: str | None = None
    insurance: str | None = None
    other_services: str | None = None


class AccommodationPreferencesInputSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    hotel_level: str | None = None
    preferred_hotel: str | None = None
    room_type: str | None = None
    bedding: str | None = None
    connecting: str | None = None
    suite_interest: str | None = None
    hotel_style: str | None = None


class SpecialRequirementsInputSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    dietary: str | None = None
    halal: str | None = None
    mobility: str | None = None
    health_considerations: str | None = None
    special_requirements: str | None = None


class CommercialParametersInputSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    budget: float | None = None
    budget_basis: str | None = None
    currency: str | None = "USD"
    pricing_type: str | None = None
    commission: float | None = None
    target_gp: float | None = None
    minimum_gp: float | None = None
    contingency: float | None = None
    payment_fee: float | None = None
    tax_treatment: str | None = None
    discount_cap: str | None = None
    quote_validity: str | None = None
    payment_terms: str | None = None


class CostingReadinessInputSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    existing_template: str | None = None
    rates_available: str | None = None
    rfq_required: str | None = None
    rate_risk: str | None = None
    preferred_suppliers: str | None = None
    missing_info: str | None = None


class SalesStrategyInputSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    journey_direction: str | None = None
    selling_angle: str | None = None
    competitor: str | None = None
    internal_notes: str | None = None


class QuoteRequestCreateSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # Lead & Ownership
    role: Literal["traveller", "advisor"]
    brand_id: str | None = "selvara"
    travel_designer_id: str | None = None
    created_by_profile_id: str | None = None
    partner_id: str | None = None
    priority: Literal["normal", "warm", "hot"] | None = "normal"
    lead_source: str | None = None
    quote_deadline: str | None = None
    decision_date: str | None = None

    # Contact & Persona
    customer_name: str
    client_name: str | None = None
    email: str
    phone: str | None = None
    company_name: str | None = None
    market: str | None = None
    preferred_contact: str | None = None
    client_context: str | None = None

    # Journey & Basics
    destinations: list[str] = Field(default_factory=list)
    start_date: str | None = None
    end_date: str | None = None
    raw_dates_text: str | None = None
    travel_timing: str | None = None
    date_flexibility: str | None = None
    arrival_city: str | None = None
    departure_city: str | None = None
    room_configuration: str | None = None
    routing_constraints: str | None = None

    # Travellers Composition
    adults: int = Field(default=2, ge=1)
    children: int = Field(default=0, ge=0)
    kid_ages: list[int] = Field(default_factory=list)
    children_details: str | None = None
    infants: int = 0
    infant_ages: list[int] = Field(default_factory=list)

    # Style, Vision & Priorities
    travel_style: str | None = None
    travel_pace: str | None = None
    priority_1: str | None = None
    priority_2: str | None = None
    priority_3: str | None = None
    occasion: str | None = None
    must_have: str | None = None
    avoid: str | None = None
    interests: str | None = None
    privacy: str | None = None
    experience_expectations: str | None = None

    # Accommodation Requirements
    hotel_level: str | None = None
    preferred_hotel: str | None = None
    room_type: str | None = None
    bedding: str | None = None
    connecting: str | None = None
    suite_interest: str | None = None
    hotel_style: str | None = None

    # Service Scope for Costing
    private_vehicle: str | None = None
    vehicle_preference: str | None = None
    guide_language: str | None = None
    guide_scope: str | None = None
    domestic_flights: str | None = None
    intl_flights: str | None = None
    rail_cruise: str | None = None
    transport_class: str | None = None
    meal_plan: str | None = None
    dining_level: str | None = None
    experiences_included: str | None = None
    optional_activities: str | None = None
    visa_fasttrack: str | None = None
    meet_assist: str | None = None
    insurance: str | None = None
    other_services: str | None = None

    # Special & Health Requirements
    special_requirements: str | None = None
    dietary: str | None = None
    halal: str | None = None
    mobility: str | None = None
    health_considerations: str | None = None

    # Commercial & Pricing Parameters
    budget: float | None = None
    budget_basis: str | None = None
    currency: str | None = "USD"
    pricing_type: str | None = None
    commission: float | None = None
    target_gp: float | None = None
    minimum_gp: float | None = None
    contingency: float | None = None
    payment_fee: float | None = None
    tax_treatment: str | None = None
    discount_cap: str | None = None
    quote_validity: str | None = None
    payment_terms: str | None = None

    # Output Presentation & Readiness
    price_display: str | None = None
    quote_options: int | None = 1
    hotel_options: str | None = None
    show_commission: str | None = None
    inclusions_exclusions: str | None = None
    quote_assumptions: str | None = None
    existing_template: str | None = None
    rates_available: str | None = None
    rfq_required: str | None = None
    rate_risk: str | None = None
    preferred_suppliers: str | None = None
    missing_info: str | None = None

    # Sales Strategy
    journey_direction: str | None = None
    selling_angle: str | None = None
    competitor: str | None = None
    internal_notes: str | None = None

    # Optional Basic Itinerary
    itinerary_days: list[BasicItineraryDayInputSchema] = Field(default_factory=list)

    # Honeypot anti-bot validation field (must be empty/None)
    website: str | None = None


class QuoteRequestEditPayloadSchema(QuoteRequestCreateSchema):
    model_config = ConfigDict(extra="ignore")

    change_summary: str | None = None


class QuoteRequestUpdateSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: Literal["new", "under_review", "quotation_created", "archived"] | None = None
    customer_name: str | None = None
    email: str | None = None
    phone: str | None = None
    company_name: str | None = None
    market: str | None = None
    special_requirements: str | None = None
    linked_quotation_id: str | None = None
    created_by_profile_id: str | None = None
    partner_id: str | None = None


class QuoteRequestStatusUpdateSchema(BaseModel):
    status: Literal["new", "under_review", "quotation_created", "archived"]
    baseRevision: int = Field(ge=1)


class QuoteRequestResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    status: str
    current_revision: int = 1
    customer_name: str | None
    email: str | None
    phone: str | None
    company_name: str | None
    market: str | None
    preferred_contact: str | None
    destinations: list[str]
    start_date: str | None
    end_date: str | None
    raw_dates_text: str | None
    adults: int | None
    children: int | None
    kid_ages: list[int]
    children_details: str | None
    travel_style: str | None
    special_requirements: str | None
    payload_json: dict[str, Any]
    created_by_profile_id: str | None
    updated_by_profile_id: str | None = None
    partner_id: str | None
    linked_quotation_id: str | None
    created_at: datetime
    updated_at: datetime


class QuoteRequestRevisionSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    revision: int
    change_summary: str | None = None
    change_source: str = "manual_edit"
    created_by_profile_id: str | None = None
    created_at: datetime


class QuoteRequestRevisionDetailSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    request_id: str
    revision: int
    role: str
    status: str | None = None
    customer_name: str | None
    email: str | None
    phone: str | None
    company_name: str | None
    market: str | None
    preferred_contact: str | None
    destinations: list[str]
    start_date: str | None
    end_date: str | None
    raw_dates_text: str | None
    adults: int | None
    children: int | None
    kid_ages: list[int]
    children_details: str | None
    travel_style: str | None
    special_requirements: str | None
    payload_json: dict[str, Any]
    change_summary: str | None
    change_source: str
    created_by_profile_id: str | None
    created_at: datetime


class QuoteRequestRevisionsListResponseSchema(BaseModel):
    request_id: str
    current_revision: int
    items: list[QuoteRequestRevisionSummarySchema]


class QuotationVersionSummarySchema(BaseModel):
    quotation_id: str
    quotation_family_id: str
    business_version: int
    parent_quotation_id: str | None = None
    status: str
    title: str | None = None
    created_at: datetime


class RequestQuotationVersionsResponseSchema(BaseModel):
    request_id: str
    request_revision: int
    items: list[QuotationVersionSummarySchema] = Field(default_factory=list)


class QuoteRequestListResponseSchema(BaseModel):
    items: list[QuoteRequestResponseSchema]
    total: int
    next_cursor: str | None = None
    summary: dict[str, int] = Field(default_factory=dict)


class MinimalItineraryDayWithStayOverrideSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    day_number: int = Field(ge=1)
    title: str | None = None
    destination: str | None = None
    destination_ref: dict[str, Any] | None = None
    overnight: str | None = None
    accommodation_id: str | None = None
    accommodation_name: str | None = None
    room_type: str | None = None
    summary: str | None = None
    meals: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    sense_of_pace: str | None = None
    display_date: str | None = None


class MinimalCommercialPricingOverrideSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    label: str = "Standard Luxury Option"
    currency: str = "USD"
    per_adult_amount_minor: int | None = None
    per_child_amount_minor: int | None = None
    group_total_amount_minor: int | None = None


class QuotationMinimalOverridesSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    brand_id: str | None = None
    lang: Literal["en", "vi", "ar"] | None = "en"
    template_id: str | None = "itinerary-imagery-v1"
    travel_designer_id: str | None = None
    customer_name: str | None = None
    adults: int | None = Field(default=None, ge=1)
    children: int | None = Field(default=None, ge=0)
    kid_ages: list[int] = Field(default_factory=list)
    start_date: str | None = None
    end_date: str | None = None
    request_revision: int | None = Field(default=None, ge=1)

    itinerary_with_stays: list[MinimalItineraryDayWithStayOverrideSchema] = Field(default_factory=list)
    pricing: MinimalCommercialPricingOverrideSchema | None = None
    pricing_options: list[MinimalCommercialPricingOverrideSchema] = Field(default_factory=list)


class GenerateQuotationFromRequestResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    quotation_id: str
    request_id: str
    redirect_url: str
    status: str = "draft"
    current_revision: int = 1
    facts_snapshot: dict[str, Any] = Field(default_factory=dict)
