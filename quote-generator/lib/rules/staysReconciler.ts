/**
 * Pure domain rules for accommodation stay reconciliation (TypeScript).
 * Guarantees invariant clustering, gap handling (transits/self-booked),
 * night calculation, date shifting, and bidirectional synchronization
 * between daily itinerary items and hotel stays.
 */

import {
  dateForItineraryDay,
  formatDisplayDate,
  parseIsoDate,
} from "./datesRules.ts";
import type { DestinationRef, HotelFact } from "../../components/quotation-workspace/factsTypes.ts";
import type { CanonicalDay, CanonicalTrip } from "./tripReconciler.ts";

export type AccommodationStayStatus =
  | "booked"
  | "self_arranged"
  | "transit_overnight"
  | "no_overnight"
  | "unassigned";

export type CanonicalStay = {
  id?: string;
  accommodation_id: string | null;
  name: string | null;
  destination: string | null;
  destination_ref?: DestinationRef | null;
  room_type: string | null;
  day_start: number; // 1-based day number
  day_end: number;   // 1-based day number (inclusive)
  nights: number;    // day_end - day_start + 1
  check_in: string | null;  // ISO date: startDate + (day_start - 1) days
  check_out: string | null; // ISO date: startDate + day_end days
  intro?: string | null;
  phone?: string | null;
  display_city?: string | null;
  display_date?: string | null;
  hotel_asset?: string | null;
  room_asset?: string | null;
  [key: string]: unknown;
};

export type CanonicalTripWithStays = CanonicalTrip & {
  stays: CanonicalStay[];
};

export type StayCoverageSummary = {
  totalTourDays: number;
  totalTourNights: number;
  bookedNights: number;
  unassignedNights: number;
  gapNights: number; // transits, self-booked, or departure day
  isComplete: boolean;
};

/**
 * Format date range label for stay cards (e.g. "Mon, 09 Nov – Thu, 12 Nov").
 */
export function formatStayDisplayDate(
  checkIn: string | null | undefined,
  checkOut: string | null | undefined,
  lang: string = "en"
): string | null {
  if (!checkIn || !checkOut) return null;
  const inLabel = formatDisplayDate(checkIn, lang);
  const outLabel = formatDisplayDate(checkOut, lang);
  if (!inLabel || !outLabel) return null;
  return `${inLabel} – ${outLabel}`;
}

/**
 * Calculate nights between two ISO dates or default to day range.
 */
export function calculateStayNights(
  checkIn: string | null | undefined,
  checkOut: string | null | undefined,
  fallbackNights = 1
): number {
  if (!checkIn || !checkOut) return fallbackNights;
  const cin = parseIsoDate(checkIn);
  const cout = parseIsoDate(checkOut);
  if (!cin || !cout || cout < cin) return fallbackNights;
  const diffDays = Math.floor((cout.getTime() - cin.getTime()) / 86_400_000);
  return Math.max(1, diffDays);
}

/**
 * Find matching previous hotel metadata to preserve custom assets, intro, phone, etc.
 */
function findMatchingMetadata(
  accId: string | null,
  accName: string | null,
  destination: string | null,
  prevHotels: Array<Partial<HotelFact> | Partial<CanonicalStay>> = []
): Partial<HotelFact> | null {
  if (!prevHotels.length) return null;

  // 1. Match by accommodation_id
  if (accId) {
    const byId = prevHotels.find((h) => h.accommodation_id === accId);
    if (byId) return byId;
  }

  // 2. Match by exact hotel name and destination
  if (accName) {
    const byNameAndDest = prevHotels.find(
      (h) =>
        h.name &&
        h.name.toLowerCase() === accName.toLowerCase() &&
        h.destination &&
        destination &&
        h.destination.toLowerCase() === destination.toLowerCase()
    );
    if (byNameAndDest) return byNameAndDest;

    const byName = prevHotels.find(
      (h) => h.name && h.name.toLowerCase() === accName.toLowerCase()
    );
    if (byName) return byName;
  }

  // 3. Fallback: match by destination
  if (destination) {
    const byDest = prevHotels.find(
      (h) => h.destination && h.destination.toLowerCase() === destination.toLowerCase()
    );
    if (byDest) return byDest;
  }

  return null;
}

