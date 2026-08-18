/**
 * Facade providing clean domain rules and backward-compatible helper signatures.
 * Delegates pure business rules to lib/rules/*.
 */

import {
  type DestinationRef,
  type HotelFact,
  type ItineraryDayFact,
} from "../components/quotation-workspace/factsTypes";
import {
  dateForItineraryDay,
  parseIsoDate,
  isValidIsoDate,
  addDaysToIsoDate,
  formatDisplayDate,
  calculateValidityExpiry,
} from "./rules/datesRules";
import { generatePartyLabel, inferGreetingName as inferGreetingNameRule } from "./rules/partyRules";
import { calculateTriPricing, inferRatesFromGroupTotal } from "./rules/pricingRules";

export {
  isValidIsoDate,
  addDaysToIsoDate,
  formatDisplayDate,
  calculateValidityExpiry,
};



export type StaySegment = {
  city: string;
  destinationRef: DestinationRef | null;
  dayStart: number;
  dayEnd: number;
  checkIn: string | null;
  checkOut: string | null;
  nights: number;
  displayDate: string | null;
  displayCity: string | null;
  defaultIntro: string;
};

export type HotelDateValidationResult = {
  valid: boolean;
  code: "BEFORE_START" | "AFTER_END" | "INVALID_RANGE" | null;
  message: string | null;
};

/**
 * Infer the display ISO date for a given day in the tour based on start date and day number.
 */
export function inferDayDate(startDate: string | null, dayNumber: number | null): string | null {
  return dateForItineraryDay(startDate, dayNumber);
}

/**
 * Infer overnight destination when destination is selected. If current overnight is blank,
 * default overnight to destination.
 */
export function inferOvernightDestination(destination: string | null, currentOvernight: string | null): string | null {
  if (!currentOvernight || !currentOvernight.trim()) {
    return destination;
  }
  return currentOvernight;
}

/**
 * Derive stay segments from itinerary by grouping consecutive days with the same overnight location.
 */
export function deriveStaySegmentsFromItinerary(
  itinerary: ItineraryDayFact[],
  startDate: string | null,
  endDate: string | null,
): StaySegment[] {
  if (!itinerary || !itinerary.length) return [];

  const groups: ItineraryDayFact[][] = [];
  for (const day of itinerary) {
    const overnightCity = (day.overnight || day.destination || "").trim();
    if (!overnightCity) continue;

    const previousGroup = groups[groups.length - 1];
    const previousDay = previousGroup ? previousGroup[previousGroup.length - 1] : null;
    const previousCity = previousDay ? (previousDay.overnight || previousDay.destination || "").trim() : "";

    if (previousGroup && previousCity.toLowerCase() === overnightCity.toLowerCase()) {
      previousGroup.push(day);
    } else {
      groups.push([day]);
    }
  }

  return groups.map((group, index) => {
    const firstDay = group[0];
    const lastDay = group[group.length - 1];

    const dayStart = firstDay.day_number ?? (index + 1);
    const dayEnd = lastDay.day_number ?? (index + group.length);
    const nights = Math.max(1, dayEnd - dayStart + 1);

    const city = (lastDay.overnight || lastDay.destination || "").trim();
    const destinationRef = lastDay.destination_ref ?? firstDay.destination_ref ?? null;

    const checkIn = inferDayDate(startDate, dayStart);
    const checkOut = inferDayDate(startDate, dayEnd + 1) || (startDate && endDate && dayEnd === itinerary.length ? endDate : null);

    const displayDate = checkIn && checkOut ? `${checkIn} – ${checkOut}` : null;

    return {
      city,
      destinationRef,
      dayStart,
      dayEnd,
      checkIn,
      checkOut,
      nights,
      displayDate,
      displayCity: city,
      defaultIntro: "Breakfast included.",
    };
  });
}

/**
 * Sync hotel facts from derived stay segments. Preserves existing hotel details where possible.
 */
