import type { QuoteRequestItem, QuoteRequestRole } from "../components/quotation-workspace/factsTypes.ts";
import type { BasicDayItem } from "../components/quotation-workspace/BasicItineraryDayGrid.tsx";
import type { DestinationRef } from "../components/destination/types.ts";

export type QuoteRequestFormState = {
  role: QuoteRequestRole;
  brand_id: string;
  travel_designer_id: string | null;
  partner_id: string | null;
  priority: "normal" | "warm" | "hot";
  lead_source: string;
  quote_deadline: string;
  decision_date: string;

  // Traveller Identity
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  country: string;
  preferred_contact: string;
  client_context: string;

  // Advisor Identity & End-Client
  client_name: string;
  advisor_first_name: string;
  advisor_last_name: string;
  advisor_company: string;
  advisor_email: string;
  advisor_phone: string;
  advisor_market: string;

  // Journey Specs
  destination: string;
  destinations?: string[];
  destination_refs?: DestinationRef[];
  display_route_text?: string;
  travel_timing: string;
  arrival_date: string;
  departure_date: string;
  raw_dates_text: string;
  date_flexibility: string;
  arrival_city: string;
  departure_city: string;
  room_configuration: string;
  routing_constraints: string;

  adults: number;
  children: number;
  kid_ages: number[];
  infants: number;
  primary_theme: string;
  travel_pace: string;
  priority_1: string;
  priority_2: string;
  priority_3: string;
  occasion: string;
  must_have: string;
  avoid: string;
  interests: string;
  privacy: string;
  experience_expectations: string;
  advisor_journey_type: string;
  message: string;

  // Accommodation Scope
  hotel_level: string;
  preferred_hotel: string;
  room_type: string;
  bedding: string;
  connecting: string;
  suite_interest: string;
  hotel_style: string;

  // Service Scope
  private_vehicle: string;
  vehicle_preference: string;
  guide_language: string;
  guide_scope: string;
  domestic_flights: string;
  intl_flights: string;
  rail_cruise: string;
  transport_class: string;
  meal_plan: string;
  dining_level: string;
  experiences_included: string;
  optional_activities: string;
  visa_fasttrack: string;
  meet_assist: string;
  insurance: string;
  other_services: string;

  // Special Requirements
  dietary: string;
  halal: string;
  mobility: string;
  health_considerations: string;

  // Commercial & Pricing
  budget: number | "";
  budget_basis: string;
  currency: string;
  pricing_type: string;
  commission: number | "";
  show_commission: string;
  price_display: string;
  target_gp: number | "";
  minimum_gp: number | "";
  contingency: number | "";
  payment_fee: number | "";
  tax_treatment: string;
  discount_cap: string;
  quote_validity: string;
  payment_terms: string;

  // Readiness & Strategy
  existing_template: string;
  rates_available: string;
  rfq_required: string;
  rate_risk: string;
  preferred_suppliers: string;
  missing_info: string;
  journey_direction: string;
  selling_angle: string;
  competitor: string;
  internal_notes: string;

  // Anti-bot Honeypot
  website: string;
};

export function getInitialQuoteRequestFormState(role: QuoteRequestRole = "traveller"): QuoteRequestFormState {
  return {
    role,
    brand_id: "selvara",
    travel_designer_id: null,
    partner_id: null,
    priority: "normal",
    lead_source: "Website",
    quote_deadline: "",
    decision_date: "",

    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    country: "",
    preferred_contact: "Email",
    client_context: "",

    client_name: "",
    advisor_first_name: "",
    advisor_last_name: "",
    advisor_company: "",
    advisor_email: "",
    advisor_phone: "",
    advisor_market: "",

    destination: "Vietnam",
    destinations: [],
    destination_refs: [],
    display_route_text: "",
    travel_timing: "Exact dates",
    arrival_date: "",
    departure_date: "",
    raw_dates_text: "",
    date_flexibility: "",
    arrival_city: "",
    departure_city: "",
    room_configuration: "",
    routing_constraints: "",

    adults: 2,
    children: 0,
    kid_ages: [],
    infants: 0,
    primary_theme: "Living Heritage",
    travel_pace: "Balanced",
    priority_1: "",
    priority_2: "",
    priority_3: "",
    occasion: "",
    must_have: "",
    avoid: "",
    interests: "",
    privacy: "",
    experience_expectations: "",
    advisor_journey_type: "Tailor-made cultural journey",
    message: "",

    hotel_level: "",
    preferred_hotel: "",
    room_type: "",
    bedding: "",
    connecting: "",
    suite_interest: "",
    hotel_style: "",

    private_vehicle: "Yes",
    vehicle_preference: "",
    guide_language: "English",
    guide_scope: "Full-trip guide",
    domestic_flights: "Yes",
    intl_flights: "No",
    rail_cruise: "",
    transport_class: "",
    meal_plan: "Breakfast only",
    dining_level: "",
    experiences_included: "All planned experiences",
    optional_activities: "",
    visa_fasttrack: "No",
    meet_assist: "No",
    insurance: "No",
    other_services: "",

    dietary: "",
    halal: "",
    mobility: "",
    health_considerations: "",

    budget: "",
    budget_basis: "Total trip",
    currency: "USD",
    pricing_type: "Gross",
    commission: "",
    show_commission: "No",
    price_display: "Total journey price",
    target_gp: "",
    minimum_gp: "",
    contingency: "",
    payment_fee: "",
    tax_treatment: "",
    discount_cap: "",
    quote_validity: "",
    payment_terms: "",

    existing_template: "",
    rates_available: "",
    rfq_required: "",
    rate_risk: "",
    preferred_suppliers: "",
    missing_info: "",
    journey_direction: "",
    selling_angle: "",
    competitor: "",
    internal_notes: "",

    website: "",
  };
}