export const staysReconciler = {
  /**
   * Pure clustering: Group contiguous itinerary days that share the same hotel into discrete CanonicalStay objects.
   *
   * Business Rules:
   * 1. Only days with a valid accommodation_id (or accommodation_name) produce stays.
   * 2. Contiguous days sharing the same accommodation_id, accommodation_name, room_type and destination
   *    are merged into a single Stay segment.
   * 3. Days without a hotel (transits, self-arranged, or departure day) close the active stay, creating clean gaps.
   * 4. check_in is set to the start date of the first day in the stay cluster.
   * 5. check_out is set to the date of the day immediately following the last day in the stay cluster.
   * 6. Preserves custom assets, intro, phone, display_city from prevHotels.
   */
  reconcileStaysFromItinerary(
    itinerary: CanonicalDay[] = [],
    startDate: string | null | undefined = null,
    prevHotels: Array<Partial<HotelFact> | Partial<CanonicalStay>> = []
  ): CanonicalStay[] {
    if (!itinerary || itinerary.length === 0) return [];

    const stays: CanonicalStay[] = [];
    let currentStay: CanonicalStay | null = null;

    for (let idx = 0; idx < itinerary.length; idx++) {
      const day = itinerary[idx];
      const dayNum = day.day_number ?? idx + 1;
      const accId = day.accommodation_id?.trim() || null;
      const accName = day.accommodation_name?.trim() || null;
      const roomType = day.room_type?.trim() || "Standard Room";
      const dest = day.overnight?.trim() || day.destination?.trim() || null;
      const destRef = day.destination_ref ?? null;
      const hasHotel = Boolean(accId || accName);

      if (!hasHotel) {
        // Gap day (overnight transit, self-arranged, or departure day): close previous stay if open
        if (currentStay) {
          currentStay.check_in = dateForItineraryDay(startDate, currentStay.day_start);
          currentStay.check_out = dateForItineraryDay(startDate, currentStay.day_end + 1);
          currentStay.display_date = formatStayDisplayDate(
            currentStay.check_in,
            currentStay.check_out
          );
          stays.push(currentStay);
          currentStay = null;
        }
        continue;
      }

      // Check if day belongs to current active stay
      const isContiguousSameStay =
        currentStay !== null &&
        (currentStay.accommodation_id === accId ||
          (!accId && !currentStay.accommodation_id && currentStay.name === (accName || currentStay.name))) &&
        (currentStay.destination === dest || (!currentStay.destination && !dest));

      if (isContiguousSameStay && currentStay) {
        currentStay.day_end = dayNum;
        currentStay.nights = currentStay.day_end - currentStay.day_start + 1;
        if (destRef && !currentStay.destination_ref) {
          currentStay.destination_ref = destRef;
        }
        continue;
      }

      // Switching to a new hotel: close previous stay
      if (currentStay) {
        currentStay.check_in = dateForItineraryDay(startDate, currentStay.day_start);
        currentStay.check_out = dateForItineraryDay(startDate, currentStay.day_end + 1);
        currentStay.display_date = formatStayDisplayDate(
          currentStay.check_in,
          currentStay.check_out
        );
        stays.push(currentStay);
      }

      // Start new stay segment
      const meta = findMatchingMetadata(accId, accName, dest, prevHotels);
      const stayCheckIn = dateForItineraryDay(startDate, dayNum);
      const stayCheckOut = dateForItineraryDay(startDate, dayNum + 1);

      currentStay = {
        id: `stay_${Date.now()}_${dayNum}`,
        accommodation_id: accId || meta?.accommodation_id || null,
        name: accName || meta?.name || null,
        destination: dest,
        destination_ref: destRef || meta?.destination_ref || null,
        room_type: roomType || meta?.room_type || null,
        day_start: dayNum,
        day_end: dayNum,
        nights: 1,
        check_in: stayCheckIn,
        check_out: stayCheckOut,
        intro: meta?.intro || "Breakfast included.",
        phone: meta?.phone || null,
        display_city: meta?.display_city || dest || null,
        display_date: formatStayDisplayDate(stayCheckIn, stayCheckOut),
        hotel_asset: meta?.hotel_asset || null,
        room_asset: meta?.room_asset || null,
      };
    }

    // Flush final stay if still open
    if (currentStay) {
      currentStay.check_in = dateForItineraryDay(startDate, currentStay.day_start);
      currentStay.check_out = dateForItineraryDay(startDate, currentStay.day_end + 1);
      currentStay.display_date = formatStayDisplayDate(
        currentStay.check_in,
        currentStay.check_out
      );
      stays.push(currentStay);
    }

    return stays;
  },

  /**
   * Reverse synchronization: Update itinerary days from discrete HotelFact or CanonicalStay items.
   */
  syncItineraryFromStays(
    itinerary: CanonicalDay[] = [],
    stays: Array<HotelFact | CanonicalStay> = [],
    startDate: string | null | undefined = null
  ): CanonicalDay[] {
    if (!itinerary || itinerary.length === 0) return [];
    if (!stays || stays.length === 0) {
      return itinerary.map((day) => ({
        ...day,
        accommodation_id: null,
        accommodation_name: null,
        room_type: null,
      }));
    }

    return itinerary.map((day, idx) => {
      const dayNum = day.day_number ?? idx + 1;
      const dayDate = dateForItineraryDay(startDate, dayNum);

      // 1. Try matching stay by day_start <= dayNum <= day_end
      const stayByDayRange = stays.find((s) => {
        const canonical = s as CanonicalStay;
        if (typeof canonical.day_start === "number" && typeof canonical.day_end === "number") {
          return dayNum >= canonical.day_start && dayNum <= canonical.day_end;
        }
        return false;
      });

      if (stayByDayRange) {
        return {
          ...day,
          accommodation_id: stayByDayRange.accommodation_id ?? null,
          accommodation_name: stayByDayRange.name ?? null,
          room_type: stayByDayRange.room_type ?? null,
        };
      }

      // 2. Try matching stay by check_in <= dayDate < check_out
      if (dayDate) {
        const stayByDate = stays.find((s) => {
          if (!s.check_in || !s.check_out) return false;
          return dayDate >= s.check_in && dayDate < s.check_out;
        });

        if (stayByDate) {
          return {
            ...day,
            accommodation_id: stayByDate.accommodation_id ?? null,
            accommodation_name: stayByDate.name ?? null,
            room_type: stayByDate.room_type ?? null,
          };
        }
      }

      // 3. Fallback: match by destination when no date constraints are set
      const stayByDest = stays.find((s) => {
        const canonical = s as CanonicalStay;
        const hasDateBounds = Boolean(s.check_in || s.check_out || canonical.day_start);
        if (hasDateBounds) return false;
        const targetDest = day.overnight || day.destination;
        return (
          s.destination &&
          targetDest &&
          s.destination.trim().toLowerCase() === targetDest.trim().toLowerCase()
        );
      });

      if (stayByDest) {
        return {
          ...day,
          accommodation_id: stayByDest.accommodation_id ?? null,
          accommodation_name: stayByDest.name ?? null,
          room_type: stayByDest.room_type ?? null,
        };
      }

      // 4. If no stay covers this day, reset accommodation fields
      return {
        ...day,
        accommodation_id: null,
        accommodation_name: null,
        room_type: null,
      };
    });
  },

  /**
   * Date shift: Tịnh tiến check_in và check_out của toàn bộ stays khi startDate thay đổi.
   */
  shiftStayDates(
    stays: Array<HotelFact | CanonicalStay> = [],
    nextStartDate: string | null | undefined,
    itinerary: CanonicalDay[] = []
  ): CanonicalStay[] {
    if (!stays || stays.length === 0) return [];

    return stays.map((stay, idx) => {
      const canonical = stay as CanonicalStay;
      let dayStart = canonical.day_start;
      let dayEnd = canonical.day_end;

      // If day_start/day_end missing, infer from itinerary or default index
      if (typeof dayStart !== "number" || typeof dayEnd !== "number") {
        if (itinerary.length > 0 && (stay.accommodation_id || stay.name)) {
          const matchingDays = itinerary.filter(
            (d) =>
              (stay.accommodation_id && d.accommodation_id === stay.accommodation_id) ||
              (stay.name && d.accommodation_name === stay.name)
          );
          if (matchingDays.length > 0) {
            dayStart = matchingDays[0].day_number ?? idx + 1;
            dayEnd = matchingDays[matchingDays.length - 1].day_number ?? idx + 1;
          }
        }
        if (typeof dayStart !== "number") dayStart = idx + 1;
        const stayNights = (stay as CanonicalStay).nights;
        if (typeof dayEnd !== "number") dayEnd = dayStart + (stayNights ? stayNights - 1 : 0);
      }

      const nextCheckIn = dateForItineraryDay(nextStartDate, dayStart);
      const nextCheckOut = dateForItineraryDay(nextStartDate, dayEnd + 1);
      const displayDate = formatStayDisplayDate(nextCheckIn, nextCheckOut);

      return {
        ...canonical,
        day_start: dayStart,
        day_end: dayEnd,
        nights: Math.max(1, dayEnd - dayStart + 1),
        check_in: nextCheckIn,
        check_out: nextCheckOut,
        display_date: displayDate,
      };
    });
  },

  /**
   * Update an individual day accommodation and automatically cascade to contiguous days with same destination.
   */
  updateDayAccommodation(
    itinerary: CanonicalDay[],
    index: number,
    patch: Partial<CanonicalDay>,
    startDate: string | null | undefined,
    prevHotels: Array<Partial<HotelFact> | Partial<CanonicalStay>> = []
  ): { itinerary: CanonicalDay[]; stays: CanonicalStay[]; hotels: HotelFact[] } {
    if (index < 0 || index >= itinerary.length) {
      const currentStays = this.reconcileStaysFromItinerary(itinerary, startDate, prevHotels);
      return { itinerary, stays: currentStays, hotels: this.toHotelFacts(currentStays) };
    }

    const currentDay = itinerary[index];
    const updatedDay: CanonicalDay = {
      ...currentDay,
      ...patch,
    };

    const nextItinerary = [...itinerary];
    nextItinerary[index] = updatedDay;

    // Smart Cascade: If hotel changed, cascade to contiguous subsequent days with same destination
    if (
      (patch.accommodation_id !== undefined || patch.accommodation_name !== undefined || patch.room_type !== undefined) &&
      updatedDay.destination
    ) {
      for (let i = index + 1; i < nextItinerary.length; i++) {
        if (
          nextItinerary[i].destination &&
          nextItinerary[i].destination!.toLowerCase() === updatedDay.destination.toLowerCase()
        ) {
          nextItinerary[i] = {
            ...nextItinerary[i],
            accommodation_id: updatedDay.accommodation_id ?? null,
            accommodation_name: updatedDay.accommodation_name ?? null,
            room_type: updatedDay.room_type ?? null,
          };
        } else {
          break;
        }
      }
    }

    const stays = this.reconcileStaysFromItinerary(nextItinerary, startDate, prevHotels);
    return {
      itinerary: nextItinerary,
      stays,
      hotels: this.toHotelFacts(stays),
    };
  },

  /**
   * Convert CanonicalStay array to standard HotelFact array.
   */
  toHotelFacts(stays: CanonicalStay[] = []): HotelFact[] {
    return stays.map((s) => ({
      accommodation_id: s.accommodation_id ?? null,
      destination: s.destination ?? null,
      destination_ref: s.destination_ref ?? null,
      name: s.name ?? null,
      room_type: s.room_type ?? null,
      check_in: s.check_in ?? null,
      check_out: s.check_out ?? null,
      intro: s.intro ?? "Breakfast included.",
      phone: s.phone ?? null,
      display_city: s.display_city ?? s.destination ?? null,
      display_date: s.display_date ?? null,
      hotel_asset: s.hotel_asset ?? null,
      room_asset: s.room_asset ?? null,
    }));
  },

  /**
   * Calculate coverage statistics for accommodations across the trip duration.
   */
  calculateCoverage(
    itinerary: CanonicalDay[] = [],
    stays: Array<CanonicalStay | HotelFact> = [],
    durationDays: number | null = null
  ): StayCoverageSummary {
    const totalDays = durationDays ?? itinerary.length;
    const totalNights = Math.max(0, totalDays - 1);

    const bookedNights = stays.reduce((sum, s) => {
      if (typeof (s as CanonicalStay).nights === "number") {
        return sum + (s as CanonicalStay).nights;
      }
      return sum + calculateStayNights(s.check_in, s.check_out, 1);
    }, 0);

    const daysWithHotel = itinerary.filter((d) => Boolean(d.accommodation_id || d.accommodation_name)).length;
    const daysWithoutHotel = Math.max(0, totalNights - daysWithHotel);

    return {
      totalTourDays: totalDays,
      totalTourNights: totalNights,
      bookedNights,
      unassignedNights: daysWithoutHotel,
      gapNights: Math.max(0, totalNights - bookedNights),
      isComplete: bookedNights === totalNights,
    };
  },
};
