/**
 * Pure domain rules for Route parsing, formatting, and itinerary derivation (TypeScript).
 * Zero React dependencies, 100% deterministic.
 */

import type { CanonicalDay } from "./tripReconciler.ts";

export type DestinationRef = {
  id: string;
  name: string;
  slug: string;
  country?: string;
  [key: string]: unknown;
};

/**
 * Tokenize raw route text by common delimiters (->, –, —, -, >, &, ,, newline, tab).
 * Example: "Ho Chi Minh -> Mekong Delta -> Da Nang -> Hanoi"
 *   ==> ["Ho Chi Minh", "Mekong Delta", "Da Nang", "Hanoi"]
 */
export function parseRouteTokens(rawText: string | null | undefined): string[] {
  if (!rawText || typeof rawText !== "string") return [];
  const normalized = rawText.trim();
  if (!normalized) return [];

  // Split by common chain separators: ->, –, —, >, &, ,, newlines, tabs
  // Also split by single hyphen if surrounded by spaces or between words
  const tokens = normalized
    .split(/(?:->|–|—|(?:\s+-\s+)|>|&|,|\n|\r|\t)+/)
    .map((token) => token.trim())
    .filter((token) => token.length > 0);

  return tokens;
}

/**
 * Format a list of destination names or DestinationRef objects into a standardized brochure string.
 * Example: ["Hanoi", "Halong Bay", "Hue"] ==> "Hanoi – Halong Bay – Hue"
 */
export function formatRouteString(
  destinations: Array<string | DestinationRef | null | undefined> | null | undefined,
  separator: string = " – "
): string {
  if (!destinations || !Array.isArray(destinations) || destinations.length === 0) {
    return "";
  }

  const names: string[] = [];
  for (const item of destinations) {
    if (!item) continue;
    const name = typeof item === "string" ? item.trim() : item.name?.trim();
    if (name && !names.includes(name)) {
      names.push(name);
    }
  }

  return names.join(separator);
}

export type DerivedRouteMetadata = {
  arrivalCity: string | null;
  departureCity: string | null;
  destinations: string[];
  destinationRefs: DestinationRef[];
  displayRouteText: string | null;
};

/**
 * Automatically derive route metadata (arrival city, departure city, destinations list, display route text)
 * from an itinerary list.
 */
export function deriveRouteFromItinerary(
  itinerary: CanonicalDay[] | null | undefined
): DerivedRouteMetadata {
  if (!itinerary || !Array.isArray(itinerary) || itinerary.length === 0) {
    return {
      arrivalCity: null,
      departureCity: null,
      destinations: [],
      destinationRefs: [],
      displayRouteText: null,
    };
  }

  const validDays = itinerary.filter(
    (day) => Boolean(day.destination?.trim()) || Boolean(day.overnight?.trim())
  );

  if (validDays.length === 0) {
    return {
      arrivalCity: null,
      departureCity: null,
      destinations: [],
      destinationRefs: [],
      displayRouteText: null,
    };
  }

  const firstDay = validDays[0];
  const lastDay = validDays[validDays.length - 1];

  const arrivalCity = firstDay.destination?.trim() || firstDay.overnight?.trim() || null;
  const departureCity = lastDay.destination?.trim() || lastDay.overnight?.trim() || null;

  const destinations: string[] = [];
  const destinationRefs: DestinationRef[] = [];
  const seenNames = new Set<string>();

  for (const day of validDays) {
    const name = day.destination?.trim() || day.overnight?.trim();
    if (!name) continue;

    const lower = name.toLowerCase();
    if (!seenNames.has(lower)) {
      seenNames.add(lower);
      destinations.push(name);

      if (day.destination_ref && day.destination_ref.id) {
        destinationRefs.push({
          id: day.destination_ref.id,
          name: day.destination_ref.name || name,
          slug: day.destination_ref.slug || lower.replace(/\s+/g, "-"),
        });
      } else {
        destinationRefs.push({
          id: `dst_${lower.replace(/[^a-z0-9]/g, "_")}`,
          name: name,
          slug: lower.replace(/\s+/g, "-"),
        });
      }
    }
  }

  const displayRouteText = formatRouteString(destinations);

  return {
    arrivalCity,
    departureCity,
    destinations,
    destinationRefs,
    displayRouteText: displayRouteText || null,
  };
}
