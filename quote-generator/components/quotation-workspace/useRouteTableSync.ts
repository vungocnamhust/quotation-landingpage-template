"use client";

import { useCallback, useMemo } from "react";
import type { DayWithStayItem } from "./DayEmbeddedRouteTable.tsx";
import type { ItineraryDayFact, QuotationFacts } from "./factsTypes.ts";
import { ensureFactsDefaults, routeDestinationRefsFromItinerary } from "./factsTypes.ts";
import { POPULAR_DESTINATIONS } from "../destination/useDestinationSearch.ts";
import { staysAdapter } from "../../lib/rules/staysAdapter.ts";
import { staysReconciler } from "../../lib/rules/staysReconciler.ts";

export function deriveDayWithStays(facts: QuotationFacts): DayWithStayItem[] {
  const safe = ensureFactsDefaults(facts);
  const canonical = staysAdapter.fromQuotationFacts(safe);
  const hydratedItinerary = staysReconciler.syncItineraryFromStays(
    canonical.itinerary,
    safe.service_facts.hotels,
    safe.trip_facts.start_date
  );

  return hydratedItinerary.map((day, idx) => {
    const dest = day.destination ?? null;
    const overnight = day.overnight ?? dest ?? null;
    const overnightRef = overnight
      ? POPULAR_DESTINATIONS.find(
          (p) =>
            p.name.toLowerCase() === overnight.toLowerCase() ||
            p.slug.toLowerCase() === overnight.toLowerCase() ||
            p.id.toLowerCase() === overnight.toLowerCase()
        ) ?? null
      : null;

    return {
      day_number: day.day_number ?? idx + 1,
      destination: dest,
      destination_ref: day.destination_ref ?? null,
      overnight,
      overnight_ref: overnightRef,
      accommodation_id: day.accommodation_id ?? null,
      accommodation_name: day.accommodation_name ?? null,
      room_type: day.room_type ?? null,
      summary: day.summary ?? null,
    };
  });
}

export function syncRouteTableToFacts(
  current: QuotationFacts,
  items: DayWithStayItem[]
): QuotationFacts {
  const safe = ensureFactsDefaults(current);

  const itinerary: ItineraryDayFact[] = items.map((item, idx) => {
    const existing = safe.trip_facts.itinerary[idx];
    const resolvedOvernight =
      item.overnight !== undefined
        ? item.overnight
        : (existing?.overnight || item.destination);

    return {
      day_number: item.day_number,
      destination: item.destination,
      destination_ref: item.destination_ref ?? null,
      summary: item.summary,
      overnight: resolvedOvernight,
      highlights: existing?.highlights ?? [],
      meals: existing?.meals ?? ["Breakfast"],
      notes: existing?.notes ?? [],
      sense_of_pace: existing?.sense_of_pace ?? "balanced",
      display_date: existing?.display_date ?? null,
      accommodation_id: item.accommodation_id ?? null,
      accommodation_name: item.accommodation_name ?? null,
      room_type: item.room_type ?? null,
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

  const stays = staysReconciler.reconcileStaysFromItinerary(
    itinerary,
    safe.trip_facts.start_date,
    safe.service_facts.hotels
  );
  const hotels = staysReconciler.toHotelFacts(stays);

  return {
    ...safe,
    trip_facts: {
      ...safe.trip_facts,
      itinerary,
      destination_refs: destinationRefs,
      destinations,
    },
    service_facts: {
      ...safe.service_facts,
      hotels,
    },
  };
}

export function useRouteTableSync(
  facts: QuotationFacts,
  onFactsChange: (updater: (prev: QuotationFacts) => QuotationFacts) => void
) {
  const dayWithStays = useMemo(() => deriveDayWithStays(facts), [facts]);

  const handleRouteTableChange = useCallback(
    (newItems: DayWithStayItem[]) => {
      onFactsChange((current) => syncRouteTableToFacts(current, newItems));
    },
    [onFactsChange]
  );

  return {
    dayWithStays,
    handleRouteTableChange,
  };
}
