---
name: quote-generator-prefill-governor
description: Govern prefill, default values, and bidirectional domain reconciliation in quote-generator. Use when adding or modifying form fields, handling default values, calculating trip duration/dates, inferring overnight destinations, computing commercial totals, generating traveller labels, or synchronizing accommodation slots. Enforce the 4-layer Bidirectional Reconciler & Canonical Adapter architecture, Vercel React Best Practices, and multilingual defaults.
---

# Quote Generator Prefill & Domain Reconciler Governor

Govern prefill, default value assignment, and data reconciliation logic across all quotation tabs (`request`, `new quotation`, `fact`, `content`, `design`).

## Architecture & Ownership (The 4-Layer Reconciler Pattern)

Always follow the **4-Layered Architecture** for state mutations, derivations, and invariant reconciliation:

```
┌────────────────────────────────────────────────────────────────────────┐
│ Tầng 4: React UI Layer (QuoteRequestForm, BasicItineraryDayGrid, Facts)│
│ - Calls 1-line Facade Updaters or Headless Reconciler Hooks            │
│ - STRICT: No inline math, day-index arithmetic, or manual date loops   │
├──────────────────────────────────┬─────────────────────────────────────┘
                                   │ Single-pass transformations
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Tầng 3: Orchestrator / Facade Layer (quote-generator/lib/prefillEngine.ts)
│ - Executes atomic state mutations on QuotationFacts / FormStates       │
│ - Prevents cascading re-renders via single-pass updates                │
├──────────────────────────────────┬─────────────────────────────────────┤
│ Tầng 2: Canonical Adapter Layer (quote-generator/lib/rules/*Adapter.ts) │
│ - tripAdapter: bridges QuoteRequestFormState <-> CanonicalTrip <-> Facts│
│ - Zero schema corruption, reusable across all entrypoints              │
├──────────────────────────────────┬─────────────────────────────────────┤
│ Tầng 1: Pure Domain Reconciler Core (lib/rules/*Reconciler.ts & Rules) │
│ - tripReconciler.ts: startDate <-> endDate <-> duration <-> itinerary  │
│ - staysRules.ts: overnight grouping <-> hotel stays <-> checkIn/Out    │
│ - pricingRules.ts: per-person rate <-> group total 2-way inference     │
│ - partyRules.ts: name/pax count <-> party_label & greeting_name        │
└────────────────────────────────────────────────────────────────────────┘
```

## Hard Guardrails

1. **Strictly Use Domain Reconcilers for Closed State Graphs**:
   - For Trip Dates & Itinerary: **`tripReconciler`** enforces:
     $$\text{EndDate} = \text{StartDate} + \text{Length} - 1$$
     $$\text{Duration Days} = \text{Length of Itinerary}$$
     $$\text{Day } i\text{ Date} = \text{StartDate} + (i - 1)\text{ days}$$
   - Any mutation to StartDate, EndDate, or Itinerary Days **MUST** pass through:
     ```ts
     const canonical = tripAdapter.fromQuoteRequest(formState, itineraryDays);
     const updated = tripReconciler.addDay(canonical); // or removeDay, setStartDate, setEndDate
     const synced = tripAdapter.syncToQuoteRequest(updated, formState);
     setFormState(synced.formState);
     setItineraryDays(synced.itineraryDays);
     ```

2. **Never Execute Multi-step Inline State Mutations in Components**:
   - ❌ **BAD**: Calling multiple `setFacts` in sequence inside event handlers or manually calculating `days.length + 1` with `Date.now()`.
   - ✅ **GOOD**: Call atomic facade updaters from `prefillEngine.ts` or `tripReconciler`.

3. **Never Duplicate Derived State in React State**:
   - ❌ **BAD**: Storing dynamic calculations (like duration days/nights, party label badges, calculated pricing totals) in duplicate component state.
   - ✅ **GOOD**: Compute derived values dynamically using pure functions in `lib/rules/*` or memoize with `useMemo`.

4. **Always Multilingual Default Meals**:
   - When initializing new itinerary days, always use `getDefaultMealsForLang(lang)` or `getDefaultMeals(lang)`:
     - `en`: `["Breakfast", "Lunch", "Dinner"]`
     - `vi`: `["Bữa sáng", "Bữa trưa", "Bữa tối"]`
     - `ar`: `["الإفطار", "الغداء", "العشاء"]`

5. **Ensure O(1) Performance for Derivations**:
   - Use `Set` / `Map` for stay segment grouping (`deriveStaySegmentsFromItinerary`) and route destination reference aggregation (`routeDestinationRefsFromItinerary`).

## Available Reconciler & Facade Updaters

- **`tripReconciler`** (`lib/rules/tripReconciler.ts`):
  - `addDay(trip, defaultPayload)`: Pushes endDate and sets projected display_date.
  - `removeDay(trip, index)`: Pulls back endDate and re-indexes all days.
  - `setStartDate(trip, nextStartDate)`: Shifts display_date for all days and shifts endDate.
  - `setEndDate(trip, nextEndDate)`: Resizes itinerary array to match duration.
  - `updateDay(trip, index, patch)`: Smart overnight auto-fill and hotel cascading.
- **`tripAdapter`** (`lib/rules/tripAdapter.ts`):
  - `fromQuoteRequest(formState, days)` & `syncToQuoteRequest(canonical, prev)`
  - `fromQuotationFacts(facts)` & `syncToQuotationFacts(canonical, prev)`
- **`prefillEngine`** (`lib/prefillEngine.ts`):
  - `updateCustomerName(input, name)`
  - `updateCustomerCounts(input, { adults, children })`
  - `updateItineraryDayDestination(input, index, destination, ref)`
  - `syncHotelsFromItineraryOvernights(input)`
  - `patchPricingOptionWithInference(input, index, patch)`

## References

- Contract documentation: `quote-generator/docs/prefill-system-contract.md`
- Reconciler Engine: `quote-generator/lib/rules/tripReconciler.ts`
- Canonical Adapter: `quote-generator/lib/rules/tripAdapter.ts`
- Facade Engine: `quote-generator/lib/prefillEngine.ts`
- Master Guidelines: `AGENTS.md` (Contract 2)`party_label` and `greeting_name` if not manually overridden.
- `updateCustomerCounts(input, { adults, children })`: Single-pass update for adult/children counts, auto-updating `party_label`.
- `updateItineraryDayDestination(input, index, destination, ref)`: Single-pass update for day destination, auto-inferring overnight and rebuilding `routeDestinationRefs`.
- `applyRouteDates(input, startDate, endDate, nextLength)`: Updates travel dates and resizes itinerary while preserving day contents and localized meal defaults.
- `syncHotelsFromItineraryOvernights(input)`: Groups consecutive overnight stays and synchronizes accommodation slots in a single step.
- `patchPricingOptionWithInference(input, index, patch)`: Updates pricing options with automatic 2-way per traveler <-> group total price inference.

## References

- Contract documentation: `quote-generator/docs/prefill-system-contract.md`
- Core Engine: `quote-generator/lib/prefillEngine.ts`
- Domain Rules: `quote-generator/lib/prefillRules.ts`
