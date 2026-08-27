import type { ItineraryDayFact, QuotationFacts } from "../components/quotation-workspace/factsTypes.ts";
import type { CostingWorkbenchResponse } from "./quotationApi.ts";
import { syncHotelsFromItineraryOvernights } from "./prefillEngine.ts";

/**
 * Pure utility function that overlays a costing sheet's picked lines onto
 * QuotationFacts, using 100% 4-Layer Domain Reconcilers (Stays via
 * `prefillEngine.syncHotelsFromItineraryOvernights`) for the actual stay
 * clustering — this module never re-derives that logic (15.4 §3.2).
 *
 * Runs exactly once, at the moment a quotation is generated from a costing
 * sheet (Flow 1). It never re-runs while the quotation is open — that is a
 * deliberately separate, user-triggered "apply again" action left to 15.5.
 */
export function buildFactsFromCostingWorkbench(
  workbench: CostingWorkbenchResponse | null | undefined,
  fallback: QuotationFacts,
): QuotationFacts {
  if (!workbench) return fallback;

  const { items, sheet, summary } = workbench;

  // ---------------------------------------------------------------------------
  // 1. STAYS — patch itinerary days covered by an accommodation line's
  //    [day_number, day_number + qty_time - 1] range, only where the sale
  //    hasn't already set a destination/accommodation for that day. The actual
  //    contiguous-run clustering into service_facts.hotels[] is delegated to
  //    prefillEngine.syncHotelsFromItineraryOvernights below.
  // ---------------------------------------------------------------------------
  const itinerary: ItineraryDayFact[] = fallback.trip_facts.itinerary.map((day) => ({ ...day }));

  for (const line of items) {
    if (line.category !== "accommodation" || !line.product_ref?.property_id || line.day_number === null) continue;
    const destinationName = line.product_ref.destination_name ?? null;
    const nights = Math.max(1, line.qty_time);
    for (let offset = 0; offset < nights; offset += 1) {
      const index = line.day_number - 1 + offset;
      const day = itinerary[index];
      if (!day) continue;
      itinerary[index] = {
        ...day,
        destination: day.destination || destinationName,
        overnight: day.overnight || destinationName,
        accommodation_id: day.accommodation_id || line.product_ref.property_id,
        accommodation_name: day.accommodation_name || line.title,
        room_type: day.room_type || line.subcategory || day.room_type,
      };
    }
  }

  // ---------------------------------------------------------------------------
  // 2. DESTINATIONS — fill blank day destinations from any other line's
  //    productRef, matched by day_number. Never overwrites a destination the
  //    sale already set from the request.
  // ---------------------------------------------------------------------------
  for (const line of items) {
    if (line.category === "accommodation" || !line.product_ref?.destination_name || line.day_number === null) continue;
    const index = line.day_number - 1;
    const day = itinerary[index];
    if (!day || day.destination) continue;
    itinerary[index] = { ...day, destination: line.product_ref.destination_name };
  }

  const withItinerary: QuotationFacts = {
    ...fallback,
    trip_facts: { ...fallback.trip_facts, itinerary },
  };
  const withHotels = syncHotelsFromItineraryOvernights(withItinerary);

  // ---------------------------------------------------------------------------
  // 3. PRICING — sell_total + currency onto options[0]. Per-adult/per-child are
  //    left null so pricingReconciler.inferOptionRatesFromTotal derives them the
  //    moment the sale opens the pricing panel (chốt #9 — one-shot prefill, sale
  //    stays in control from there). Skipped entirely for an empty sheet — there
  //    is no sell total worth prefilling yet.
  // ---------------------------------------------------------------------------
  if (items.length === 0 || summary.sell_total_minor <= 0) {
    return withHotels;
  }

  const existingOption = withHotels.pricing_facts.options[0];
  const pricingOption = {
    id: existingOption?.id ?? "opt-standard",
    label: existingOption?.label ?? "Standard Luxury Option",
    currency: sheet.currency,
    per_traveler_amount_minor: null,
    group_total_amount_minor: summary.sell_total_minor,
    per_adult_amount_minor: null,
    per_child_amount_minor: null,
  };

  return {
    ...withHotels,
    pricing_facts: {
      ...withHotels.pricing_facts,
      options: [pricingOption, ...withHotels.pricing_facts.options.slice(1)],
    },
  };
}
