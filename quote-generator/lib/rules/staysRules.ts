/**
 * Pure domain rules for accommodation stay consolidation (TypeScript).
 */

import type { HotelFact, DestinationRef } from "../../components/quotation-workspace/factsTypes";
import { dateForItineraryDay } from "./datesRules";

export type DayItemWithStayLike = {
  day_number?: number | null;
  destination?: string | null;
  destination_ref?: DestinationRef | null;
  accommodation_id?: string | null;
  accommodation_name?: string | null;
  room_type?: string | null;
  summary?: string | null;
};

export function consolidateStaysFromDayItems(
  items: DayItemWithStayLike[],
  startDate: string | null | undefined
): HotelFact[] {
  if (!items || items.length === 0) return [];

  const hotels: HotelFact[] = [];
  let currentStay: HotelFact | null = null;
  let stayStartDay = 1;
  let stayEndDay = 1;

  for (let idx = 0; idx < items.length; idx++) {
    const day = items[idx];
    const dayNum = day.day_number ?? idx + 1;
    const accId = day.accommodation_id;
    const accName = day.accommodation_name;
    const roomType = day.room_type || "Standard Room";
    const dest = day.destination ?? null;

    if (!accId && !accName) {
      if (currentStay) {
        currentStay.check_in = dateForItineraryDay(startDate, stayStartDay);
        currentStay.check_out = dateForItineraryDay(startDate, stayEndDay + 1);
        hotels.push(currentStay);
        currentStay = null;
      }
      continue;
    }

    if (
      currentStay !== null &&
      currentStay.accommodation_id === accId &&
      currentStay.room_type === roomType
    ) {
      stayEndDay = dayNum;
      continue;
    }

    if (currentStay) {
      currentStay.check_in = dateForItineraryDay(startDate, stayStartDay);
      currentStay.check_out = dateForItineraryDay(startDate, stayEndDay + 1);
      hotels.push(currentStay);
    }

    stayStartDay = dayNum;
    stayEndDay = dayNum;
    currentStay = {
      accommodation_id: accId ?? null,
      destination: dest,
      destination_ref: day.destination_ref ?? null,
      name: accName || "Hotel",
      room_type: roomType,
      check_in: null,
      check_out: null,
      intro: "Breakfast included.",
      phone: null,
      display_city: dest,
      display_date: null,
      hotel_asset: null,
      room_asset: null,
    };
  }

  if (currentStay) {
    currentStay.check_in = dateForItineraryDay(startDate, stayStartDay);
    currentStay.check_out = dateForItineraryDay(startDate, stayEndDay + 1);
    hotels.push(currentStay);
  }

  return hotels;
}

export function hydrateDayAccommodationsFromHotels<T extends DayItemWithStayLike>(
  itinerary: T[],
  hotels: HotelFact[],
  startDate: string | null | undefined
): T[] {
  if (!itinerary || itinerary.length === 0) return [];
  if (!hotels || hotels.length === 0) return itinerary;

  return itinerary.map((day, idx) => {
    if (day.accommodation_id || day.accommodation_name) {
      return day;
    }
    const dayNum = day.day_number ?? idx + 1;
    const dayDate = dateForItineraryDay(startDate, dayNum);

    // 1. Try matching hotel by check_in <= dayDate < check_out
    if (dayDate) {
      const matchingHotel = hotels.find((h) => {
        if (!h.check_in || !h.check_out) return false;
        return dayDate >= h.check_in && dayDate < h.check_out;
      });
      if (matchingHotel) {
        return {
          ...day,
          accommodation_id: matchingHotel.accommodation_id,
          accommodation_name: matchingHotel.name,
          room_type: matchingHotel.room_type,
        };
      }
    }

    // 2. Fallback: match by destination
    const destMatchingHotel = hotels.find(
      (h) => h.destination && day.destination && h.destination.toLowerCase() === day.destination.toLowerCase()
    );
    if (destMatchingHotel) {
      return {
        ...day,
        accommodation_id: destMatchingHotel.accommodation_id,
        accommodation_name: destMatchingHotel.name,
        room_type: destMatchingHotel.room_type,
      };
    }

    return day;
  });
}