export function mapRequestToFormState(request: QuoteRequestItem): QuoteRequestFormState {
  const payload = (
    typeof request.payload_json === "string"
      ? (() => {
          try {
            return JSON.parse(request.payload_json) as Record<string, unknown>;
          } catch {
            return {};
          }
        })()
      : (request.payload_json || {})
  ) as Record<string, unknown>;
  const isTraveller = request.role === "traveller";

  // Split name for traveller or advisor if not in payload
  const rawName = request.customer_name || "";
  const nameParts = rawName.split(" ");
  const defaultFirst = nameParts[0] || "";
  const defaultLast = nameParts.slice(1).join(" ") || "";

  return {
    role: request.role,
    brand_id: (payload.brand_id as string) || "selvara",
    travel_designer_id: (request.created_by_profile_id || payload.travel_designer_id || null) as string | null,
    partner_id: (request.partner_id || payload.partner_id || null) as string | null,
    priority: (payload.priority as "normal" | "warm" | "hot") || "normal",
    lead_source: (payload.lead_source as string) || "Website",
    quote_deadline: (payload.quote_deadline as string) || "",
    decision_date: (payload.decision_date as string) || "",

    first_name: isTraveller ? (payload.first_name as string) || defaultFirst : "",
    last_name: isTraveller ? (payload.last_name as string) || defaultLast : "",
    email: isTraveller ? request.email || "" : "",
    phone: isTraveller ? request.phone || "" : "",
    country: isTraveller ? request.market || (payload.country as string) || "" : "",
    preferred_contact: (request.preferred_contact || payload.preferred_contact || "Email") as string,
    client_context: (payload.client_context as string) || "",

    client_name: (payload.client_name as string) || "",
    advisor_first_name: !isTraveller ? (payload.advisor_first_name as string) || defaultFirst : "",
    advisor_last_name: !isTraveller ? (payload.advisor_last_name as string) || defaultLast : "",
    advisor_company: !isTraveller ? request.company_name || (payload.advisor_company as string) || "" : "",
    advisor_email: !isTraveller ? request.email || "" : "",
    advisor_phone: !isTraveller ? request.phone || "" : "",
    advisor_market: !isTraveller ? request.market || (payload.advisor_market as string) || "" : "",

    destination: request.destinations?.[0] || (payload.destination as string) || "Vietnam",
    destinations: request.destinations || (payload.destinations as string[]) || [],
    destination_refs: (payload.destination_refs as DestinationRef[]) || [],
    display_route_text: (payload.display_route_text as string) || "",
    travel_timing: (payload.travel_timing as string) || "Exact dates",
    arrival_date: request.start_date || (payload.arrival_date as string) || "",
    departure_date: request.end_date || (payload.departure_date as string) || "",
    raw_dates_text: request.raw_dates_text || (payload.raw_dates_text as string) || "",
    date_flexibility: (payload.date_flexibility as string) || "",
    arrival_city: (payload.arrival_city as string) || "",
    departure_city: (payload.departure_city as string) || "",
    room_configuration: (payload.room_configuration as string) || "",
    routing_constraints: (payload.routing_constraints as string) || "",

    adults: request.adults ?? 2,
    children: request.children ?? 0,
    kid_ages: request.kid_ages || [],
    infants: (payload.infants as number) || 0,
    primary_theme: request.travel_style || (payload.primary_theme as string) || "Living Heritage",
    travel_pace: (payload.travel_pace as string) || "Balanced",
    priority_1: (payload.priority_1 as string) || "",
    priority_2: (payload.priority_2 as string) || "",
    priority_3: (payload.priority_3 as string) || "",
    occasion: (payload.occasion as string) || "",
    must_have: (payload.must_have as string) || "",
    avoid: (payload.avoid as string) || "",
    interests: (payload.interests as string) || "",
    privacy: (payload.privacy as string) || "",
    experience_expectations: (payload.experience_expectations as string) || "",
    advisor_journey_type: (payload.advisor_journey_type as string) || "Tailor-made cultural journey",
    message: request.special_requirements || (payload.message as string) || "",

    hotel_level: (payload.hotel_level as string) || "",
    preferred_hotel: (payload.preferred_hotel as string) || "",
    room_type: (payload.room_type as string) || "",
    bedding: (payload.bedding as string) || "",
    connecting: (payload.connecting as string) || "",
    suite_interest: (payload.suite_interest as string) || "",
    hotel_style: (payload.hotel_style as string) || "",

    private_vehicle: (payload.private_vehicle as string) || "Yes",
    vehicle_preference: (payload.vehicle_preference as string) || "",
    guide_language: (payload.guide_language as string) || "English",
    guide_scope: (payload.guide_scope as string) || "Full-trip guide",
    domestic_flights: (payload.domestic_flights as string) || "Yes",
    intl_flights: (payload.intl_flights as string) || "No",
    rail_cruise: (payload.rail_cruise as string) || "",
    transport_class: (payload.transport_class as string) || "",
    meal_plan: (payload.meal_plan as string) || "Breakfast only",
    dining_level: (payload.dining_level as string) || "",
    experiences_included: (payload.experiences_included as string) || "All planned experiences",
    optional_activities: (payload.optional_activities as string) || "",
    visa_fasttrack: (payload.visa_fasttrack as string) || "No",
    meet_assist: (payload.meet_assist as string) || "No",
    insurance: (payload.insurance as string) || "No",
    other_services: (payload.other_services as string) || "",

    dietary: (payload.dietary as string) || "",
    halal: (payload.halal as string) || "",
    mobility: (payload.mobility as string) || "",
    health_considerations: (payload.health_considerations as string) || "",

    budget: typeof payload.budget === "number" ? payload.budget : "",
    budget_basis: (payload.budget_basis as string) || "Total trip",
    currency: (payload.currency as string) || "USD",
    pricing_type: (payload.pricing_type as string) || "Gross",
    commission: typeof payload.commission === "number" ? payload.commission : "",
    show_commission: (payload.show_commission as string) || "No",
    price_display: (payload.price_display as string) || "Total journey price",
    target_gp: typeof payload.target_gp === "number" ? payload.target_gp : "",
    minimum_gp: typeof payload.minimum_gp === "number" ? payload.minimum_gp : "",
    contingency: typeof payload.contingency === "number" ? payload.contingency : "",
    payment_fee: typeof payload.payment_fee === "number" ? payload.payment_fee : "",
    tax_treatment: (payload.tax_treatment as string) || "",
    discount_cap: (payload.discount_cap as string) || "",
    quote_validity: (payload.quote_validity as string) || "",
    payment_terms: (payload.payment_terms as string) || "",

    existing_template: (payload.existing_template as string) || "",
    rates_available: (payload.rates_available as string) || "",
    rfq_required: (payload.rfq_required as string) || "",
    rate_risk: (payload.rate_risk as string) || "",
    preferred_suppliers: (payload.preferred_suppliers as string) || "",
    missing_info: (payload.missing_info as string) || "",
    journey_direction: (payload.journey_direction as string) || "",
    selling_angle: (payload.selling_angle as string) || "",
    competitor: (payload.competitor as string) || "",
    internal_notes: (payload.internal_notes as string) || "",

    website: "",
  };
}

