# Prefill & Bidirectional Reconciler System Contract

## Overview

This contract governs the data-reconciliation, prefill, default value assignment, and data-derivation architecture for the `quote-generator` application across all workspace stages (`request`, `new quotation`, `fact`, `content`, `design`).

---

## 1. Architectural Layers (4-Layer Bidirectional Reconciler)

```
┌────────────────────────────────────────────────────────────────────────┐
│ Layer 4: React UI Layer (QuoteRequestForm, BasicItineraryDayGrid, Facts)│
│ - Calls 1-line Facade Updaters or Headless Reconciler Hooks            │
│ - STRICT: No inline math, day-index arithmetic, or manual date loops   │
├──────────────────────────────────┬─────────────────────────────────────┘
                                   │ Single-pass transformations
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Layer 3: Orchestrator / Facade Layer (quote-generator/lib/prefillEngine.ts)
│ - Executes atomic state mutations on QuotationFacts / FormStates       │
│ - Prevents cascading re-renders via single-pass updates                │
├──────────────────────────────────┬─────────────────────────────────────┤
│ Layer 2: Canonical Adapter Layer (quote-generator/lib/rules/*Adapter.ts) │
│ - tripAdapter: bridges QuoteRequestFormState <-> CanonicalTrip <-> Facts│
│ - Zero schema corruption, reusable across all entrypoints              │
├──────────────────────────────────┬─────────────────────────────────────┤
│ Layer 1: Pure Domain Reconciler Core (lib/rules/*Reconciler.ts & Rules) │
│ - tripReconciler.ts: startDate <-> endDate <-> duration <-> itinerary  │
│ - staysRules.ts: overnight grouping <-> hotel stays <-> checkIn/Out    │
│ - pricingRules.ts: per-person rate <-> group total 2-way inference     │
│ - partyRules.ts: name/pax count <-> party_label & greeting_name        │
└────────────────────────────────────────────────────────────────────────┘
```

### Layer 1: Pure Domain Reconcilers & Rules (`quote-generator/lib/rules/`)
- **Responsibility**: Pure domain calculation and invariant reconciliation without side-effects.
- **Core Modules**:
  - `tripReconciler.ts`: Pure state transition engine for temporal trip invariants (`addDay`, `removeDay`, `setStartDate`, `setEndDate`, `updateDay`).
  - `staysRules.ts`: Derives stay segments and synchronizes accommodation facts based on overnight locations.
  - `pricingRules.ts`: 2-way commercial price inference between per-traveler rate and group total.
  - `partyRules.ts`: Infers party labels and greetings from guest counts and customer names.
  - `datesRules.ts`: ISO date manipulation, validation, and localized display formatting.

### Layer 2: Canonical Adapters (`quote-generator/lib/rules/*Adapter.ts`)
- **Responsibility**: Translates diverse schema shapes (`QuoteRequestFormState`, `QuotationFacts`, API DTOs) into unified Canonical representations (`CanonicalTrip`) and syncs back.
- **Exports**:
  - `tripAdapter.fromQuoteRequest(formState, days)`
  - `tripAdapter.syncToQuoteRequest(canonical, prev)`
  - `tripAdapter.fromQuotationFacts(facts)`
  - `tripAdapter.syncToQuotationFacts(canonical, prev)`

### Layer 3: Orchestrator / Facade (`quote-generator/lib/prefillEngine.ts`)
- **Responsibility**: Single-pass state transformation functions operating on `QuotationFacts` objects for React UI components.
- **Exports**:
  - `createItineraryDayWithDefaults({ index, startDate, lang })`
  - `updateCustomerName(input, name)`
  - `updateCustomerCounts(input, { adults, children })`
  - `updateItineraryDayDestination(input, index, destination, ref)`
  - `syncHotelsFromItineraryOvernights(input)`
  - `patchPricingOptionWithInference(input, index, patch)`

### Layer 4: Data Contracts & UI Presentation
- **Responsibility**: TypeScript interfaces (`CanonicalTrip`, `QuotationFacts`, `ItineraryDayFact`, `HotelFact`, `PricingOptionFact`) and UI components (`BasicItineraryDayGrid`, `FactTripSection`).

---

## 2. Temporal Trip Closed Graph Invariants

When any one of the 4 temporal elements changes, the remaining 3 are automatically reconciled:

$$\text{EndDate} = \text{StartDate} + (\text{Length} - 1)$$
$$\text{Duration Days} = \text{Length of Itinerary}$$
$$\text{Day } i\text{ Date} = \text{StartDate} + (i - 1)\text{ days}$$

```ts
// Canonical Trip Shape
export type CanonicalTrip = {
  startDate: string | null;
  endDate: string | null;
  durationDays: number | null;
  durationNights: number | null;
  itinerary: CanonicalDay[];
  lang?: string | null;
};
```

---

## 3. Vercel React Best Practices Enforcement

- **`rerender-functional-setstate`**: Always pass pure updaters to `setFacts` or `onChange`:
  ```ts
  // Correct single-pass update:
  onChange((current) => updateCustomerName(current, value));
  ```
- **`rerender-derived-state`**: Never store dynamic calculations (e.g. `duration_days`, `party_label` badges) in duplicate component state.
- **`js-set-map-lookups`**: Use `Set` / `Map` for O(1) collection lookups in stay segment derivation and route ref extraction.

---

## 4. Multilingual Default Values

| Language Code (`lang`) | Default Meals (`getDefaultMealsForLang` / `getDefaultMeals`) |
| :--- | :--- |
| `en` (English) | `["Breakfast", "Lunch", "Dinner"]` |
| `vi` (Vietnamese) | `["Bữa sáng", "Bữa trưa", "Bữa tối"]` |
| `ar` (Arabic) | `["الإفطار", "الغداء", "العشاء"]` |

---

## 5. Quality Gate Audit Checklist

Before declaring any prefill, reconciler, or form change complete:
1. `cd quote-generator && npm run lint` must pass with 0 errors.
2. `cd quote-generator && npm run build` must compile clean TypeScript with 0 errors.
3. Unit tests in `quote-generator/lib/__tests__/*.test.ts` must pass 100%.
4. `python -m pytest tests` must pass 100%.
