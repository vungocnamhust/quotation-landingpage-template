import {
  createItineraryDay,
  dateForItineraryDay,
  ensureFactsDefaults,
  routeDestinationRefsFromItinerary,
  type DestinationRef,
  type HotelFact,
  type ItineraryDayFact,
  type PricingOptionFact,
  type QuotationFacts,
} from "../components/quotation-workspace/factsTypes.ts";
import {
  deriveStaySegmentsFromItinerary,
  getDefaultMealsForLang,
  inferOvernightDestination,
  syncHotelsFromStaySegments,
} from "./prefillRules.ts";
import { parseIsoDate } from "./rules/datesRules.ts";
import { formatStayDisplayDate, staysReconciler } from "./rules/staysReconciler.ts";
import { partyAdapter } from "./rules/partyAdapter.ts";
import { partyReconciler } from "./rules/partyReconciler.ts";
import { staysAdapter } from "./rules/staysAdapter.ts";
import { pricingAdapter } from "./rules/pricingAdapter.ts";
import { pricingReconciler, type CanonicalPricingOption } from "./rules/pricingReconciler.ts";

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
  const canonicalParty = partyAdapter.fromQuotationFacts(current);
  const updatedParty = partyReconciler.setCustomerName(canonicalParty, rawName);
  return partyAdapter.syncToQuotationFacts(updatedParty, current);
}

/**
 * Single-pass updater when changing adult or child traveler counts.
 * Automatically resizes kid_ages array vector and synchronizes pricing options total price with new Pax counts.
 */
export function updateCustomerCounts(
  input: QuotationFacts,
  { adults, children }: { adults?: number | null; children?: number | null },
): QuotationFacts {
  const current = ensureFactsDefaults(input);
  const canonicalParty = partyAdapter.fromQuotationFacts(current);

  let updatedParty = canonicalParty;
  if (adults !== undefined && adults !== null) {
    updatedParty = partyReconciler.setAdults(updatedParty, adults);
  }
  if (children !== undefined && children !== null) {
    updatedParty = partyReconciler.setChildren(updatedParty, children);
  }

  // Sync pricing options with new Pax counts
  const canonicalPricing = pricingAdapter.fromQuotationFacts(current);
  const syncedPricing = pricingReconciler.syncPaxCounts(
    canonicalPricing,
    updatedParty.adults,
    updatedParty.children
  );
  const syncedFacts = pricingAdapter.syncToQuotationFacts(syncedPricing, current);

  return partyAdapter.syncToQuotationFacts(updatedParty, syncedFacts);
}

/**
 * Single-pass updater when modifying kid ages vector.
 */
export function updateCustomerKidAges(
  input: QuotationFacts,
  kidAges: number[]
): QuotationFacts {
  const current = ensureFactsDefaults(input);
  const canonicalParty = partyAdapter.fromQuotationFacts(current);
  const reconciledParty = partyReconciler.reconcileParty({
    ...canonicalParty,
    kidAges,
  });
  return partyAdapter.syncToQuotationFacts(reconciledParty, current);
}

/**
 * Single-pass updater when modifying individual kid age.
 */
export function updateCustomerKidAgeAtIndex(
  input: QuotationFacts,
  index: number,
  age: number
): QuotationFacts {
  const current = ensureFactsDefaults(input);
  const canonicalParty = partyAdapter.fromQuotationFacts(current);
  const updatedParty = partyReconciler.setKidAge(canonicalParty, index, age);
  return partyAdapter.syncToQuotationFacts(updatedParty, current);
}

/**
 * Single-pass updater when modifying room notes & requests.
 */
export function updateCustomerRoomNotes(
  input: QuotationFacts,
  roomNotes: string | null
): QuotationFacts {
  const current = ensureFactsDefaults(input);
  const canonicalParty = partyAdapter.fromQuotationFacts(current);
  const updatedParty = partyReconciler.setRoomNotes(canonicalParty, roomNotes);
  return partyAdapter.syncToQuotationFacts(updatedParty, current);
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
  const destinations =
    destination_refs.length > 0
      ? destination_refs.map((r) => r.name)
      : Array.from(
          new Set(
            itinerary.map((d) => d.destination).filter((d): d is string => Boolean(d))
          )
        );

  return {
    ...current,
    trip_facts: {
      ...current.trip_facts,
      itinerary,
      destination_refs,
      destinations,
    },
  };
}

