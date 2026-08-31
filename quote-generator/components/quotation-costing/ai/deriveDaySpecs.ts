import type { DraftDaySpec, ServiceLineProfile } from "../types.ts";

/**
 * Fallback day-spec source for the AI Drafter (15.7 §1.6) when the host view doesn't
 * already have the full itinerary loaded. The Draft endpoint requires the caller to
 * supply `days: [{dayNumber, destinationId, serviceDate}]` on every call — the backend
 * deliberately does not reach into the facts/itinerary pipeline to rebuild it
 * (routers/v2/ai_drafter.py, schemas/v2/ai_drafter.py `DraftDaySpecSchema`).
 *
 * This derives one day spec per distinct `day_number` already present among the sheet's
 * existing service lines, anchored on `product_ref.destination_id`. A day with no lines
 * yet, or whose lines carry no destination_id (manual/non-catalog lines), cannot be
 * derived this way. Prefer passing an explicit `days` prop into `CostingWorkbench` from a
 * view that already has the itinerary loaded (e.g. the quotation's `itinerary_days` facts)
 * — this fallback only covers "draft more services onto a day the sheet already touched".
 */
export function deriveDaySpecsFromLines(items: ServiceLineProfile[]): DraftDaySpec[] {
  const byDay = new Map<number, DraftDaySpec>();
  for (const line of items) {
    if (line.day_number == null || !line.service_date) continue;
    if (byDay.has(line.day_number)) continue;
    const destinationId = line.product_ref?.destination_id;
    if (!destinationId) continue;
    byDay.set(line.day_number, {
      dayNumber: line.day_number,
      destinationId,
      serviceDate: line.service_date,
    });
  }
  return Array.from(byDay.values()).sort((a, b) => a.dayNumber - b.dayNumber);
}

export default deriveDaySpecsFromLines;
