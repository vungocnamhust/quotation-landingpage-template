"use client";

import { useCallback, useMemo } from "react";
import type { DayWithStayItem } from "./DayEmbeddedRouteTable";
import type { HotelFact, ItineraryDayFact, QuotationFacts } from "./factsTypes";
import { ensureFactsDefaults, routeDestinationRefsFromItinerary } from "./factsTypes";
import { inferOvernightDestination } from "../../lib/prefillRules";
import { consolidateStaysFromDayItems } from "../../lib/rules/staysRules";

export function deriveDayWithStays(facts: QuotationFacts): DayWithStayItem[] {
  const itinerary = facts.trip_facts.itinerary;
  const hotels = facts.service_facts.hotels;

  return itinerary.map((day, idx) => {
    // Attempt to match hotel with day destination/overnight
    const matchingHotel =
      hotels.find(
        (h) =>
          (h.destination && day.destination && h.destination === day.destination) ||
          (h.destination && day.overnight && h.destination === day.overnight)
      ) || hotels[idx];

    return {
      day_number: day.day_number ?? idx + 1,
      destination: day.destination,
      destination_ref: day.destination_ref,
      accommodation_id: matchingHotel?.accommodation_id ?? null,
      accommodation_name: matchingHotel?.name ?? null,
      room_type: matchingHotel?.room_type ?? null,
      summary: day.summary,
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
    return {
      day_number: item.day_number,
      destination: item.destination,
      destination_ref: item.destination_ref ?? null,
      summary: item.summary,
      overnight: inferOvernightDestination(
        item.destination,
        existing?.overnight || item.destination
      ),
      highlights: existing?.highlights ?? [],
      meals: existing?.meals ?? ["Breakfast"],
      notes: existing?.notes ?? [],
      sense_of_pace: existing?.sense_of_pace ?? "balanced",
      display_date: existing?.display_date ?? null,
    };
  });

  const destinationRefs = routeDestinationRefsFromItinerary(itinerary);

  // Consolidate contiguous stays from day items using domain rules
  const consolidatedHotels = consolidateStaysFromDayItems(items, safe.trip_facts.start_date);
  const hotels: HotelFact[] =
    consolidatedHotels.length > 0 ? consolidatedHotels : safe.service_facts.hotels;

  return {
    ...safe,
    trip_facts: {
      ...safe.trip_facts,
      itinerary,
      destination_refs: destinationRefs,
      destinations: destinationRefs.map((r) => r.name),
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
