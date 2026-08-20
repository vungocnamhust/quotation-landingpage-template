/**
 * Adapter module bridging application schemas (QuotationFacts, QuoteRequestFormState, DayWithStayItem[])
 * with the unified CanonicalTripWithStays model used by staysReconciler.
 */

import type { DayWithStayItem } from "../../components/quotation-workspace/DayEmbeddedRouteTable.tsx";
import type { BasicDayItem } from "../../components/quotation-workspace/BasicItineraryDayGrid.tsx";
import type {
  HotelFact,
  ItineraryDayFact,
  QuotationFacts,
} from "../../components/quotation-workspace/factsTypes.ts";
import {
  ensureFactsDefaults,
  routeDestinationRefsFromItinerary,
} from "../../components/quotation-workspace/factsTypes.ts";
import type { QuoteRequestFormState } from "../quoteRequestPayload.ts";
import { calculateDuration, formatTravelDatesLabel } from "./datesRules.ts";
import type { CanonicalDay } from "./tripReconciler.ts";
import { staysReconciler, type CanonicalStay, type CanonicalTripWithStays } from "./staysReconciler.ts";

export const staysAdapter = {
  /**
   * Convert QuotationFacts to CanonicalTripWithStays.
   */
  fromQuotationFacts(factsInput: QuotationFacts): CanonicalTripWithStays {
    const facts = ensureFactsDefaults(factsInput);
    const trip = facts.trip_facts;
    const start = trip.start_date?.trim() || null;
    const end = trip.end_date?.trim() || null;
    const duration = calculateDuration(start, end);

    const canonicalDays: CanonicalDay[] = trip.itinerary.map((d, index) => ({
      id: `day_${d.day_number || index + 1}`,
      day_number: d.day_number || index + 1,
      destination: d.destination || null,
      destination_ref: d.destination_ref ?? null,
      overnight: d.overnight || d.destination || null,
      display_date: d.display_date || null,
      summary: d.summary || null,
      meals: d.meals || [],
      highlights: d.highlights || [],
      notes: d.notes || [],
      sense_of_pace: d.sense_of_pace || "balanced",
      accommodation_id: d.accommodation_id || null,
      accommodation_name: d.accommodation_name || null,
      room_type: d.room_type || null,
    }));

    // If day accommodations are present, reconcile stays from day items;
    // otherwise if hotels list is provided, use staysReconciler to structure stays
    const stays: CanonicalStay[] =
      canonicalDays.some((d) => Boolean(d.accommodation_id || d.accommodation_name))
        ? staysReconciler.reconcileStaysFromItinerary(
            canonicalDays,
            start,
            facts.service_facts.hotels
          )
        : facts.service_facts.hotels.map((h, i) => ({
            id: `stay_${h.accommodation_id || i + 1}`,
            accommodation_id: h.accommodation_id,
            name: h.name,
            destination: h.destination,
            destination_ref: h.destination_ref ?? null,
            room_type: h.room_type,
            day_start: i + 1,
            day_end: i + 1,
            nights: 1,
            check_in: h.check_in,
            check_out: h.check_out,
            intro: h.intro,
            phone: h.phone,
            display_city: h.display_city,
            display_date: h.display_date,
            hotel_asset: h.hotel_asset,
            room_asset: h.room_asset,
          }));

    return {
      startDate: start,
      endDate: end,
      durationDays: duration.durationDays ?? (canonicalDays.length || null),
      durationNights:
        duration.durationNights ??
        (canonicalDays.length ? Math.max(0, canonicalDays.length - 1) : null),
      itinerary: canonicalDays,
      stays,
      lang: facts.lang || "en",
    };
  },

  /**
   * Synchronize CanonicalTripWithStays back to QuotationFacts.
   */
  syncToQuotationFacts(
    canonical: CanonicalTripWithStays,
    prevInput: QuotationFacts
  ): QuotationFacts {
    const safe = ensureFactsDefaults(prevInput);

    const itinerary: ItineraryDayFact[] = canonical.itinerary.map((d, index) => {
      const existing = safe.trip_facts.itinerary[index];
      return {
        day_number: d.day_number || index + 1,
        destination: d.destination || null,
        destination_ref: d.destination_ref ?? null,
        overnight: d.overnight || d.destination || null,
        display_date: d.display_date || null,
        summary: (d.summary as string) || null,
        meals: d.meals && d.meals.length ? d.meals : existing?.meals ?? ["Breakfast"],
        highlights: d.highlights ?? existing?.highlights ?? [],
        notes: d.notes ?? existing?.notes ?? [],
        sense_of_pace: (d.sense_of_pace as string) || existing?.sense_of_pace || "balanced",
        accommodation_id: (d.accommodation_id as string) || null,
        accommodation_name: (d.accommodation_name as string) || null,
        room_type: (d.room_type as string) || null,
      };
    });

    const destinationRefs = routeDestinationRefsFromItinerary(itinerary);
    const hotels = staysReconciler.toHotelFacts(canonical.stays);

    // Fallback destinations list: use destinationRefs if available, or unique destination names from itinerary
    const destinations =
      destinationRefs.length > 0
        ? destinationRefs.map((r) => r.name)
        : Array.from(
            new Set(
              itinerary.map((d) => d.destination).filter((d): d is string => Boolean(d))
            )
          );

    return {
      ...safe,
      trip_facts: {
        ...safe.trip_facts,
        start_date: canonical.startDate,
        end_date: canonical.endDate,
        duration_days: canonical.durationDays,
        duration_nights: canonical.durationNights,
        itinerary,
        destination_refs: destinationRefs,
        destinations,
      },
      service_facts: {
        ...safe.service_facts,
        hotels,
      },
    };
  },

  /**
   * Convert QuoteRequestFormState + BasicDayItem[] to CanonicalTripWithStays.
   */
  fromQuoteRequest(
    formState: QuoteRequestFormState,
    days: BasicDayItem[] = []
  ): CanonicalTripWithStays {
    const start = formState.arrival_date?.trim() || null;
    const end = formState.departure_date?.trim() || null;
    const duration = calculateDuration(start, end);

    const canonicalDays: CanonicalDay[] = days.map((d, index) => ({
      id: d.id || `day_${d.day_number || index + 1}`,
      day_number: d.day_number || index + 1,
      destination: d.destination || null,
      destination_ref: d.destination_ref_id
        ? { id: d.destination_ref_id, name: d.destination, slug: "" }
        : null,
      overnight: d.overnight || d.destination || null,
      display_date: d.display_date || null,
      summary: d.summary || null,
      meals: d.meals || [],
      highlights: d.highlights || [],
      notes: d.notes || [],
    }));

    const stays = staysReconciler.reconcileStaysFromItinerary(canonicalDays, start);

    return {
      startDate: start,
      endDate: end,
      durationDays: duration.durationDays ?? (canonicalDays.length || null),
      durationNights:
        duration.durationNights ??
        (canonicalDays.length ? Math.max(0, canonicalDays.length - 1) : null),
      itinerary: canonicalDays,
      stays,
      lang: "en",
    };
  },

  /**
   * Synchronize CanonicalTripWithStays back to QuoteRequestFormState + BasicDayItem[].
   */
  syncToQuoteRequest(
    canonical: CanonicalTripWithStays,
    prev: QuoteRequestFormState
  ): { formState: QuoteRequestFormState; itineraryDays: BasicDayItem[] } {
    const rawDatesText = formatTravelDatesLabel(
      canonical.startDate,
      canonical.endDate,
      prev.raw_dates_text
    );

    const itineraryDays: BasicDayItem[] = canonical.itinerary.map((d, index) => ({
      id: (d.id as string) || `day_${d.day_number || index + 1}`,
      day_number: d.day_number || index + 1,
      destination: d.destination || "",
      destination_ref_id: d.destination_ref?.id || null,
      overnight: d.overnight || d.destination || "",
      display_date: d.display_date || "",
      summary: (d.summary as string) || "",
      meals: d.meals || [],
      highlights: d.highlights || [],
      notes: d.notes || [],
    }));

    return {
      formState: {
        ...prev,
        arrival_date: canonical.startDate || "",
        departure_date: canonical.endDate || "",
        raw_dates_text: rawDatesText,
      },
      itineraryDays,
    };
  },

  /**
   * Convert DayWithStayItem[] into CanonicalTripWithStays.
   */
  fromDayWithStays(
    items: DayWithStayItem[],
    startDate: string | null | undefined,
    prevHotels: HotelFact[] = []
  ): CanonicalTripWithStays {
    const canonicalDays: CanonicalDay[] = items.map((item, idx) => ({
      day_number: item.day_number ?? idx + 1,
      destination: item.destination,
      destination_ref: item.destination_ref ?? null,
      overnight: item.destination,
      summary: item.summary,
      display_date: null,
      accommodation_id: item.accommodation_id ?? null,
      accommodation_name: item.accommodation_name ?? null,
      room_type: item.room_type ?? null,
    }));

    const stays = staysReconciler.reconcileStaysFromItinerary(
      canonicalDays,
      startDate,
      prevHotels
    );

    return {
      startDate: startDate ?? null,
      endDate: null,
      durationDays: items.length || null,
      durationNights: items.length ? Math.max(0, items.length - 1) : null,
      itinerary: canonicalDays,
      stays,
      lang: "en",
    };
  },

  /**
   * Convert CanonicalTripWithStays to DayWithStayItem[].
   */
  toDayWithStays(canonical: CanonicalTripWithStays): DayWithStayItem[] {
    return canonical.itinerary.map((day, idx) => ({
      day_number: day.day_number ?? idx + 1,
      destination: day.destination,
      destination_ref: day.destination_ref ?? null,
      accommodation_id: day.accommodation_id ?? null,
      accommodation_name: day.accommodation_name ?? null,
      room_type: day.room_type ?? null,
      summary: day.summary ?? null,
    }));
  },
};
