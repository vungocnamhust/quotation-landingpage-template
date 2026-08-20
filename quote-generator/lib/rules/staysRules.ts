/**
 * Pure domain rules for accommodation stay consolidation (TypeScript).
 * Thin backward-compatibility wrapper delegating to staysReconciler.ts.
 */

import type { HotelFact, DestinationRef } from "../../components/quotation-workspace/factsTypes.ts";
import { staysReconciler, type CanonicalStay } from "./staysReconciler.ts";
import type { CanonicalDay } from "./tripReconciler.ts";

export type DayItemWithStayLike = {
  day_number?: number | null;
  destination?: string | null;
  destination_ref?: DestinationRef | null;
  accommodation_id?: string | null;
  accommodation_name?: string | null;
  room_type?: string | null;
  summary?: string | null;
  overnight?: string | null;
};

/**
 * @deprecated Use staysReconciler.reconcileStaysFromItinerary instead.
 */
export function consolidateStaysFromDayItems(
  items: DayItemWithStayLike[],
  startDate: string | null | undefined,
  prevHotels: HotelFact[] = []
): HotelFact[] {
  if (!items || items.length === 0) return [];
  const canonicalDays: CanonicalDay[] = items.map((item, idx) => ({
    day_number: item.day_number ?? idx + 1,
    destination: item.destination ?? null,
    destination_ref: item.destination_ref ?? null,
    overnight: item.overnight ?? item.destination ?? null,
    display_date: null,
    summary: item.summary ?? null,
    accommodation_id: item.accommodation_id ?? null,
    accommodation_name: item.accommodation_name ?? null,
    room_type: item.room_type ?? null,
  }));

  const stays = staysReconciler.reconcileStaysFromItinerary(canonicalDays, startDate, prevHotels);
  return staysReconciler.toHotelFacts(stays);
}

/**
 * @deprecated Use staysReconciler.syncItineraryFromStays instead.
 */
export function hydrateDayAccommodationsFromHotels<T extends DayItemWithStayLike>(
  itinerary: T[],
  hotels: HotelFact[],
  startDate: string | null | undefined
): T[] {
  if (!itinerary || itinerary.length === 0) return [];
  if (!hotels || hotels.length === 0) return itinerary;

  const canonicalDays: CanonicalDay[] = itinerary.map((item, idx) => ({
    day_number: item.day_number ?? idx + 1,
    destination: item.destination ?? null,
    destination_ref: item.destination_ref ?? null,
    overnight: item.overnight ?? item.destination ?? null,
    display_date: null,
    summary: item.summary ?? null,
    accommodation_id: item.accommodation_id ?? null,
    accommodation_name: item.accommodation_name ?? null,
    room_type: item.room_type ?? null,
  }));

  const hydrated = staysReconciler.syncItineraryFromStays(canonicalDays, hotels, startDate);
  return itinerary.map((day, idx) => ({
    ...day,
    accommodation_id: hydrated[idx]?.accommodation_id ?? null,
    accommodation_name: hydrated[idx]?.accommodation_name ?? null,
    room_type: hydrated[idx]?.room_type ?? null,
  }));
}

export { staysReconciler, type CanonicalStay };
