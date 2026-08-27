/**
 * Pure, display-only domain rules for the Costing Workbench grid (15.4).
 *
 * IMPORTANT — this module never mirrors `core/rules/costing_rules.py`. The
 * server (`core/rules/costing_rules.py` → `services/costing_service.py`) is
 * the sole source of truth for cost/sell totals; every write round-trips a
 * fresh `CostingSummary` and the grid must render that, not a client
 * recomputation. `previewLineSellMinor`/`previewLineCostMinor` here exist
 * ONLY to paint an optimistic number between "user types a value" and
 * "server responds" — `resolveLineDisplayTotals` always prefers the
 * server-confirmed numbers the moment they exist.
 */
import { pricingReconciler as pricingReconcilerCore } from "./pricingReconciler.ts";

export type CostingLineDraft = {
  unitCostMinor: number;
  qtyUnit: number;
  qtyTime: number;
  fxRatePpm?: number | null;
  sellOverrideMinor?: number | null;
  markupRateBps: number;
  roundingIncrementMinor: number;
};

export type CostingGroupRow = {
  id: string;
  dayNumber: number | null;
  category: string;
  costMinor: number;
  sellMinor: number;
};

export type CostingDayGroup = {
  dayNumber: number | null; // null == trip-level bucket
  rows: CostingGroupRow[];
  costMinor: number;
  sellMinor: number;
};

/**
 * Optimistic preview of a line's cost, in the sheet's currency. Never persisted,
 * never authoritative — a stand-in until the server's `cost_minor` arrives.
 */
export function previewLineCostMinor(draft: CostingLineDraft): number {
  const base = draft.unitCostMinor * draft.qtyUnit * draft.qtyTime;
  if (!draft.fxRatePpm) return Math.round(base);
  return Math.round((base * draft.fxRatePpm) / 1_000_000);
}

/**
 * Optimistic preview of a line's sell price. Mirrors the server's rounding
 * *intent* (markup then round up to increment) closely enough for a smooth
 * typing experience, but is explicitly not guaranteed to match the persisted
 * value bit-for-bit — see module doc.
 */
export function previewLineSellMinor(draft: CostingLineDraft, costMinor: number): number {
  if (draft.sellOverrideMinor !== null && draft.sellOverrideMinor !== undefined) {
    return draft.sellOverrideMinor;
  }
  const raw = Math.ceil((costMinor * (10_000 + draft.markupRateBps)) / 10_000);
  if (draft.roundingIncrementMinor <= 0) return raw;
  const remainder = raw % draft.roundingIncrementMinor;
  return remainder === 0 ? raw : raw + (draft.roundingIncrementMinor - remainder);
}

/**
 * Server totals always win. Call this with the server's `cost_minor`/`sell_minor`
 * for a line whenever they're available (i.e. always, once the line exists) —
 * the preview path is only for a not-yet-created draft row.
 */
export function resolveLineDisplayTotals(
  draft: CostingLineDraft,
  serverTotals?: { costMinor: number; sellMinor: number } | null,
): { costMinor: number; sellMinor: number; isPreview: boolean } {
  if (serverTotals) {
    return { costMinor: serverTotals.costMinor, sellMinor: serverTotals.sellMinor, isPreview: false };
  }
  const costMinor = previewLineCostMinor(draft);
  const sellMinor = previewLineSellMinor(draft, costMinor);
  return { costMinor, sellMinor, isPreview: true };
}

/**
 * Groups confirmed rows by day, with a single `null`-keyed trip-level bucket
 * for lines that carry no `day_number` (visa, flights, whole-trip guide, ...).
 * Day buckets are sorted ascending; the trip-level bucket is always last.
 */
export function groupRowsByDay(rows: CostingGroupRow[]): CostingDayGroup[] {
  const byDay = new Map<number | null, CostingGroupRow[]>();
  for (const row of rows) {
    const bucket = byDay.get(row.dayNumber);
    if (bucket) bucket.push(row);
    else byDay.set(row.dayNumber, [row]);
  }

  const dayNumbers = [...byDay.keys()].filter((d): d is number => d !== null).sort((a, b) => a - b);
  const groups: CostingDayGroup[] = dayNumbers.map((dayNumber) => {
    const groupRows = byDay.get(dayNumber) ?? [];
    return {
      dayNumber,
      rows: groupRows,
      costMinor: groupRows.reduce((sum, r) => sum + r.costMinor, 0),
      sellMinor: groupRows.reduce((sum, r) => sum + r.sellMinor, 0),
    };
  });

  const tripLevelRows = byDay.get(null);
  if (tripLevelRows && tripLevelRows.length > 0) {
    groups.push({
      dayNumber: null,
      rows: tripLevelRows,
      costMinor: tripLevelRows.reduce((sum, r) => sum + r.costMinor, 0),
      sellMinor: tripLevelRows.reduce((sum, r) => sum + r.sellMinor, 0),
    });
  }

  return groups;
}

/**
 * Splits a confirmed sell total per adult/child for the handoff-into-facts
 * preview strip. Delegates to `pricingReconciler.inferOptionRatesFromTotal` —
 * this module never re-derives the per-person formula.
 */
export function splitSellTotalPerPerson(
  sellTotalMinor: number,
  adults: number,
  children: number,
  childRatio = 0.75,
): { perAdultMinor: number | null; perChildMinor: number | null } {
  return pricingReconcilerCore.inferOptionRatesFromTotal(sellTotalMinor, adults, children, childRatio);
}

export const costingReconciler = {
  previewLineCostMinor,
  previewLineSellMinor,
  resolveLineDisplayTotals,
  groupRowsByDay,
  splitSellTotalPerPerson,
};
