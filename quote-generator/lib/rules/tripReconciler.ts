/**
 * Pure domain rules for temporal trip reconciliation (TypeScript).
 * Guarantees invariant synchronization between startDate, endDate, duration, and daily itinerary items.
 */

import {
  addDaysToIsoDate,
  calculateDuration,
  dateForItineraryDay,
  formatDisplayDate,
  isValidIsoDate,
} from "./datesRules.ts";
import {
  deriveRouteFromItinerary,
  type DestinationRef,
} from "./routeRules.ts";

export type CanonicalDay = {
  id?: string;
  day_number: number | null;
  title?: string | null;
  destination: string | null;
  destination_ref?: DestinationRef | null;
  overnight: string | null;
  display_date: string | null;
  summary: string | null;
  meals?: string[];
  highlights?: string[];
  notes?: string[];
  sense_of_pace?: string | null;
  accommodation_id?: string | null;
  accommodation_name?: string | null;
  room_type?: string | null;
  [key: string]: unknown;
};

export type CanonicalTrip = {
  startDate: string | null;
  endDate: string | null;
  durationDays: number | null;
  durationNights: number | null;
  arrivalCity?: string | null;
  departureCity?: string | null;
  destinations?: string[];
  destinationRefs?: DestinationRef[];
  displayRouteText?: string | null;
  routingConstraints?: string | null;
  itinerary: CanonicalDay[];
  lang?: "en" | "vi" | "ar" | string | null;
};

const DEFAULT_MEALS_BY_LANG: Record<string, string[]> = {
  en: ["Breakfast"],
  vi: ["Bữa sáng"],
  ar: ["الإفطار"],
};

export function getDefaultMeals(lang?: string | null): string[] {
  if (lang && DEFAULT_MEALS_BY_LANG[lang]) {
    return [...DEFAULT_MEALS_BY_LANG[lang]];
  }
  return [...DEFAULT_MEALS_BY_LANG.en];
}

