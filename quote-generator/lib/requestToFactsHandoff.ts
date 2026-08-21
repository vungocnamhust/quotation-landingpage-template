import type {
  HotelFact,
  ItineraryDayFact,
  QuotationFacts,
  QuoteRequestItem,
} from "../components/quotation-workspace/factsTypes.ts";
import { partyReconciler } from "./rules/partyReconciler.ts";
import { pricingReconciler } from "./rules/pricingReconciler.ts";
import { getDefaultMeals, tripReconciler, type CanonicalDay, type CanonicalTrip } from "./rules/tripReconciler.ts";
import { staysReconciler, type CanonicalStay } from "./rules/staysReconciler.ts";
import { formatRouteString } from "./rules/routeRules.ts";
import { POPULAR_DESTINATIONS } from "../components/destination/useDestinationSearch.ts";

/**
 * Pure utility function to build initial QuotationFacts from a QuoteRequestItem
 * using 100% 4-Layer Domain Reconcilers (Party, Pricing, Trip, Stays).
 * Used when generating a new quotation directly from a staff workspace request.
 */
export function buildInitialFactsFromRequest(
  quoteRequest: QuoteRequestItem | null | undefined,
  fallback: QuotationFacts,
  targetLang?: string,
  defaultDesignerId?: string | null
): QuotationFacts {
  if (!quoteRequest) return fallback;

  const payload = (quoteRequest.payload_json || {}) as Record<string, unknown>;
  const lang = (targetLang || (payload.lang as string) || fallback.lang || "en") as "en" | "vi" | "ar";

  // ---------------------------------------------------------------------------
  // 1. PARTY RECONCILER
  // ---------------------------------------------------------------------------
  const rawClientName = payload.client_name as string | undefined;
  const displayName = partyReconciler.resolveClientDisplayName(
    quoteRequest.role,
    quoteRequest.customer_name,
    rawClientName
  );

  const rawAdults = quoteRequest.adults ?? fallback.customer_facts.adults ?? 2;
  const rawChildren = quoteRequest.children ?? fallback.customer_facts.children ?? 0;
  const rawKidAges = quoteRequest.kid_ages ?? fallback.customer_facts.kid_ages ?? [];
  const rawInfants = (payload.infants as number | undefined) ?? 0;

  const reconciledParty = partyReconciler.reconcileParty({
    customerName: displayName,
    clientName: rawClientName || null,
    role: quoteRequest.role || "traveller",
    adults: rawAdults,
    children: rawChildren,
    kidAges: rawKidAges,
    infants: rawInfants,
    travelStyle: quoteRequest.travel_style || fallback.customer_facts.travel_style,
    market: quoteRequest.market || fallback.customer_facts.market,
    nationality: (payload.country as string) || quoteRequest.market || fallback.customer_facts.nationality,
    roomConfiguration: (payload.room_configuration as string) || null,
    roomNotes: (payload.room_configuration as string) || (payload.hotel_style as string) || fallback.service_facts.room_notes,
    lang,
  });

  // ---------------------------------------------------------------------------
  // 2. PRICING RECONCILER
  // ---------------------------------------------------------------------------
  const currency = ((payload.currency as string) || "USD").toUpperCase();
  const divisor = pricingReconciler.currencyDivisor(currency);
  const budgetRaw = payload.budget ? Number(payload.budget) : null;
  const budgetBasis = ((payload.budget_basis as string) || "Total trip").toLowerCase();
  const isPerPerson = budgetBasis.includes("per person") || budgetBasis.includes("per_person");

  let perAdultMinor: number | null = null;
  let perChildMinor: number | null = null;
  let totalMinor: number | null = null;

  if (budgetRaw !== null && !isNaN(budgetRaw) && budgetRaw > 0) {
    const budgetMinor = Math.round(budgetRaw * divisor);
    if (isPerPerson) {
      perAdultMinor = budgetMinor;
      perChildMinor = reconciledParty.children > 0 ? Math.round(perAdultMinor * 0.75) : null;
      totalMinor = pricingReconciler.calculateOptionTotal(
        perAdultMinor,
        perChildMinor,
        reconciledParty.adults,
        reconciledParty.children
      );
    } else {
      totalMinor = budgetMinor;
      const inferred = pricingReconciler.inferOptionRatesFromTotal(
        totalMinor,
        reconciledParty.adults,
        reconciledParty.children,
        0.75
      );
      perAdultMinor = inferred.perAdultMinor;
      perChildMinor = inferred.perChildMinor;
    }
  } else {
    totalMinor = fallback.pricing_facts.options[0]?.group_total_amount_minor ?? 700000;
    const inferred = pricingReconciler.inferOptionRatesFromTotal(
      totalMinor,
      reconciledParty.adults,
      reconciledParty.children,
      0.75
    );
    perAdultMinor = inferred.perAdultMinor;
    perChildMinor = inferred.perChildMinor;
  }

  const effectiveTravelerMinor = perAdultMinor ?? totalMinor;

  // ---------------------------------------------------------------------------
  // 3. TRIP RECONCILER & DESTINATIONS
  // ---------------------------------------------------------------------------
  const defaultMeals = getDefaultMeals(lang);
  const rawItinerary = payload.itinerary_days as Array<Record<string, unknown>> | undefined;

  let initialItinerary: CanonicalDay[] = [];
  if (Array.isArray(rawItinerary) && rawItinerary.length > 0) {
    initialItinerary = rawItinerary.map((d, i) => {
      const destName = (d.destination as string) || null;
      const overnightName = (d.overnight as string) || destName || null;
      const matchedRef = destName
        ? POPULAR_DESTINATIONS.find(
            (p) =>
              p.name.toLowerCase() === destName.toLowerCase() ||
              p.slug.toLowerCase() === destName.toLowerCase() ||
              p.id.toLowerCase() === destName.toLowerCase()
          ) ?? null
        : null;

      const rawMeals = Array.isArray(d.meals) && d.meals.length > 0 ? (d.meals as string[]) : defaultMeals;

      return {
        id: `day_${d.day_number || i + 1}`,
        day_number: Number(d.day_number) || i + 1,
        title: (d.title as string) || null,
        destination: destName,
        destination_ref: matchedRef,
        summary: (d.summary as string) || null,
        overnight: overnightName,
        meals: rawMeals.map((s) => String(s).trim()).filter(Boolean),
        highlights: Array.isArray(d.highlights)
          ? (d.highlights as string[]).map((s) => String(s).trim()).filter(Boolean)
          : [],
        notes: Array.isArray(d.notes)
          ? (d.notes as string[]).map((s) => String(s).trim()).filter(Boolean)
          : [],
        sense_of_pace: (d.sense_of_pace as "relaxed" | "balanced" | "fast") || "balanced",
        display_date: (d.display_date as string) || null,
        accommodation_id: (d.accommodation_id as string) || null,
        accommodation_name: (d.accommodation_name as string) || null,
        room_type: (d.room_type as string) || null,
      };
    });
  } else if (quoteRequest.destinations && quoteRequest.destinations.length > 0) {
    // If no daily itinerary was provided, build default sequence from destinations list
    initialItinerary = quoteRequest.destinations.map((dest, idx) => {
      const matchedRef = POPULAR_DESTINATIONS.find(
        (p) =>
          p.name.toLowerCase() === dest.toLowerCase() ||
          p.slug.toLowerCase() === dest.toLowerCase() ||
          p.id.toLowerCase() === dest.toLowerCase()
      ) ?? null;
      return {
        id: `day_${idx + 1}`,
        day_number: idx + 1,
        destination: dest,
        destination_ref: matchedRef,
        summary: null,
        overnight: dest,
        meals: [...defaultMeals],
        highlights: [],
        notes: [],
        sense_of_pace: "balanced",
        display_date: null,
      };
    });
  } else {
    initialItinerary = fallback.trip_facts.itinerary.map((d, idx) => ({
      ...d,
      id: `day_${d.day_number || idx + 1}`,
      meals: d.meals && d.meals.length > 0 ? d.meals : [...defaultMeals],
    }));
  }

  const rawTrip: CanonicalTrip = {
    startDate: quoteRequest.start_date || fallback.trip_facts.start_date,
    endDate: quoteRequest.end_date || fallback.trip_facts.end_date,
    durationDays: null,
    durationNights: null,
    itinerary: initialItinerary,
    routingConstraints: (payload.routing_constraints as string) || null,
    lang,
  };

  const syncedTrip = tripReconciler.setStartDate(
    tripReconciler.syncRouteMetadata(rawTrip),
    quoteRequest.start_date || fallback.trip_facts.start_date
  );

  const finalDestinations =
    syncedTrip.destinations && syncedTrip.destinations.length > 0
      ? syncedTrip.destinations
      : quoteRequest.destinations && quoteRequest.destinations.length > 0
        ? quoteRequest.destinations
        : fallback.trip_facts.destinations;

  const displayRouteText =
    syncedTrip.displayRouteText ||
    formatRouteString(finalDestinations) ||
    fallback.trip_facts.display_route_text;

  // ---------------------------------------------------------------------------
  // 4. STAYS RECONCILER (ACCOMMODATION CLUSTERING)
  // ---------------------------------------------------------------------------
  let stays: CanonicalStay[] = staysReconciler.reconcileStaysFromItinerary(
    syncedTrip.itinerary,
    syncedTrip.startDate,
    fallback.service_facts.hotels
  );

  // If itinerary days did not have explicit hotel names, synthesize stay slots grouped by contiguous overnight
  if (stays.length === 0 && syncedTrip.itinerary.length > 0) {
    const overnightGroups: CanonicalDay[][] = [];
    for (const day of syncedTrip.itinerary) {
      const overnightCity = (day.overnight || day.destination || "").trim();
      if (!overnightCity) continue;

      const prevGroup = overnightGroups[overnightGroups.length - 1];
      const prevDay = prevGroup ? prevGroup[prevGroup.length - 1] : null;
      const prevCity = prevDay ? (prevDay.overnight || prevDay.destination || "").trim() : "";

      if (prevGroup && prevCity.toLowerCase() === overnightCity.toLowerCase()) {
        prevGroup.push(day);
      } else {
        overnightGroups.push([day]);
      }
    }

    stays = overnightGroups.map((group, idx) => {
      const first = group[0];
      const last = group[group.length - 1];
      const dayStart = first.day_number ?? idx + 1;
      const dayEnd = last.day_number ?? idx + group.length;
      const dest = first.overnight || first.destination || null;
      const destRef = first.destination_ref ?? null;

      return {
        id: `stay_${Date.now()}_${idx + 1}`,
        accommodation_id: null,
        name: null,
        destination: dest,
        destination_ref: destRef,
        room_type: "Standard Room",
        day_start: dayStart,
        day_end: dayEnd,
        nights: Math.max(1, dayEnd - dayStart + 1),
        check_in: null,
        check_out: null,
        intro: "Breakfast included.",
        phone: null,
        display_city: dest,
        display_date: null,
      };
    });

    if (syncedTrip.startDate) {
      stays = staysReconciler.shiftStayDates(stays, syncedTrip.startDate, syncedTrip.itinerary);
    }
  }

  const finalHotels: HotelFact[] =
    stays.length > 0 ? staysReconciler.toHotelFacts(stays) : fallback.service_facts.hotels;

  // Hydrate days with reconciled stays
  const hydratedItinerary: ItineraryDayFact[] = syncedTrip.itinerary.map((d, index) => {
    const existing = fallback.trip_facts.itinerary[index];
    return {
      id: d.id || existing?.id,
      day_number: d.day_number || index + 1,
      title: (d.title as string) ?? existing?.title ?? null,
      destination: d.destination || null,
      destination_ref: d.destination_ref ?? null,
      overnight: d.overnight || d.destination || null,
      display_date: d.display_date || null,
      summary: (d.summary as string) || null,
      meals: d.meals && d.meals.length > 0 ? d.meals : existing?.meals ?? [...defaultMeals],
      highlights: d.highlights ?? existing?.highlights ?? [],
      notes: d.notes ?? existing?.notes ?? [],
      sense_of_pace: (d.sense_of_pace as string) || existing?.sense_of_pace || "balanced",
      accommodation_id: (d.accommodation_id as string) || null,
      accommodation_name: (d.accommodation_name as string) || null,
      room_type: (d.room_type as string) || null,
    };
  });

  return {
    ...fallback,
    brand_id: (payload.brand_id as string) || fallback.brand_id || "selvara",
    lang,
    presentation_options: {
      ...fallback.presentation_options,
      travel_designer_id:
        quoteRequest.created_by_profile_id ||
        (payload.travel_designer_id as string) ||
        defaultDesignerId ||
        fallback.presentation_options.travel_designer_id,
      partner_id: quoteRequest.partner_id || (payload.partner_id as string) || fallback.presentation_options.partner_id,
    },
    trip_facts: {
      ...fallback.trip_facts,
      destinations: finalDestinations,
      destination_refs:
        syncedTrip.destinationRefs && syncedTrip.destinationRefs.length > 0
          ? syncedTrip.destinationRefs
          : fallback.trip_facts.destination_refs,
      start_date: syncedTrip.startDate,
      end_date: syncedTrip.endDate,
      duration_days: syncedTrip.durationDays,
      duration_nights: syncedTrip.durationNights,
      itinerary: hydratedItinerary,
      display_route_text: displayRouteText,
      display_travel_dates: quoteRequest.raw_dates_text || fallback.trip_facts.display_travel_dates,
      ...(payload.routing_constraints
        ? { routing_constraints: payload.routing_constraints as string }
        : {}),
    },
    customer_facts: {
      ...fallback.customer_facts,
      customer_name: reconciledParty.customerName,
      adults: reconciledParty.adults,
      children: reconciledParty.children,
      kid_ages: reconciledParty.kidAges,
      party_label: reconciledParty.partyLabel,
      greeting_name: reconciledParty.greetingName,
      market: reconciledParty.market ?? null,
      nationality: reconciledParty.nationality ?? null,
      travel_style: reconciledParty.travelStyle ?? null,
      guest_profile: reconciledParty.travelStyle ?? null,
      advisor_name: quoteRequest.role === "advisor" ? quoteRequest.customer_name : null,
      advisor_agency: quoteRequest.role === "advisor" ? quoteRequest.company_name : null,
    },
    service_facts: {
      ...fallback.service_facts,
      hotels: finalHotels,
      room_notes: reconciledParty.roomNotes ?? null,
    },
    pricing_facts: {
      ...fallback.pricing_facts,
      options: [
        {
          id: "opt-standard",
          label: "Standard Luxury Option",
          currency,
          per_traveler_amount_minor: effectiveTravelerMinor,
          group_total_amount_minor: totalMinor,
          per_adult_amount_minor: effectiveTravelerMinor,
          per_child_amount_minor: perChildMinor,
        },
      ],
    },
  };
}