/**
 * Single-pass updater for updating travel dates & route itinerary size.
 * Also shifts check_in/check_out of hotel stays in sync.
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
  const destinations =
    destination_refs.length > 0
      ? destination_refs.map((r) => r.name)
      : Array.from(
          new Set(
            itinerary.map((d) => d.destination).filter((d): d is string => Boolean(d))
          )
        );

  // Shift stay dates if hotels exist
  const canonical = staysAdapter.fromQuotationFacts({
    ...current,
    trip_facts: {
      ...current.trip_facts,
      start_date: startDate,
      end_date: endDate,
      itinerary,
    },
  });
  const shiftedStays = staysReconciler.shiftStayDates(canonical.stays, startDate, canonical.itinerary);
  const hotels = staysReconciler.toHotelFacts(shiftedStays);

  return {
    ...current,
    trip_facts: {
      ...current.trip_facts,
      start_date: startDate,
      end_date: endDate,
      duration_days: nextLength,
      duration_nights: Math.max(0, nextLength - 1),
      itinerary,
      destination_refs,
      destinations,
    },
    service_facts: {
      ...current.service_facts,
      hotels,
    },
  };
}

/**
 * Single-pass hotel sync from itinerary overnights using staysReconciler.
 */
export function syncHotelsFromItineraryOvernights(input: QuotationFacts): QuotationFacts {
  const current = ensureFactsDefaults(input);
  const canonical = staysAdapter.fromQuotationFacts(current);
  const reconciledStays = staysReconciler.reconcileStaysFromItinerary(
    canonical.itinerary,
    canonical.startDate,
    current.service_facts.hotels
  );

  if (reconciledStays.length > 0) {
    return staysAdapter.syncToQuotationFacts(
      { ...canonical, stays: reconciledStays },
      current
    );
  }

  const segments = deriveStaySegmentsFromItinerary(
    current.trip_facts.itinerary,
    current.trip_facts.start_date,
    current.trip_facts.end_date
  );
  const hotels = syncHotelsFromStaySegments(current.service_facts.hotels, segments);
  return {
    ...current,
    service_facts: {
      ...current.service_facts,
      hotels,
    },
  };
}

/**
 * Single-pass updater when editing a day's accommodation, with automatic smart cascading.
 */
export function updateDayAccommodationInFacts(
  input: QuotationFacts,
  index: number,
  patch: Partial<ItineraryDayFact>
): QuotationFacts {
  const current = ensureFactsDefaults(input);
  const canonical = staysAdapter.fromQuotationFacts(current);
  const { itinerary, stays } = staysReconciler.updateDayAccommodation(
    canonical.itinerary,
    index,
    patch,
    canonical.startDate,
    current.service_facts.hotels
  );
  return staysAdapter.syncToQuotationFacts(
    { ...canonical, itinerary, stays },
    current
  );
}

/**
 * Single-pass updater for modifying an itinerary day's attributes or destination.
 * Automatically handles overnight prefill, destination_refs rebuild, and delegates
 * accommodation changes to updateDayAccommodationInFacts.
 */
