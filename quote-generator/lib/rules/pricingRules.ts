/**
 * Pure domain rules for commercial pricing, child rate presets, and multi-currency math (TypeScript).
 * Delegates to pricingReconciler.ts (SSOT).
 */

import {
  pricingReconciler,
  SUPPORTED_CURRENCIES,
  type SupportedCurrency,
} from "./pricingReconciler.ts";

export { SUPPORTED_CURRENCIES, type SupportedCurrency };

export const currencyDivisor = pricingReconciler.currencyDivisor;
export const calculateTriPricing = pricingReconciler.calculateOptionTotal;

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

export const inferRatesFromGroupTotal = pricingReconciler.inferOptionRatesFromTotal;
