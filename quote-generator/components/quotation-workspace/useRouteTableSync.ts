"use client";

import { useCallback, useMemo } from "react";
import type { DayWithStayItem } from "./DayEmbeddedRouteTable.tsx";
import type { ItineraryDayFact, QuotationFacts } from "./factsTypes.ts";
import { ensureFactsDefaults, routeDestinationRefsFromItinerary } from "./factsTypes.ts";
import { POPULAR_DESTINATIONS } from "../destination/useDestinationSearch.ts";
import { inferOvernightDestination } from "../../lib/prefillRules.ts";
import { patchItineraryDayInFacts } from "../../lib/prefillEngine.ts";
import { staysAdapter } from "../../lib/rules/staysAdapter.ts";
import { staysReconciler } from "../../lib/rules/staysReconciler.ts";
import { tripReconciler, type CanonicalDay } from "../../lib/rules/tripReconciler.ts";

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

export function updateDayInRouteTable(
  current: QuotationFacts,
  index: number,
  patch: Partial<DayWithStayItem>
): QuotationFacts {
  const safe = ensureFactsDefaults(current);
  const canonical = staysAdapter.fromQuotationFacts(safe);
  const prevDay = index > 0 ? canonical.itinerary[index - 1] : null;
  const currentDay = canonical.itinerary[index];
  if (!currentDay) return current;

  const updatedPatch: Partial<ItineraryDayFact> = {
    ...patch,
  };

  // If destination changed, check if overnight was in sync with destination
  if (patch.destination !== undefined && patch.destination !== currentDay.destination) {
    const newDest = patch.destination;
    if (!currentDay.overnight || currentDay.overnight === currentDay.destination) {
      updatedPatch.overnight = inferOvernightDestination(newDest, currentDay.overnight);
      updatedPatch.destination_ref = patch.destination_ref ?? null;
    }

    // Auto-inherit accommodation from previous day if same destination and no accommodation selected in patch
    if (
      prevDay &&
      (prevDay.destination === newDest || prevDay.overnight === newDest) &&
      prevDay.accommodation_id &&
      !patch.accommodation_id
    ) {
      updatedPatch.accommodation_id = prevDay.accommodation_id;
      updatedPatch.accommodation_name = prevDay.accommodation_name;
      updatedPatch.room_type = prevDay.room_type;
    }
  }

  // If accommodation is patched, delegate to staysReconciler.updateDayAccommodation
  if (
    updatedPatch.accommodation_id !== undefined ||
    updatedPatch.accommodation_name !== undefined ||
    updatedPatch.room_type !== undefined
  ) {
    const { itinerary, stays } = staysReconciler.updateDayAccommodation(
      canonical.itinerary,
      index,
      updatedPatch,
      canonical.startDate,
      safe.service_facts.hotels
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

    return staysAdapter.syncToQuotationFacts(
      { ...canonical, itinerary, stays, destinationRefs: destination_refs, destinations },
      safe
    );
  }

  // Otherwise patch itinerary day normally via prefillEngine
  return patchItineraryDayInFacts(safe, index, updatedPatch);
}

export function addDayToRouteTable(
  current: QuotationFacts,
  defaultPayload?: Partial<DayWithStayItem> | Partial<ItineraryDayFact> | Partial<CanonicalDay>
): QuotationFacts {
  const safe = ensureFactsDefaults(current);
  const canonical = staysAdapter.fromQuotationFacts(safe);
  const reconciled = tripReconciler.addDay(
    canonical,
    defaultPayload as Partial<CanonicalDay> | undefined
  );
  const nextStays = staysReconciler.reconcileStaysFromItinerary(
    reconciled.itinerary,
    reconciled.startDate,
    safe.service_facts.hotels
  );
  const destination_refs = routeDestinationRefsFromItinerary(reconciled.itinerary as ItineraryDayFact[]);
  const destinations =
    destination_refs.length > 0
      ? destination_refs.map((r) => r.name)
      : Array.from(
          new Set(
            reconciled.itinerary
              .map((d) => d.destination)
              .filter((d): d is string => Boolean(d))
          )
        );

  return staysAdapter.syncToQuotationFacts(
    { ...reconciled, stays: nextStays, destinationRefs: destination_refs, destinations },
    safe
  );
}

export function removeDayFromRouteTable(
  current: QuotationFacts,
  index: number
): QuotationFacts {
  const safe = ensureFactsDefaults(current);
  const canonical = staysAdapter.fromQuotationFacts(safe);
  if (canonical.itinerary.length <= 1) {
    return safe; // Guardrail: preserve at least 1 day in itinerary
  }
  const reconciled = tripReconciler.removeDay(canonical, index);
  const nextStays = staysReconciler.reconcileStaysFromItinerary(
    reconciled.itinerary,
    reconciled.startDate,
    safe.service_facts.hotels
  );
  const destination_refs = routeDestinationRefsFromItinerary(reconciled.itinerary as ItineraryDayFact[]);
  const destinations =
    destination_refs.length > 0
      ? destination_refs.map((r) => r.name)
      : Array.from(
          new Set(
            reconciled.itinerary
              .map((d) => d.destination)
              .filter((d): d is string => Boolean(d))
          )
        );

  return staysAdapter.syncToQuotationFacts(
    { ...reconciled, stays: nextStays, destinationRefs: destination_refs, destinations },
    safe
  );
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

  const handleUpdateDay = useCallback(
    (index: number, patch: Partial<DayWithStayItem>) => {
      onFactsChange((current) => updateDayInRouteTable(current, index, patch));
    },
    [onFactsChange]
  );

  const handleAddDay = useCallback(
    (defaultPayload?: Partial<DayWithStayItem>) => {
      onFactsChange((current) => addDayToRouteTable(current, defaultPayload));
    },
    [onFactsChange]
  );

  const handleRemoveDay = useCallback(
    (index: number) => {
      onFactsChange((current) => removeDayFromRouteTable(current, index));
    },
    [onFactsChange]
  );

  return {
    dayWithStays,
    handleRouteTableChange,
    handleUpdateDay,
    handleAddDay,
    handleRemoveDay,
  };
}