export function patchItineraryDayInFacts(
  input: QuotationFacts,
  index: number,
  patch: Partial<ItineraryDayFact>
): QuotationFacts {
  if (
    patch.accommodation_id !== undefined ||
    patch.accommodation_name !== undefined ||
    patch.room_type !== undefined
  ) {
    return updateDayAccommodationInFacts(input, index, patch);
  }

  const current = ensureFactsDefaults(input);
  const existingDay = current.trip_facts.itinerary[index];
  if (!existingDay) return current;

  const destName = patch.destination !== undefined ? patch.destination : existingDay.destination;
  let resolvedOvernight = existingDay.overnight;
  if (patch.overnight !== undefined) {
    resolvedOvernight = patch.overnight;
  } else if (patch.destination !== undefined) {
    if (!existingDay.overnight || existingDay.overnight === existingDay.destination) {
      resolvedOvernight = destName;
    }
  }

  const updatedDay: ItineraryDayFact = {
    ...existingDay,
    ...patch,
    destination: destName,
    overnight: resolvedOvernight,
  };

  const itinerary = current.trip_facts.itinerary.map((item, itemIndex) =>
    itemIndex === index ? updatedDay : item
  );

  const destination_refs = routeDestinationRefsFromItinerary(itinerary);
  const destinations =
    destination_refs.length > 0
      ? destination_refs.map((r) => r.name)
      : Array.from(
          new Set(
            itinerary.map((d) => d.destination).filter((d): d is string => Boolean(d))
          )
        );

  return {
    ...current,
    trip_facts: {
      ...current.trip_facts,
      itinerary,
      destination_refs,
      destinations,
    },
  };
}

/**
 * Single-pass updater for adding a new hotel to service_facts.hotels.
 * Automatically computes check_in / check_out based on the last existing hotel or trip start date.
 */
export function addHotelToFacts(input: QuotationFacts): QuotationFacts {
  const current = ensureFactsDefaults(input);
  const existingHotels = current.service_facts.hotels;
  const lastHotel = existingHotels.length > 0 ? existingHotels[existingHotels.length - 1] : null;

  let checkIn: string | null = null;
  let checkOut: string | null = null;

  if (lastHotel?.check_out) {
    checkIn = lastHotel.check_out;
    const cinDate = parseIsoDate(checkIn);
    if (cinDate) {
      const nextDay = new Date(cinDate.getTime() + 86_400_000);
      checkOut = nextDay.toISOString().split("T")[0];
    }
  } else if (current.trip_facts.start_date) {
    checkIn = current.trip_facts.start_date;
    const cinDate = parseIsoDate(checkIn);
    if (cinDate) {
      const nextDay = new Date(cinDate.getTime() + 86_400_000);
      checkOut = nextDay.toISOString().split("T")[0];
    }
  }

  const newHotel: HotelFact = {
    accommodation_id: null,
    destination: null,
    destination_ref: null,
    name: null,
    room_type: null,
    check_in: checkIn,
    check_out: checkOut,
    intro: null,
    phone: null,
    display_city: null,
    display_date: formatStayDisplayDate(checkIn, checkOut, current.lang || undefined),
    hotel_asset: null,
    room_asset: null,
  };

  return {
    ...current,
    service_facts: {
      ...current.service_facts,
      hotels: [...existingHotels, newHotel],
    },
  };
}

/**
 * Single-pass updater for removing a hotel from service_facts.hotels.
 * Automatically synchronizes itinerary days via staysReconciler.
 */
export function removeHotelFromFacts(input: QuotationFacts, index: number): QuotationFacts {
  const current = ensureFactsDefaults(input);
  const hotels = current.service_facts.hotels.filter((_, i) => i !== index);

  const canonical = staysAdapter.fromQuotationFacts(current);
  const syncedItinerary = staysReconciler.syncItineraryFromStays(
    canonical.itinerary,
    hotels,
    canonical.startDate
  );
  const reconciledStays = staysReconciler.reconcileStaysFromItinerary(
    syncedItinerary,
    canonical.startDate,
    hotels
  );

  return staysAdapter.syncToQuotationFacts(
    {
      ...canonical,
      itinerary: syncedItinerary,
      stays: reconciledStays,
    },
    {
      ...current,
      service_facts: {
        ...current.service_facts,
        hotels,
      },
    }
  );
}

/**
 * Single-pass updater when modifying a hotel in service_facts.hotels,
 * automatically syncing accommodation metadata to corresponding itinerary days.
 */