export const tripReconciler = {
  /**
   * Synchronize route metadata (arrivalCity, departureCity, destinations, destinationRefs, displayRouteText)
   * based on the current itinerary items.
   */
  syncRouteMetadata<T extends CanonicalTrip>(trip: T): T {
    const routeMeta = deriveRouteFromItinerary(trip.itinerary);
    return {
      ...trip,
      arrivalCity: routeMeta.arrivalCity ?? trip.arrivalCity ?? null,
      departureCity: routeMeta.departureCity ?? trip.departureCity ?? null,
      destinations: routeMeta.destinations.length > 0 ? routeMeta.destinations : (trip.destinations ?? []),
      destinationRefs: routeMeta.destinationRefs.length > 0 ? routeMeta.destinationRefs : (trip.destinationRefs ?? []),
      displayRouteText: routeMeta.displayRouteText ?? trip.displayRouteText ?? null,
    };
  },

  /**
   * Apply an ordered list of destinations (from RouteSequenceInput or parser) to the trip.
   * Expands the itinerary if needed, updates day destinations, and recalculates duration/dates.
   */
  applyRouteSequence<T extends CanonicalTrip>(
    trip: T,
    destinationItems: Array<string | DestinationRef>
  ): T {
    if (!destinationItems || destinationItems.length === 0) {
      return trip;
    }

    const normalizedItems: DestinationRef[] = destinationItems.map((item, idx) => {
      if (typeof item === "string") {
        const clean = item.trim();
        const lower = clean.toLowerCase().replace(/[^a-z0-9]/g, "_");
        return {
          id: `dst_${lower || idx}`,
          name: clean,
          slug: clean.toLowerCase().replace(/\s+/g, "-"),
        };
      }
      return item;
    });

    const targetLength = Math.max(trip.itinerary.length, normalizedItems.length);
    const defaultMeals = getDefaultMeals(trip.lang);
    const lang = trip.lang || "en";

    let nextEndDate = trip.endDate;
    if (trip.startDate && isValidIsoDate(trip.startDate)) {
      nextEndDate = addDaysToIsoDate(trip.startDate, targetLength - 1);
    }

    const nextItinerary: CanonicalDay[] = [];
    for (let i = 0; i < targetLength; i++) {
      const dayNum = i + 1;
      const projectedIso = dateForItineraryDay(trip.startDate, dayNum);
      const projectedLabel = projectedIso ? formatDisplayDate(projectedIso, lang) : null;
      const destRef = i < normalizedItems.length ? normalizedItems[i] : null;
      const existingDay = i < trip.itinerary.length ? trip.itinerary[i] : null;

      const destName = destRef?.name || existingDay?.destination || null;
      const overnight = destName || existingDay?.overnight || null;

      nextItinerary.push({
        id: existingDay?.id || `day_${Date.now()}_${dayNum}`,
        day_number: dayNum,
        title: existingDay?.title || null,
        destination: destName,
        destination_ref: destRef ?? existingDay?.destination_ref ?? null,
        overnight,
        display_date: existingDay?.display_date || projectedLabel,
        summary: existingDay?.summary || null,
        meals: existingDay?.meals?.length ? existingDay.meals : [...defaultMeals],
        highlights: existingDay?.highlights || [],
        notes: existingDay?.notes || [],
        sense_of_pace: existingDay?.sense_of_pace || "balanced",
        accommodation_id: existingDay?.accommodation_id ?? null,
        accommodation_name: existingDay?.accommodation_name ?? null,
        room_type: existingDay?.room_type ?? null,
      });
    }

    const { durationDays, durationNights } = calculateDuration(trip.startDate, nextEndDate);
    const routeMeta = deriveRouteFromItinerary(nextItinerary);

    return {
      ...trip,
      endDate: nextEndDate,
      durationDays: durationDays ?? targetLength,
      durationNights: durationNights ?? Math.max(0, targetLength - 1),
      arrivalCity: routeMeta.arrivalCity,
      departureCity: routeMeta.departureCity,
      destinations: routeMeta.destinations,
      destinationRefs: routeMeta.destinationRefs,
      displayRouteText: routeMeta.displayRouteText,
      itinerary: nextItinerary,
    };
  },

  /**
   * Add a new day to the itinerary.
   * Invariant: Automatically pushes endDate by 1 day and calculates the new day's display_date.
   */
  addDay<T extends CanonicalTrip>(trip: T, defaultDayPayload?: Partial<CanonicalDay>): T {
    const nextLength = trip.itinerary.length + 1;
    let nextEndDate = trip.endDate;

    if (trip.startDate && isValidIsoDate(trip.startDate)) {
      nextEndDate = addDaysToIsoDate(trip.startDate, nextLength - 1);
    }

    const newDayNumber = nextLength;
    const projectedIso = dateForItineraryDay(trip.startDate, newDayNumber);
    const projectedLabel = projectedIso
      ? formatDisplayDate(projectedIso, trip.lang || "en")
      : null;

    const defaultMeals = getDefaultMeals(trip.lang);

    const prevDay = trip.itinerary.length > 0 ? trip.itinerary[trip.itinerary.length - 1] : null;
    const initialDest = defaultDayPayload?.destination || null;
    const inheritHotel =
      prevDay && initialDest && prevDay.destination === initialDest
        ? {
            accommodation_id: prevDay.accommodation_id ?? null,
            accommodation_name: prevDay.accommodation_name ?? null,
            room_type: prevDay.room_type ?? null,
          }
        : {};

    const newDay: CanonicalDay = {
      id: defaultDayPayload?.id || `day_${Date.now()}_${newDayNumber}`,
      day_number: newDayNumber,
      title: defaultDayPayload?.title || null,
      destination: initialDest,
      destination_ref: defaultDayPayload?.destination_ref ?? null,
      overnight: defaultDayPayload?.overnight || initialDest,
      display_date: defaultDayPayload?.display_date || projectedLabel,
      summary: defaultDayPayload?.summary || null,
      meals: defaultDayPayload?.meals?.length ? defaultDayPayload.meals : defaultMeals,
      highlights: defaultDayPayload?.highlights || [],
      notes: defaultDayPayload?.notes || [],
      sense_of_pace: defaultDayPayload?.sense_of_pace || "balanced",
      ...inheritHotel,
      ...defaultDayPayload,
    };

    const nextItinerary = [...trip.itinerary, newDay];
    const { durationDays, durationNights } = calculateDuration(trip.startDate, nextEndDate);
    const routeMeta = deriveRouteFromItinerary(nextItinerary);

    return {
      ...trip,
      endDate: nextEndDate,
      durationDays: durationDays ?? nextLength,
      durationNights: durationNights ?? Math.max(0, nextLength - 1),
      arrivalCity: routeMeta.arrivalCity ?? trip.arrivalCity ?? null,
      departureCity: routeMeta.departureCity ?? trip.departureCity ?? null,
      destinations: routeMeta.destinations.length > 0 ? routeMeta.destinations : (trip.destinations ?? []),
      destinationRefs: routeMeta.destinationRefs.length > 0 ? routeMeta.destinationRefs : (trip.destinationRefs ?? []),
      displayRouteText: routeMeta.displayRouteText ?? trip.displayRouteText ?? null,
      itinerary: nextItinerary,
    };
  },

  /**
   * Remove a day from the itinerary at a given index.
   * Invariant: Automatically pulls back endDate by 1 day and re-indexes all subsequent days.
   */
  removeDay<T extends CanonicalTrip>(trip: T, removeIndex: number): T {
    if (removeIndex < 0 || removeIndex >= trip.itinerary.length) {
      return trip;
    }

    const filtered = trip.itinerary.filter((_, i) => i !== removeIndex);
    const nextLength = filtered.length;
    let nextEndDate = trip.endDate;

    if (trip.startDate && isValidIsoDate(trip.startDate)) {
      nextEndDate =
        nextLength > 0 ? addDaysToIsoDate(trip.startDate, nextLength - 1) : trip.startDate;
    }

    const lang = trip.lang || "en";
    const reIndexed = filtered.map((day, i) => {
      const dayNum = i + 1;
      const projectedIso = dateForItineraryDay(trip.startDate, dayNum);
      const projectedLabel = projectedIso ? formatDisplayDate(projectedIso, lang) : day.display_date;
      return {
        ...day,
        day_number: dayNum,
        display_date: projectedLabel,
      };
    });

    const { durationDays, durationNights } = calculateDuration(trip.startDate, nextEndDate);
    const routeMeta = deriveRouteFromItinerary(reIndexed);

    return {
      ...trip,
      endDate: nextEndDate,
      durationDays: durationDays ?? nextLength,
      durationNights: durationNights ?? Math.max(0, nextLength - 1),
      arrivalCity: routeMeta.arrivalCity ?? trip.arrivalCity ?? null,
      departureCity: routeMeta.departureCity ?? trip.departureCity ?? null,
      destinations: routeMeta.destinations.length > 0 ? routeMeta.destinations : (trip.destinations ?? []),
      destinationRefs: routeMeta.destinationRefs.length > 0 ? routeMeta.destinationRefs : (trip.destinationRefs ?? []),
      displayRouteText: routeMeta.displayRouteText ?? trip.displayRouteText ?? null,
      itinerary: reIndexed,
    };
  },

  /**
   * Set or change trip startDate.
   * Invariant: Shifts display_date for all existing days and updates endDate to preserve duration.
   */
  setStartDate<T extends CanonicalTrip>(trip: T, nextStartDate: string | null): T {
    const start = nextStartDate?.trim() || null;
    const length = trip.itinerary.length;
    let nextEndDate = trip.endDate;

    if (start && isValidIsoDate(start) && length > 0) {
      nextEndDate = addDaysToIsoDate(start, length - 1);
    }

    const lang = trip.lang || "en";
    const reIndexed = trip.itinerary.map((day, i) => {
      const dayNum = i + 1;
      const projectedIso = dateForItineraryDay(start, dayNum);
      const projectedLabel = projectedIso ? formatDisplayDate(projectedIso, lang) : null;
      return {
        ...day,
        day_number: dayNum,
        display_date: projectedLabel,
      };
    });

    const { durationDays, durationNights } = calculateDuration(start, nextEndDate);
    const routeMeta = deriveRouteFromItinerary(reIndexed);

    return {
      ...trip,
      startDate: start,
      endDate: nextEndDate,
      durationDays: durationDays ?? length,
      durationNights: durationNights ?? Math.max(0, length - 1),
      arrivalCity: routeMeta.arrivalCity ?? trip.arrivalCity ?? null,
      departureCity: routeMeta.departureCity ?? trip.departureCity ?? null,
      destinations: routeMeta.destinations.length > 0 ? routeMeta.destinations : (trip.destinations ?? []),
      destinationRefs: routeMeta.destinationRefs.length > 0 ? routeMeta.destinationRefs : (trip.destinationRefs ?? []),
      displayRouteText: routeMeta.displayRouteText ?? trip.displayRouteText ?? null,
      itinerary: reIndexed,
    };
  },

  /**
   * Set or change trip endDate.
   * Invariant: Resizes the itinerary array to match the calculated span between startDate and endDate.
   */
  setEndDate<T extends CanonicalTrip>(trip: T, nextEndDate: string | null): T {
    const end = nextEndDate?.trim() || null;
    const { durationDays, durationNights } = calculateDuration(trip.startDate, end);

    let nextItinerary = [...trip.itinerary];
    const lang = trip.lang || "en";

    if (durationDays !== null && durationDays !== trip.itinerary.length) {
      if (durationDays > trip.itinerary.length) {
        const defaultMeals = getDefaultMeals(trip.lang);
        while (nextItinerary.length < durationDays) {
          const dayNum = nextItinerary.length + 1;
          const projectedIso = dateForItineraryDay(trip.startDate, dayNum);
          const projectedLabel = projectedIso ? formatDisplayDate(projectedIso, lang) : null;
          nextItinerary.push({
            id: `day_${Date.now()}_${dayNum}`,
            day_number: dayNum,
            title: null,
            destination: null,
            overnight: null,
            display_date: projectedLabel,
            summary: null,
            meals: [...defaultMeals],
            highlights: [],
            notes: [],
            sense_of_pace: "balanced",
          });
        }
      } else {
        nextItinerary = nextItinerary.slice(0, durationDays);
      }
    }

    const routeMeta = deriveRouteFromItinerary(nextItinerary);

    return {
      ...trip,
      endDate: end,
      durationDays,
      durationNights,
      arrivalCity: routeMeta.arrivalCity ?? trip.arrivalCity ?? null,
      departureCity: routeMeta.departureCity ?? trip.departureCity ?? null,
      destinations: routeMeta.destinations.length > 0 ? routeMeta.destinations : (trip.destinations ?? []),
      destinationRefs: routeMeta.destinationRefs.length > 0 ? routeMeta.destinationRefs : (trip.destinationRefs ?? []),
      displayRouteText: routeMeta.displayRouteText ?? trip.displayRouteText ?? null,
      itinerary: nextItinerary,
    };
  },

  /**
   * Update an individual day item with automatic overnight inference and smart hotel cascading.
   */
  updateDay<T extends CanonicalTrip>(
    trip: T,
    index: number,
    patch: Partial<CanonicalDay>,
  ): T {
    if (index < 0 || index >= trip.itinerary.length) {
      return trip;
    }

    const currentDay = trip.itinerary[index];
    const prevDay = index > 0 ? trip.itinerary[index - 1] : null;

    let updatedDay: CanonicalDay = {
      ...currentDay,
      ...patch,
    };

    // 0. Day number change: re-calculate display_date if trip.startDate is present and patch.display_date is not explicitly provided
    if (patch.day_number !== undefined && patch.display_date === undefined) {
      const dayNum = patch.day_number;
      if (dayNum && trip.startDate) {
        const projectedIso = dateForItineraryDay(trip.startDate, dayNum);
        updatedDay.display_date = projectedIso
          ? formatDisplayDate(projectedIso, trip.lang || "en")
          : null;
      }
    }

    // 1. Destination change: auto-infer overnight if overnight was blank or matched previous destination
    if (patch.destination !== undefined && patch.destination !== currentDay.destination) {
      const isOvernightMatchingOrBlank =
        !currentDay.overnight || currentDay.overnight === currentDay.destination;
      if (isOvernightMatchingOrBlank) {
        updatedDay.overnight = patch.destination;
      }

      // Auto-inherit hotel from previous day if same destination
      if (
        prevDay &&
        prevDay.destination &&
        patch.destination &&
        prevDay.destination.toLowerCase() === patch.destination.toLowerCase() &&
        prevDay.accommodation_id &&
        !patch.accommodation_id
      ) {
        updatedDay = {
          ...updatedDay,
          accommodation_id: prevDay.accommodation_id,
          accommodation_name: prevDay.accommodation_name,
          room_type: prevDay.room_type,
        };
      }
    }

    const nextItinerary = [...trip.itinerary];
    nextItinerary[index] = updatedDay;

    // 2. Smart Hotel Cascade: If hotel changed, cascade to contiguous subsequent days with same destination
    if (
      (patch.accommodation_id !== undefined || patch.room_type !== undefined) &&
      updatedDay.destination
    ) {
      for (let i = index + 1; i < nextItinerary.length; i++) {
        if (
          nextItinerary[i].destination &&
          nextItinerary[i].destination!.toLowerCase() === updatedDay.destination.toLowerCase()
        ) {
          nextItinerary[i] = {
            ...nextItinerary[i],
            accommodation_id: updatedDay.accommodation_id ?? null,
            accommodation_name: updatedDay.accommodation_name ?? null,
            room_type: updatedDay.room_type ?? null,
          };
        } else {
          break;
        }
      }
    }

    const routeMeta = deriveRouteFromItinerary(nextItinerary);

    return {
      ...trip,
      arrivalCity: routeMeta.arrivalCity ?? trip.arrivalCity ?? null,
      departureCity: routeMeta.departureCity ?? trip.departureCity ?? null,
      destinations: routeMeta.destinations.length > 0 ? routeMeta.destinations : (trip.destinations ?? []),
      destinationRefs: routeMeta.destinationRefs.length > 0 ? routeMeta.destinationRefs : (trip.destinationRefs ?? []),
      displayRouteText: routeMeta.displayRouteText ?? trip.displayRouteText ?? null,
      itinerary: nextItinerary,
    };
  },
};
