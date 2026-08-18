/**
 * Pure domain rules for commercial pricing, child rate presets, and multi-currency math (TypeScript).
 */

export const SUPPORTED_CURRENCIES = ["USD", "EUR", "GBP", "AUD", "VND"] as const;
export type SupportedCurrency = (typeof SUPPORTED_CURRENCIES)[number];

export function currencyDivisor(currency: string | null | undefined): number {
  return (currency || "").toUpperCase() === "VND" ? 1 : 100;
}

export function calculateTriPricing(
  perAdultMinor: number | null | undefined,
  perChildMinor: number | null | undefined,
  adults: number = 2,
  children: number = 0
): number | null {
  const safeAdults = Math.max(0, adults);
  const safeKids = Math.max(0, children);

  if (perAdultMinor === null || perAdultMinor === undefined || perAdultMinor <= 0) {
    return null;
  }

  const adultSubtotal = safeAdults * perAdultMinor;
  const childSubtotal =
    safeKids * (perChildMinor !== null && perChildMinor !== undefined && perChildMinor >= 0 ? perChildMinor : 0);

  return adultSubtotal + childSubtotal;
}

export function applyChildPresetRatio(
  perAdultMinor: number | null | undefined,
  ratio: number
): number | null {
  if (perAdultMinor === null || perAdultMinor === undefined || perAdultMinor <= 0) {
    return null;
  }
  if (ratio <= 0) return 0;
  return Math.round(perAdultMinor * ratio);
}

export function inferRatesFromGroupTotal(
  groupTotalMinor: number | null | undefined,
  adults: number = 2,
  children: number = 0,
  childRatio: number = 0.75
): { perAdultMinor: number | null; perChildMinor: number | null } {
  if (groupTotalMinor === null || groupTotalMinor === undefined || groupTotalMinor <= 0) {
    return { perAdultMinor: null, perChildMinor: null };
  }

  const safeAdults = Math.max(1, adults);
  const safeKids = Math.max(0, children);

  const weightedUnits = safeAdults + safeKids * childRatio;
  if (weightedUnits <= 0) {
    return { perAdultMinor: null, perChildMinor: null };
  }

  const perAdult = Math.round(groupTotalMinor / weightedUnits);
  const perChild = safeKids > 0 ? Math.round(perAdult * childRatio) : null;

  return { perAdultMinor: perAdult, perChildMinor: perChild };
}
