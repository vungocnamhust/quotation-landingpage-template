import {
  createItineraryDay,
  dateForItineraryDay,
  ensureFactsDefaults,
  routeDestinationRefsFromItinerary,
  type DestinationRef,
  type ItineraryDayFact,
  type PricingOptionFact,
  type QuotationFacts,
} from "../components/quotation-workspace/factsTypes";
import {
  deriveStaySegmentsFromItinerary,
  getDefaultMealsForLang,
  inferCommercialPerTraveler,
  inferCommercialTotal,
  inferGreetingName,
  inferOvernightDestination,
  inferPartyLabel,
  syncHotelsFromStaySegments,
} from "./prefillRules";

/**
 * Creates an itinerary day with default meals localized by quotation language.
 */
export function createItineraryDayWithDefaults({
  index,
  startDate,
  lang,
}: {
  index: number;
  startDate: string | null;
  lang?: QuotationFacts["lang"];
}): ItineraryDayFact {
  const baseDay = createItineraryDay({ index, startDate });
  return {
    ...baseDay,
    meals: getDefaultMealsForLang(lang),
  };
}

/**
 * Single-pass updater when changing customer name.
 * Automatically updates party_label and greeting_name if they match their previous inferred defaults or are blank.
 */
export function updateCustomerName(input: QuotationFacts, rawName: string | null): QuotationFacts {
  const current = ensureFactsDefaults(input);
  const name = rawName?.trim() || null;
  const cust = current.customer_facts;

  const prevParty = inferPartyLabel(cust.customer_name, cust.adults, cust.children);
  const prevGreeting = inferGreetingName(cust.customer_name);

  const isPartyDefaultOrBlank = !cust.party_label || cust.party_label === prevParty;
  const isGreetingDefaultOrBlank = !cust.greeting_name || cust.greeting_name === prevGreeting;

  return {
    ...current,
    customer_facts: {
      ...cust,
      customer_name: name,
      party_label: isPartyDefaultOrBlank ? inferPartyLabel(name, cust.adults, cust.children) : cust.party_label,
      greeting_name: isGreetingDefaultOrBlank ? inferGreetingName(name) : cust.greeting_name,
    },
  };
}

/**
 * Single-pass updater when changing adult or child traveler counts.
 */
export function updateCustomerCounts(
  input: QuotationFacts,
  { adults, children }: { adults?: number | null; children?: number | null },
): QuotationFacts {
  const current = ensureFactsDefaults(input);
  const cust = current.customer_facts;

  const nextAdults = adults !== undefined ? adults : cust.adults;
  const nextChildren = children !== undefined ? children : cust.children;

  const prevParty = inferPartyLabel(cust.customer_name, cust.adults, cust.children);
  const isPartyDefaultOrBlank = !cust.party_label || cust.party_label === prevParty;

  return {
    ...current,
    customer_facts: {
      ...cust,
      adults: nextAdults,
      children: nextChildren,
      party_label: isPartyDefaultOrBlank ? inferPartyLabel(cust.customer_name, nextAdults, nextChildren) : cust.party_label,
    },
  };
}

/**
 * Single-pass updater when changing destination for an itinerary day.
 * Prefills overnight if blank and rebuilds routeDestinationRefs.
 */
export function updateItineraryDayDestination(
  input: QuotationFacts,
  index: number,
  destination: string | null,
  ref?: DestinationRef | null,
): QuotationFacts {
  const current = ensureFactsDefaults(input);
  const currentDays = current.trip_facts.itinerary;

  const itinerary = currentDays.map((day, dayIndex) => {
    if (dayIndex !== index) return day;
    const destName = destination || ref?.name || null;
    const overnight = inferOvernightDestination(destName, day.overnight);
    return {
      ...day,
      destination: destName,
      destination_ref: ref ?? null,
      overnight,
    };
  });

  const destination_refs = routeDestinationRefsFromItinerary(itinerary);
  return {
    ...current,
    trip_facts: {
      ...current.trip_facts,
      itinerary,
      destination_refs,
      destinations: destination_refs.map((r) => r.name),
    },
  };
}

/**
 * Single-pass updater for updating travel dates & route itinerary size.
 */
export function applyRouteDates(
  input: QuotationFacts,
  startDate: string | null,
  endDate: string | null,
  nextLength: number,
): QuotationFacts {
  const current = ensureFactsDefaults(input);
  const currentDays = current.trip_facts.itinerary;

  const itinerary = Array.from({ length: nextLength }, (_, index) => {
    const existing = currentDays[index];
    if (existing) {
      return {
        ...existing,
        day_number: index + 1,
        display_date: dateForItineraryDay(startDate, index + 1),
        meals: existing.meals.length ? existing.meals : getDefaultMealsForLang(current.lang),
      };
    }
    return createItineraryDayWithDefaults({ index, startDate, lang: current.lang });
  });

  const destination_refs = routeDestinationRefsFromItinerary(itinerary);
  return {
    ...current,
    trip_facts: {
      ...current.trip_facts,
      start_date: startDate,
      end_date: endDate,
      itinerary,
      destination_refs,
      destinations: destination_refs.map((ref) => ref.name),
    },
  };
}

/**
 * Single-pass hotel sync from itinerary overnights.
 */
export function syncHotelsFromItineraryOvernights(input: QuotationFacts): QuotationFacts {
  const current = ensureFactsDefaults(input);
  const segments = deriveStaySegmentsFromItinerary(
    current.trip_facts.itinerary,
    current.trip_facts.start_date,
    current.trip_facts.end_date,
  );
  const syncedHotels = syncHotelsFromStaySegments(current.service_facts.hotels, segments);

  return {
    ...current,
    service_facts: {
      ...current.service_facts,
      hotels: syncedHotels,
    },
  };
}

/**
 * Patch a pricing option with automatic 2-way per traveler <-> group total price inference.
 */
export function patchPricingOptionWithInference(
  input: QuotationFacts,
  index: number,
  patch: Partial<PricingOptionFact>,
): QuotationFacts {
  const current = ensureFactsDefaults(input);
  const adults = current.customer_facts.adults;

  const options = current.pricing_facts.options.map((option, optionIndex) => {
    if (optionIndex !== index) return option;

    const updated = { ...option, ...patch };

    // If per traveler changed and group total is blank, auto-infer group total
    if (patch.per_traveler_amount_minor !== undefined && patch.group_total_amount_minor === undefined) {
      if (updated.group_total_amount_minor === null && patch.per_traveler_amount_minor !== null && adults) {
        updated.group_total_amount_minor = inferCommercialTotal(patch.per_traveler_amount_minor, adults);
      }
    }

    // If group total changed and per traveler is blank, auto-infer per traveler
    if (patch.group_total_amount_minor !== undefined && patch.per_traveler_amount_minor === undefined) {
      if (updated.per_traveler_amount_minor === null && patch.group_total_amount_minor !== null && adults) {
        updated.per_traveler_amount_minor = inferCommercialPerTraveler(patch.group_total_amount_minor, adults);
      }
    }

    return updated;
  });

  return {
    ...current,
    pricing_facts: {
      ...current.pricing_facts,
      options,
    },
  };
}

/**
 * Single-pass updater when changing travel style.
 * Updates both travel_style and guest_profile to guarantee backward compatibility.
 */
export function updateTravelStyle(input: QuotationFacts, rawStyle: string | null): QuotationFacts {
  const current = ensureFactsDefaults(input);
  const style = rawStyle?.trim() || null;
  return {
    ...current,
    customer_facts: {
      ...current.customer_facts,
      travel_style: style,
      guest_profile: style,
    },
  };
}