export function patchHotelInFacts(
  input: QuotationFacts,
  index: number,
  patch: Partial<HotelFact>
): QuotationFacts {
  const current = ensureFactsDefaults(input);
  const hotels = current.service_facts.hotels.map((h, i) =>
    i === index ? { ...h, ...patch } : h
  );

  // Sync back to itinerary days
  const canonical = staysAdapter.fromQuotationFacts(current);
  const syncedItinerary = staysReconciler.syncItineraryFromStays(
    canonical.itinerary,
    hotels,
    canonical.startDate
  );
  const reconciledStays = staysReconciler.reconcileStaysFromItinerary(
    syncedItinerary,
    canonical.startDate,
    hotels
  );

  return staysAdapter.syncToQuotationFacts(
    {
      ...canonical,
      itinerary: syncedItinerary,
      stays: reconciledStays,
    },
    {
      ...current,
      service_facts: {
        ...current.service_facts,
        hotels,
      },
    }
  );
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
  const canonical = pricingAdapter.fromQuotationFacts(current);
  const canonicalPatch: Partial<CanonicalPricingOption> = {};

  if (patch.label !== undefined) {
    canonicalPatch.label = patch.label;
  }
  if (patch.currency !== undefined) {
    canonicalPatch.currency = patch.currency ?? undefined;
  }
  if (patch.per_adult_amount_minor !== undefined) {
    canonicalPatch.perAdultMinor = patch.per_adult_amount_minor;
  } else if (patch.per_traveler_amount_minor !== undefined) {
    canonicalPatch.perAdultMinor = patch.per_traveler_amount_minor;
  }
  if (patch.per_child_amount_minor !== undefined) {
    canonicalPatch.perChildMinor = patch.per_child_amount_minor;
  }
  if (patch.group_total_amount_minor !== undefined) {
    canonicalPatch.groupTotalMinor = patch.group_total_amount_minor;
  }

  const updated = pricingReconciler.updateOption(canonical, index, canonicalPatch);
  return pricingAdapter.syncToQuotationFacts(updated, current);
}

/**
 * Single-pass updater when changing adult rate for a pricing option.
 */
export function updatePricingOptionAdultInFacts(
  input: QuotationFacts,
  index: number,
  perAdultMinor: number | null
): QuotationFacts {
  const current = ensureFactsDefaults(input);
  const canonical = pricingAdapter.fromQuotationFacts(current);
  if (index < 0 || index >= canonical.options.length) return current;

  const updatedOption = pricingReconciler.updateOptionPerAdult(
    canonical.options[index],
    perAdultMinor,
    canonical.adults,
    canonical.children
  );
  const nextOptions = [...canonical.options];
  nextOptions[index] = updatedOption;

  return pricingAdapter.syncToQuotationFacts({ ...canonical, options: nextOptions }, current);
}

/**
 * Single-pass updater when changing child rate for a pricing option.
 */
export function updatePricingOptionChildInFacts(
  input: QuotationFacts,
  index: number,
  perChildMinor: number | null
): QuotationFacts {
  const current = ensureFactsDefaults(input);
  const canonical = pricingAdapter.fromQuotationFacts(current);
  if (index < 0 || index >= canonical.options.length) return current;

  const updatedOption = pricingReconciler.updateOptionPerChild(
    canonical.options[index],
    perChildMinor,
    canonical.adults,
    canonical.children
  );
  const nextOptions = [...canonical.options];
  nextOptions[index] = updatedOption;

  return pricingAdapter.syncToQuotationFacts({ ...canonical, options: nextOptions }, current);
}

/**
 * Single-pass updater when applying a child preset ratio to a pricing option.
 */
export function applyChildPresetInFacts(
  input: QuotationFacts,
  index: number,
  ratio: number
): QuotationFacts {
  const current = ensureFactsDefaults(input);
  const canonical = pricingAdapter.fromQuotationFacts(current);
  if (index < 0 || index >= canonical.options.length) return current;

  const updatedOption = pricingReconciler.applyChildPreset(
    canonical.options[index],
    ratio,
    canonical.adults,
    canonical.children
  );
  const nextOptions = [...canonical.options];
  nextOptions[index] = updatedOption;

  return pricingAdapter.syncToQuotationFacts({ ...canonical, options: nextOptions }, current);
}