export function formStateToRequestPayload(
  formState: QuoteRequestFormState,
  itineraryDays: BasicDayItem[] = [],
  changeSummary?: string
): Record<string, unknown> {
  const isTraveller = formState.role === "traveller";
  const customerName = isTraveller
    ? `${formState.first_name} ${formState.last_name}`.trim() || formState.first_name || "Traveller"
    : `${formState.advisor_first_name} ${formState.advisor_last_name}`.trim() || formState.advisor_first_name || "Advisor";

  const email = isTraveller ? formState.email : formState.advisor_email;
  const phone = isTraveller ? formState.phone : formState.advisor_phone;

  return {
    role: formState.role,
    brand_id: formState.brand_id || "selvara",
    travel_designer_id: formState.travel_designer_id || null,
    created_by_profile_id: formState.travel_designer_id || null,
    partner_id: formState.partner_id || null,
    priority: formState.priority || "normal",
    lead_source: formState.lead_source || null,
    quote_deadline: formState.quote_deadline || null,
    decision_date: formState.decision_date || null,

    customer_name: customerName || "Valued Client",
    client_name: !isTraveller && formState.client_name ? formState.client_name : null,
    email: email || "client@example.com",
    phone: phone || null,
    company_name: !isTraveller ? formState.advisor_company || null : null,
    market: isTraveller ? formState.country || null : formState.advisor_market || null,
    preferred_contact: isTraveller ? formState.preferred_contact || null : null,
    client_context: formState.client_context || null,

    destinations: formState.destinations && formState.destinations.length > 0 ? formState.destinations : [formState.destination],
    destination_refs: formState.destination_refs || null,
    display_route_text: formState.display_route_text || null,
    start_date: isTraveller && formState.arrival_date ? formState.arrival_date : null,
    end_date: isTraveller && formState.departure_date ? formState.departure_date : null,
    raw_dates_text: !isTraveller && formState.raw_dates_text ? formState.raw_dates_text : null,
    travel_timing: formState.travel_timing || null,
    date_flexibility: formState.travel_timing || null,
    arrival_city: formState.arrival_city || null,
    departure_city: formState.departure_city || null,
    room_configuration: formState.room_configuration || null,
    routing_constraints: formState.routing_constraints || null,

    adults: formState.adults || 2,
    children: formState.children || 0,
    kid_ages: formState.kid_ages || [],
    infants: formState.infants || 0,
    children_details: null,

    travel_style: isTraveller ? formState.primary_theme : formState.advisor_journey_type,
    travel_pace: formState.travel_pace || null,
    priority_1: formState.priority_1 || null,
    priority_2: formState.priority_2 || null,
    priority_3: formState.priority_3 || null,
    occasion: formState.occasion || null,
    must_have: formState.must_have || null,
    avoid: formState.avoid || null,
    interests: formState.interests || null,
    privacy: formState.privacy || null,
    experience_expectations: formState.experience_expectations || null,
    special_requirements: formState.message || null,

    // Accommodation
    hotel_level: formState.hotel_level || null,
    preferred_hotel: formState.preferred_hotel || null,
    room_type: formState.room_type || null,
    bedding: formState.bedding || null,
    connecting: formState.connecting || null,
    suite_interest: formState.suite_interest || null,
    hotel_style: formState.hotel_style || null,

    // Service Scope
    private_vehicle: formState.private_vehicle || null,
    vehicle_preference: formState.vehicle_preference || null,
    guide_language: formState.guide_language || null,
    guide_scope: formState.guide_scope || null,
    domestic_flights: formState.domestic_flights || null,
    intl_flights: formState.intl_flights || null,
    rail_cruise: formState.rail_cruise || null,
    transport_class: formState.transport_class || null,
    meal_plan: formState.meal_plan || null,
    dining_level: formState.dining_level || null,
    experiences_included: formState.experiences_included || null,
    optional_activities: formState.optional_activities || null,
    visa_fasttrack: formState.visa_fasttrack || null,
    meet_assist: formState.meet_assist || null,
    insurance: formState.insurance || null,
    other_services: formState.other_services || null,

    // Special Requirements
    dietary: formState.dietary || null,
    halal: formState.halal || null,
    mobility: formState.mobility || null,
    health_considerations: formState.health_considerations || null,

    // Commercial Parameters
    budget: formState.budget === "" ? null : Number(formState.budget),
    budget_basis: formState.budget_basis || null,
    currency: formState.currency || "USD",
    pricing_type: formState.pricing_type || null,
    commission: formState.commission === "" ? null : Number(formState.commission),
    show_commission: formState.show_commission || null,
    price_display: formState.price_display || null,
    target_gp: formState.target_gp === "" ? null : Number(formState.target_gp),
    minimum_gp: formState.minimum_gp === "" ? null : Number(formState.minimum_gp),
    contingency: formState.contingency === "" ? null : Number(formState.contingency),
    payment_fee: formState.payment_fee === "" ? null : Number(formState.payment_fee),
    tax_treatment: formState.tax_treatment || null,
    discount_cap: formState.discount_cap || null,
    quote_validity: formState.quote_validity || null,
    payment_terms: formState.payment_terms || null,

    // Readiness & Strategy
    existing_template: formState.existing_template || null,
    rates_available: formState.rates_available || null,
    rfq_required: formState.rfq_required || null,
    rate_risk: formState.rate_risk || null,
    preferred_suppliers: formState.preferred_suppliers || null,
    missing_info: formState.missing_info || null,
    journey_direction: formState.journey_direction || null,
    selling_angle: formState.selling_angle || null,
    competitor: formState.competitor || null,
    internal_notes: formState.internal_notes || null,

    itinerary_days: itineraryDays,
    change_summary: changeSummary?.trim() || undefined,
    website: formState.website || null,
  };
}
