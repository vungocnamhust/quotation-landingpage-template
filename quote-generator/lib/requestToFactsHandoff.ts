import type { QuotationFacts, QuoteRequestItem } from "../components/quotation-workspace/factsTypes.ts";
import { resolveClientDisplayName } from "./rules/partyRules.ts";
import { currencyDivisor, inferRatesFromGroupTotal } from "./rules/pricingRules.ts";

/**
 * Pure utility function to build initial QuotationFacts from a QuoteRequestItem.
 * Used when generating a new quotation directly from a staff workspace request.
 */
export function buildInitialFactsFromRequest(
  quoteRequest: QuoteRequestItem | null | undefined,
  fallback: QuotationFacts
): QuotationFacts {
  if (!quoteRequest) return fallback;
  const payload = (quoteRequest.payload_json || {}) as Record<string, unknown>;
  const clientName = payload.client_name as string | undefined;
  const displayName = resolveClientDisplayName(quoteRequest.role, quoteRequest.customer_name, clientName);

  const rawItinerary = payload.itinerary_days as Array<Record<string, unknown>> | undefined;
  const itineraryDays =
    Array.isArray(rawItinerary) && rawItinerary.length > 0
      ? rawItinerary.map((d, i) => ({
          day_number: Number(d.day_number) || i + 1,
          destination: (d.destination as string) || null,
          destination_ref: null,
          summary: (d.summary as string) || null,
          overnight: (d.destination as string) || null,
          meals: ["Breakfast"],
          highlights: [],
          notes: [],
          sense_of_pace: "balanced" as const,
          display_date: (d.display_date as string) || null,
          accommodation_id: null,
          accommodation_name: null,
          room_type: null,
        }))
      : fallback.trip_facts.itinerary;


  const adults = quoteRequest.adults ?? fallback.customer_facts.adults ?? 2;
  const children = quoteRequest.children ?? fallback.customer_facts.children ?? 0;
  const kidAges = quoteRequest.kid_ages ?? fallback.customer_facts.kid_ages ?? [];

  const budget = payload.budget ? Number(payload.budget) : null;
  const currency = (payload.currency as string) || "USD";
  const divisor = currencyDivisor(currency);
  const totalMinor = budget
    ? Math.round(budget * divisor)
    : fallback.pricing_facts.options[0]?.group_total_amount_minor ?? 700000;

  const { perAdultMinor, perChildMinor } = inferRatesFromGroupTotal(totalMinor, adults, children, 0.75);
  const effectiveAdultMinor = perAdultMinor ?? totalMinor;

  const routeMeta = deriveRouteFromItinerary(itineraryDays);
  const finalDestinations =
    quoteRequest.destinations?.length && quoteRequest.destinations[0]
      ? quoteRequest.destinations
      : routeMeta.destinations.length > 0
        ? routeMeta.destinations
        : fallback.trip_facts.destinations;

  const displayRouteText =
    formatRouteString(finalDestinations) || fallback.trip_facts.display_route_text;

  return {
    ...fallback,
    brand_id: (payload.brand_id as string) || fallback.brand_id || "selvara",
    presentation_options: {
      ...fallback.presentation_options,
      travel_designer_id:
        quoteRequest.created_by_profile_id ||
        (payload.travel_designer_id as string) ||
        fallback.presentation_options.travel_designer_id,
    },
    trip_facts: {
      ...fallback.trip_facts,
      destinations: finalDestinations,
      destination_refs:
        routeMeta.destinationRefs.length > 0
          ? routeMeta.destinationRefs
          : fallback.trip_facts.destination_refs,
      start_date: quoteRequest.start_date || fallback.trip_facts.start_date,
      end_date: quoteRequest.end_date || fallback.trip_facts.end_date,
      itinerary: itineraryDays,
      display_route_text: displayRouteText,
      display_travel_dates: quoteRequest.raw_dates_text || fallback.trip_facts.display_travel_dates,
      ...(payload.routing_constraints
        ? { routing_constraints: payload.routing_constraints as string }
        : {}),
    },
    customer_facts: {
      ...fallback.customer_facts,
      customer_name: displayName,
      adults,
      children,
      kid_ages: kidAges,
      market: quoteRequest.market || fallback.customer_facts.market,
      travel_style: quoteRequest.travel_style || fallback.customer_facts.travel_style,
      advisor_name: quoteRequest.role === "advisor" ? quoteRequest.customer_name : null,
      advisor_agency: quoteRequest.role === "advisor" ? quoteRequest.company_name : null,
    },
    pricing_facts: {
      ...fallback.pricing_facts,
      options: [
        {
          id: "opt-standard",
          label: "Standard Luxury Option",
          currency,
          per_traveler_amount_minor: effectiveAdultMinor,
          group_total_amount_minor: totalMinor,
          per_adult_amount_minor: effectiveAdultMinor,
          per_child_amount_minor: perChildMinor,
        },
      ],
    },
  };
}
