import {
  dateForItineraryDay,
  type DestinationRef,
  type HotelFact,
  type ItineraryDayFact,
} from "../components/quotation-workspace/factsTypes";

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
      // Keep existing hotel if user selected an accommodation profile or named a hotel
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
  if (checkIn && tourStartDate && checkIn < tourStartDate) {
    return {
      valid: false,
      code: "BEFORE_START",
      message: `Check-in date (${checkIn}) cannot be before tour start date (${tourStartDate}).`,
    };
  }

  if (checkOut && tourEndDate && checkOut > tourEndDate) {
    return {
      valid: false,
      code: "AFTER_END",
      message: `Check-out date (${checkOut}) cannot be after tour end date (${tourEndDate}).`,
    };
  }

  if (checkIn && checkOut && checkOut < checkIn) {
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
  if (perTravelerAmountMinor === null || perTravelerAmountMinor <= 0 || !adults || adults <= 0) {
    return null;
  }
  return perTravelerAmountMinor * adults;
}

/**
 * Infer per traveler price from group total price and adults count.
 */
export function inferCommercialPerTraveler(
  groupTotalAmountMinor: number | null,
  adults: number | null,
): number | null {
  if (groupTotalAmountMinor === null || groupTotalAmountMinor <= 0 || !adults || adults <= 0) {
    return null;
  }
  return Math.round(groupTotalAmountMinor / adults);
}

/**
 * Infer party label string for travellers.
 */
export function inferPartyLabel(
  customerName: string | null,
  adults: number | null,
  children: number | null,
): string | null {
  const adultCount = adults && adults > 0 ? adults : null;
  const childCount = children && children > 0 ? children : null;

  const counts: string[] = [];
  if (adultCount) counts.push(`${adultCount} Adult${adultCount > 1 ? "s" : ""}`);
  if (childCount) counts.push(`${childCount} Child${childCount > 1 ? "ren" : ""}`);

  const countLabel = counts.join(", ");
  const name = customerName?.trim();

  if (name && countLabel) {
    return `${name} & Party (${countLabel})`;
  }
  if (name) {
    return name;
  }
  if (countLabel) {
    return countLabel;
  }
  return null;
}

/**
 * Infer greeting name string from customer name.
 */
export function inferGreetingName(customerName: string | null): string | null {
  const name = customerName?.trim();
  if (!name) return null;
  if (name.toLowerCase().startsWith("dear ")) return name;
  return `Dear ${name}`;
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
  en: ["Breakfast", "Lunch", "Dinner"],
  vi: ["Bữa sáng", "Bữa trưa", "Bữa tối"],
  ar: ["الإفطار", "الغداء", "العشاء"],
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

