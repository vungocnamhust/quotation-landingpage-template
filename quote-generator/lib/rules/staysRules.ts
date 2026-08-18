/**
 * Pure domain rules for accommodation stay consolidation (TypeScript).
 */

import type { HotelFact } from "../../components/quotation-workspace/factsTypes";
import type { DayWithStayItem } from "../../components/quotation-workspace/DayEmbeddedRouteTable";
import { dateForItineraryDay } from "./datesRules";

export function consolidateStaysFromDayItems(
  items: DayWithStayItem[],
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
    const dest = day.destination;

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
      accommodation_id: accId,
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
