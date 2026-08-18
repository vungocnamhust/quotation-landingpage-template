/**
 * Pure domain rules for travel dates, duration calculation, and day projection (TypeScript).
 */

export function parseIsoDate(value: string | null | undefined): Date | null {
  if (!value || typeof value !== "string") return null;
  const d = new Date(`${value}T00:00:00.000Z`);
  if (Number.isNaN(d.getTime())) return null;
  return d;
}

export function calculateDuration(
  startDate: string | null | undefined,
  endDate: string | null | undefined
): { durationDays: number | null; durationNights: number | null } {
  if (!startDate || !endDate) {
    return { durationDays: null, durationNights: null };
  }
  const start = parseIsoDate(startDate);
  const end = parseIsoDate(endDate);
  if (!start || !end || end < start) {
    return { durationDays: null, durationNights: null };
  }

  const days = Math.floor((end.getTime() - start.getTime()) / 86_400_000) + 1;
  const nights = Math.max(0, days - 1);
  return { durationDays: days, durationNights: nights };
}

export function dateForItineraryDay(
  startDate: string | null | undefined,
  dayNumber: number | null | undefined
): string | null {
  if (!startDate || !dayNumber || dayNumber < 1) return null;
  const start = parseIsoDate(startDate);
  if (!start) return null;

  const target = new Date(start.getTime() + (dayNumber - 1) * 86_400_000);
  return target.toISOString().split("T")[0];
}

export function formatTravelDatesLabel(
  startDate: string | null | undefined,
  endDate: string | null | undefined,
  fallbackText?: string | null
): string {
  if (!startDate || !endDate) return (fallbackText || "").trim();
  const start = parseIsoDate(startDate);
  const end = parseIsoDate(endDate);
  if (!start || !end || end < start) return (fallbackText || "").trim();

  const options: Intl.DateTimeFormatOptions = { day: "2-digit", month: "short", year: "numeric" };
  return `${start.toLocaleDateString("en-GB", options)} – ${end.toLocaleDateString("en-GB", options)}`;
}