/**
 * Single-pass updater when changing group total for a pricing option.
 */
export function updatePricingOptionTotalInFacts(
  input: QuotationFacts,
  index: number,
  groupTotalMinor: number | null
): QuotationFacts {
  const current = ensureFactsDefaults(input);
  const canonical = pricingAdapter.fromQuotationFacts(current);
  if (index < 0 || index >= canonical.options.length) return current;

  const updatedOption = pricingReconciler.updateOptionTotal(
    canonical.options[index],
    groupTotalMinor,
    canonical.adults,
    canonical.children
  );
  const nextOptions = [...canonical.options];
  nextOptions[index] = updatedOption;

  return pricingAdapter.syncToQuotationFacts({ ...canonical, options: nextOptions }, current);
}

/**
 * Single-pass updater when converting currency for a pricing option.
 */
export function convertOptionCurrencyInFacts(
  input: QuotationFacts,
  index: number,
  nextCurrency: string,
  convertAmounts = true
): QuotationFacts {
  const current = ensureFactsDefaults(input);
  const canonical = pricingAdapter.fromQuotationFacts(current);
  if (index < 0 || index >= canonical.options.length) return current;

  const updatedOption = pricingReconciler.convertOptionCurrency(
    canonical.options[index],
    nextCurrency,
    {
      convertAmounts,
      adults: canonical.adults,
      children: canonical.children,
    }
  );
  const nextOptions = [...canonical.options];
  nextOptions[index] = updatedOption;

  return pricingAdapter.syncToQuotationFacts({ ...canonical, options: nextOptions }, current);
}

/**
 * Single-pass updater when changing travel style.
 * Updates both travel_style and guest_profile to guarantee backward compatibility.
 */
export function updateTravelStyle(input: QuotationFacts, rawStyle: string | null): QuotationFacts {
  const current = ensureFactsDefaults(input);
  const canonical = partyAdapter.fromQuotationFacts(current);
  const updated = partyReconciler.reconcileParty({
    ...canonical,
    travelStyle: rawStyle?.trim() || null,
  });
  return partyAdapter.syncToQuotationFacts(updated, current);
}

export type DesignerPresentationPatch = Partial<QuotationFacts["designer_facts"]> & {
  booking_title?: string | null;
  booking_description?: string | null;
  customer_market?: string | null;
  customer_greeting_name?: string | null;
  customer_party_label?: string | null;
};

/**
 * Single-pass updater when saving designer presentation facts from Design Canvas.
 * Synchronizes booking title/description, customer labels, market, and designer facts via partyAdapter.
 */
export function updateDesignerPresentationFacts(
  input: QuotationFacts,
  patch: DesignerPresentationPatch
): QuotationFacts {
  const current = ensureFactsDefaults(input);
  const canonicalParty = partyAdapter.fromQuotationFacts(current);

  let updatedParty = canonicalParty;
  if (patch.customer_party_label !== undefined) {
    updatedParty = partyReconciler.setPartyLabel(updatedParty, patch.customer_party_label);
  }
  if (patch.customer_greeting_name !== undefined) {
    updatedParty = partyReconciler.setGreetingName(updatedParty, patch.customer_greeting_name);
  }
  if (patch.customer_market !== undefined) {
    updatedParty = {
      ...updatedParty,
      market: patch.customer_market || null,
    };
  }

  const syncedPartyFacts = partyAdapter.syncToQuotationFacts(updatedParty, current);

  return {
    ...syncedPartyFacts,
    booking_facts: {
      ...syncedPartyFacts.booking_facts,
      ...(patch.booking_title !== undefined ? { title: patch.booking_title || null } : {}),
      ...(patch.booking_description !== undefined ? { description: patch.booking_description || null } : {}),
    },
    designer_facts: {
      ...syncedPartyFacts.designer_facts,
      ...patch,
    },
  };
}


