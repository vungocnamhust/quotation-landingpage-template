import { currencyDivisor } from "./rules/pricingReconciler.ts";

/**
 * Format an integer minor-unit amount for staff-workspace display.
 *
 * The divisor comes from the pricing reconciler (VND → 1, others → 100) so a
 * VND sheet can never render 100× too small again (Plan 16.3 F-09). Display
 * only — domain math stays on integers.
 */
export function formatMinorAmount(amountMinor: number, currency: string): string {
  const divisor = currencyDivisor(currency);
  const major = amountMinor / divisor;
  return `${major.toLocaleString(undefined, {
    maximumFractionDigits: divisor === 1 ? 0 : 2,
  })} ${currency}`;
}
