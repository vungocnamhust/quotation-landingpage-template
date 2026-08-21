/**
 * Adapter module bridging different application schemas (QuoteRequestFormState, QuotationFacts)
 * with the unified CanonicalTrip model used by tripReconciler.
 */

import type { BasicDayItem } from "../../components/quotation-workspace/BasicItineraryDayGrid.tsx";
import type {
  ItineraryDayFact,
  QuotationFacts,
} from "../../components/quotation-workspace/factsTypes.ts";
import {
  ensureFactsDefaults,
  routeDestinationRefsFromItinerary,
} from "../../components/quotation-workspace/factsTypes.ts";
import type { QuoteRequestFormState } from "../quoteRequestPayload.ts";
import { calculateDuration, formatTravelDatesLabel } from "./datesRules.ts";
import { deriveRouteFromItinerary, formatRouteString } from "./routeRules.ts";
import type { CanonicalDay, CanonicalTrip } from "./tripReconciler.ts";

export const tripAdapter = {
  /**
   * Convert QuoteRequestFormState + BasicDayItem[] to CanonicalTrip.
   */
  fromQuoteRequest(
    formState: QuoteRequestFormState,
    days: BasicDayItem[] = [],
  ): CanonicalTrip {
    const start = formState.arrival_date?.trim() || null;
    const end = formState.departure_date?.trim() || null;
    const duration = calculateDuration(start, end);

    const canonicalDays: CanonicalDay[] = days.map((d, index) => ({
      id: d.id || `day_${d.day_number || index + 1}`,
      day_number: d.day_number || index + 1,
      title: d.title || null,
      destination: d.destination || null,
      destination_ref: d.destination_ref_id
        ? { id: d.destination_ref_id, name: d.destination || "", slug: "" }
        : null,
      overnight: d.overnight || d.destination || null,
      display_date: d.display_date || null,
      summary: d.summary || null,
      meals: (d.meals || []).map((s) => s.trim()).filter(Boolean),
      highlights: (d.highlights || []).map((s) => s.trim()).filter(Boolean),
      notes: (d.notes || []).map((s) => s.trim()).filter(Boolean),
    }));

    const routeMeta = deriveRouteFromItinerary(canonicalDays);

    return {
      startDate: start,
      endDate: end,
      durationDays: duration.durationDays ?? (canonicalDays.length || null),
      durationNights: duration.durationNights ?? (canonicalDays.length ? Math.max(0, canonicalDays.length - 1) : null),
      arrivalCity: routeMeta.arrivalCity || formState.arrival_city?.trim() || null,
      departureCity: routeMeta.departureCity || formState.departure_city?.trim() || null,
      destinations: routeMeta.destinations.length > 0 ? routeMeta.destinations : (formState.destination ? [formState.destination] : []),
      destinationRefs: routeMeta.destinationRefs.length > 0 ? routeMeta.destinationRefs : [],
      displayRouteText: routeMeta.displayRouteText || formState.destination || null,
      routingConstraints: formState.routing_constraints || null,
      itinerary: canonicalDays,
      lang: "en",
    };
  },

  /**
   * Synchronize CanonicalTrip back to QuoteRequestFormState + BasicDayItem[].
   */
  syncToQuoteRequest(
    canonical: CanonicalTrip,
    prev: QuoteRequestFormState,
  ): { formState: QuoteRequestFormState; itineraryDays: BasicDayItem[] } {
    const rawDatesText = formatTravelDatesLabel(
      canonical.startDate,
      canonical.endDate,
      prev.raw_dates_text,
    );

    const itineraryDays: BasicDayItem[] = canonical.itinerary.map((d, index) => ({
      id: (d.id as string) || `day_${d.day_number || index + 1}`,
      day_number: d.day_number || index + 1,
      title: (d.title as string) || "",
      destination: d.destination || "",
      destination_ref_id: d.destination_ref?.id || null,
      overnight: d.overnight || d.destination || "",
      display_date: d.display_date || "",
      summary: (d.summary as string) || "",
      meals: (d.meals || []).map((s) => s.trim()).filter(Boolean),
      highlights: (d.highlights || []).map((s) => s.trim()).filter(Boolean),
      notes: (d.notes || []).map((s) => s.trim()).filter(Boolean),
    }));

    return {
      formState: {
        ...prev,
        arrival_date: canonical.startDate || "",
        departure_date: canonical.endDate || "",
        raw_dates_text: rawDatesText,
        arrival_city: canonical.arrivalCity || prev.arrival_city || "",
        departure_city: canonical.departureCity || prev.departure_city || "",
        destination: canonical.destinations?.[0] || prev.destination || "",
        routing_constraints:
          canonical.routingConstraints !== undefined && canonical.routingConstraints !== null
            ? canonical.routingConstraints
            : prev.routing_constraints,
      },
      itineraryDays,
    };
  },

  /**
   * Convert QuotationFacts to CanonicalTrip.
   */
  fromQuotationFacts(factsInput: QuotationFacts): CanonicalTrip {
    const facts = ensureFactsDefaults(factsInput);
    const trip = facts.trip_facts;
    const start = trip.start_date?.trim() || null;
    const end = trip.end_date?.trim() || null;
    const duration = calculateDuration(start, end);

    const canonicalDays: CanonicalDay[] = trip.itinerary.map((d, index) => ({
      id: d.id || `day_${d.day_number || index + 1}`,
      day_number: d.day_number || index + 1,
      title: d.title || null,
      destination: d.destination || null,
      destination_ref: d.destination_ref ?? null,
      overnight: d.overnight || d.destination || null,
      display_date: d.display_date || null,
      summary: d.summary || null,
      meals: (d.meals || []).map((s) => s.trim()).filter(Boolean),
      highlights: (d.highlights || []).map((s) => s.trim()).filter(Boolean),
      notes: (d.notes || []).map((s) => s.trim()).filter(Boolean),
      sense_of_pace: d.sense_of_pace || "balanced",
      accommodation_id: d.accommodation_id || null,
      accommodation_name: d.accommodation_name || null,
      room_type: d.room_type || null,
    }));

    const routeMeta = deriveRouteFromItinerary(canonicalDays);

    return {
      startDate: start,
      endDate: end,
      durationDays: duration.durationDays ?? (canonicalDays.length || null),
      durationNights: duration.durationNights ?? (canonicalDays.length ? Math.max(0, canonicalDays.length - 1) : null),
      arrivalCity: routeMeta.arrivalCity || (trip as unknown as { arrival_city?: string }).arrival_city || null,
      departureCity: routeMeta.departureCity || (trip as unknown as { departure_city?: string }).departure_city || null,
      destinations: routeMeta.destinations.length > 0 ? routeMeta.destinations : (trip.destinations || []),
      destinationRefs: routeMeta.destinationRefs.length > 0 ? routeMeta.destinationRefs : (trip.destination_refs || []),
      displayRouteText: routeMeta.displayRouteText || trip.display_route_text || null,
      routingConstraints: (trip as unknown as { routing_constraints?: string }).routing_constraints || null,
      itinerary: canonicalDays,
      lang: facts.lang || "en",
    };
  },

  /**
   * Synchronize CanonicalTrip back to QuotationFacts.
   */
  syncToQuotationFacts(
    canonical: CanonicalTrip,
    prevInput: QuotationFacts,
  ): QuotationFacts {
    const safe = ensureFactsDefaults(prevInput);

    const itinerary: ItineraryDayFact[] = canonical.itinerary.map((d, index) => {
      const existing = safe.trip_facts.itinerary.find((item) => item.id && item.id === d.id) || safe.trip_facts.itinerary[index];
      const rawMeals = d.meals && d.meals.length ? d.meals : existing?.meals ?? ["Breakfast"];
      return {
        id: d.id || existing?.id,
        day_number: d.day_number || index + 1,
        title: (d.title as string) ?? existing?.title ?? null,
        destination: d.destination || null,
        destination_ref: d.destination_ref ?? null,
        overnight: d.overnight || d.destination || null,
        display_date: d.display_date || null,
        summary: (d.summary as string) || null,
        meals: rawMeals.map((s) => s.trim()).filter(Boolean),
        highlights: (d.highlights ?? existing?.highlights ?? []).map((s) => s.trim()).filter(Boolean),
        notes: (d.notes ?? existing?.notes ?? []).map((s) => s.trim()).filter(Boolean),
        sense_of_pace: (d.sense_of_pace as string) || existing?.sense_of_pace || "balanced",
        accommodation_id: (d.accommodation_id as string) || existing?.accommodation_id || null,
        accommodation_name: (d.accommodation_name as string) || existing?.accommodation_name || null,
        room_type: (d.room_type as string) || existing?.room_type || null,
      };
    });

    const destinationRefs = routeDestinationRefsFromItinerary(itinerary);
    const destinations =
      destinationRefs.length > 0
        ? destinationRefs.map((r) => r.name)
        : Array.from(
            new Set(
              itinerary.map((d) => d.destination).filter((d): d is string => Boolean(d))
            )
          );
    const displayRouteText = canonical.displayRouteText || formatRouteString(destinations);

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
        display_route_text: displayRouteText,
        ...(canonical.routingConstraints ? { routing_constraints: canonical.routingConstraints } : {}),
      },
    };
  },
};
