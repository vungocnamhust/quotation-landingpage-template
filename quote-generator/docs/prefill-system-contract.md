# Prefill & Data Derivation System Contract

## Overview

This contract governs the prefill, default value assignment, and data-derivation architecture for the `quote-generator` application across all workspace tabs (`new quotation`, `fact`, `content`, `design`).

---

## 1. Architectural Layers

### Layer 1: Data Contracts (`quote-generator/components/quotation-workspace/factsTypes.ts`)
- **Responsibility**: TypeScript interfaces (`QuotationFacts`, `ItineraryDayFact`, `HotelFact`, `PricingOptionFact`), API serialization (`serializeFactsForApi`), and defensive schema defaults (`ensureFactsDefaults`, `createBrochureFacts`).
- **Policy Defaults**: `BROCHURE_DEFAULT_INCLUSIONS`, `BROCHURE_DEFAULT_EXCLUSIONS`, `BROCHURE_DEFAULT_BOOKING_TERMS`, `BROCHURE_DEFAULT_FINALIZATION`.

### Layer 2: Business & Inference Rules (`quote-generator/lib/prefillRules.ts`)
- **Responsibility**: Pure domain calculation and inference algorithms without side-effects.
- **Exports**:
  - `getDefaultMealsForLang(lang)`: Multilingual default meal lists (`en`, `vi`, `ar`).
  - `inferOvernightDestination(destination, currentOvernight)`: Inters overnight destination when destination is set.
  - `deriveStaySegmentsFromItinerary(itinerary, startDate, endDate)`: Groups consecutive days by overnight location into stay segments.
  - `syncHotelsFromStaySegments(currentHotels, segments)`: Synchronizes accommodation facts while preserving user-selected hotel profiles.
  - `validateHotelDates(checkIn, checkOut, startDate, endDate)`: Validates stay bounds against tour start/end dates.
  - `inferCommercialTotal(perTraveler, adults)` & `inferCommercialPerTraveler(groupTotal, adults)`: 2-way commercial price inference.
  - `inferPartyLabel(customerName, adults, children)`: Infers party label string (e.g., `"John Doe & Party (2 Adults, 1 Child)"`).
  - `inferGreetingName(customerName)`: Infers greeting name with `"Dear "` prefix.
  - `inferDefaultCurrency(brandId, market)`: Infers default currency based on customer market region.

### Layer 3: Orchestrator / Facade (`quote-generator/lib/prefillEngine.ts`)
- **Responsibility**: Single-pass state transformation functions operating on `QuotationFacts` objects for React UI components.
- **Exports**:
  - `createItineraryDayWithDefaults({ index, startDate, lang })`
  - `updateCustomerName(input, name)`
  - `updateCustomerCounts(input, { adults, children })`
  - `updateItineraryDayDestination(input, index, destination, ref)`
  - `applyRouteDates(input, startDate, endDate, nextLength)`
  - `syncHotelsFromItineraryOvernights(input)`
  - `patchPricingOptionWithInference(input, index, patch)`

---

## 2. Vercel React Best Practices Enforcement

- **`rerender-functional-setstate`**: Always pass pure updaters to `setFacts` or `onChange`:
  ```ts
  // Correct single-pass update:
  onChange((current) => updateCustomerName(current, value));
  ```
- **`rerender-derived-state`**: Never store dynamic calculations (e.g. `duration_days`, `party_label` badges) in duplicate component state.
- **`js-set-map-lookups`**: Use `Set` / `Map` for O(1) collection lookups in stay segment derivation and route ref extraction.

---

## 3. Multilingual Default Values

| Language Code (`lang`) | Default Meals (`getDefaultMealsForLang`) |
| :--- | :--- |
| `en` (English) | `["Breakfast", "Lunch", "Dinner"]` |
| `vi` (Vietnamese) | `["Bữa sáng", "Bữa trưa", "Bữa tối"]` |
| `ar` (Arabic) | `["الإفطار", "الغداء", "العشاء"]` |

---

## 4. Quality Gate Audit Checklist

Before declaring any prefill or form change complete:
1. `cd quote-generator && npm run lint` must pass with 0 errors.
2. `cd quote-generator && npm run build` must compile clean TypeScript with 0 errors.
3. `python -m pytest tests` must pass 100%.