export function syncHotelsFromStaySegments(
  currentHotels: HotelFact[],
  segments: StaySegment[],
): HotelFact[] {
  if (!segments.length) return currentHotels;

  return segments.map((segment, index) => {
    const existing = currentHotels[index];
    if (existing && existing.name) {
      return {
        ...existing,
        destination: existing.destination || segment.city,
        destination_ref: existing.destination_ref || segment.destinationRef,
        check_in: existing.check_in || segment.checkIn,
        check_out: existing.check_out || segment.checkOut,
        display_city: existing.display_city || segment.displayCity,
        display_date: existing.display_date || segment.displayDate,
        intro: existing.intro || segment.defaultIntro,
      };
    }

    return {
      accommodation_id: null,
      destination: segment.city,
      destination_ref: segment.destinationRef,
      name: null,
      room_type: null,
      check_in: segment.checkIn,
      check_out: segment.checkOut,
      intro: segment.defaultIntro,
      phone: null,
      display_city: segment.displayCity,
      display_date: segment.displayDate,
      hotel_asset: null,
      room_asset: null,
    };
  });
}

/**
 * Validate hotel check-in and check-out dates against tour bounds (start_date and end_date).
 */
export function validateHotelDates(
  checkIn: string | null,
  checkOut: string | null,
  tourStartDate: string | null,
  tourEndDate: string | null,
): HotelDateValidationResult {
  const cin = parseIsoDate(checkIn);
  const cout = parseIsoDate(checkOut);
  const tstart = parseIsoDate(tourStartDate);
  const tend = parseIsoDate(tourEndDate);

  if (cin && tstart && cin < tstart) {
    return {
      valid: false,
      code: "BEFORE_START",
      message: `Check-in date (${checkIn}) cannot be before tour start date (${tourStartDate}).`,
    };
  }

  if (cout && tend && cout > tend) {
    return {
      valid: false,
      code: "AFTER_END",
      message: `Check-out date (${checkOut}) cannot be after tour end date (${tourEndDate}).`,
    };
  }

  if (cin && cout && cout < cin) {
    return {
      valid: false,
      code: "INVALID_RANGE",
      message: `Check-out date (${checkOut}) must be on or after check-in date (${checkIn}).`,
    };
  }

  return { valid: true, code: null, message: null };
}

/**
 * Infer group total price from per traveler price and adults count.
 */
export function inferCommercialTotal(
  perTravelerAmountMinor: number | null,
  adults: number | null,
): number | null {
  return calculateTriPricing(perTravelerAmountMinor, null, adults ?? 2, 0);
}

/**
 * Infer per traveler price from group total price and adults count.
 */
export function inferCommercialPerTraveler(
  groupTotalAmountMinor: number | null,
  adults: number | null,
): number | null {
  const { perAdultMinor } = inferRatesFromGroupTotal(groupTotalAmountMinor, adults ?? 2, 0);
  return perAdultMinor;
}

/**
 * Infer party label string for travellers.
 */
export function inferPartyLabel(
  customerName: string | null,
  adults: number | null,
  children: number | null,
  lang: string = "en"
): string | null {
  const label = generatePartyLabel(adults, children, customerName, lang);
  return label || null;
}

/**
 * Infer greeting name string from customer name.
 */
export function inferGreetingName(customerName: string | null, lang: string = "en"): string | null {
  return inferGreetingNameRule(customerName, lang);
}

/**
 * Infer default currency code based on selected brand or customer market.
 */
export function inferDefaultCurrency(brandId: string | null, market: string | null): string {
  const marketLower = (market || "").toLowerCase();
  if (marketLower.includes("vietnam") || marketLower.includes("vn")) return "VND";
  if (marketLower.includes("europe") || marketLower.includes("eu")) return "EUR";
  if (marketLower.includes("uk") || marketLower.includes("britain")) return "GBP";
  if (marketLower.includes("australia") || marketLower.includes("au")) return "AUD";

  return "USD";
}

export const MULTILINGUAL_DEFAULT_MEALS: Record<"en" | "vi" | "ar", string[]> = {
  en: ["Breakfast"],
  vi: ["Bữa sáng"],
  ar: ["الإفطار"],
};

/**
 * Get localized default meal items based on selected quotation language.
 */
export function getDefaultMealsForLang(lang?: "en" | "vi" | "ar" | null): string[] {
  if (!lang || !MULTILINGUAL_DEFAULT_MEALS[lang]) {
    return [...MULTILINGUAL_DEFAULT_MEALS.en];
  }
  return [...MULTILINGUAL_DEFAULT_MEALS[lang]];
}
