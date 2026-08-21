/**
 * PDF A4 Pagination and Chunking Pure Domain Rules
 * 0 React dependencies, 100% deterministic and unit-testable.
 */

/**
 * Splits itinerary days into chunks of 2 days per A4 page.
 */
export function chunkItineraryDaysForPdf<T>(days: T[]): T[][] {
  if (!Array.isArray(days) || days.length === 0) return [];
  const chunks: T[][] = [];
  for (let i = 0; i < days.length; i += 2) {
    chunks.push(days.slice(i, i + 2));
  }
  return chunks;
}

/**
 * Splits selected hotels into pages according to A4 layout constraints:
 * - 1 to 4 hotels: 1 page.
 * - 5 hotels: 3 hotels on page 1, 2 hotels on page 2 (avoids isolated single hotel on page 2).
 * - 6 hotels: 3 on page 1, 3 on page 2.
 * - 7 hotels: 4 on page 1, 3 on page 2.
 * - 8 hotels: 4 on page 1, 4 on page 2.
 * - n > 8: chunks of 3 or 4, resolving 5-remainder into 3 + 2.
 */
export function chunkHotelsForPdf<T>(hotels: T[]): T[][] {
  if (!Array.isArray(hotels) || hotels.length === 0) return [[]];
  const n = hotels.length;
  if (n <= 4) return [hotels];
  if (n === 5) return [hotels.slice(0, 3), hotels.slice(3, 5)];
  if (n === 6) return [hotels.slice(0, 3), hotels.slice(3, 6)];
  if (n === 7) return [hotels.slice(0, 4), hotels.slice(4, 7)];
  if (n === 8) return [hotels.slice(0, 4), hotels.slice(4, 8)];

  const chunks: T[][] = [];
  let i = 0;
  while (i < n) {
    const remaining = n - i;
    if (remaining === 5) {
      chunks.push(hotels.slice(i, i + 3));
      chunks.push(hotels.slice(i + 3, i + 5));
      break;
    }
    const chunkSize = remaining <= 4 ? remaining : 3;
    chunks.push(hotels.slice(i, i + chunkSize));
    i += chunkSize;
  }
  return chunks;
}
