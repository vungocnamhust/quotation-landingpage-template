---
name: quote-generator-prefill-governor
description: Govern prefill, default values, and data derivation in quote-generator. Use when adding or modifying form fields, handling default values, calculating trip duration/dates, inferring overnight destinations, computing commercial totals, generating traveller labels, or synchronizing accommodation slots. Enforce the 3-layered prefill architecture, Vercel React Best Practices, and multilingual defaults.
---

# Quote Generator Prefill & Data Derivation Governor

Govern prefill, default value assignment, and data derivation logic across all quotation tabs (`new quotation`, `fact`, `content`, `design`).

## Architecture & Ownership

Always follow the **3-Layered Architecture** for state mutation and data derivation:

```
┌────────────────────────────────────────────────────────────────────────┐
│  React UI Layer (QuotationIntakeForm, FactsForm, ContentStudioClient) │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ Calls Single-pass Updaters
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Layer 3: Orchestrator / Facade (quote-generator/lib/prefillEngine.ts) │
│  - Executes Single-pass State Transformations on QuotationFacts        │
│  - Prevents cascading re-renders via atomic updates                    │
└──────────────────┬──────────────────────────────────────┬──────────────┘
                   │ Reuses Pure Rules                    │ Uses Contracts
                   ▼                                      ▼
┌──────────────────────────────────────┐  ┌──────────────────────────────┐
│ Layer 2: Business & Inference Rules  │  │ Layer 1: Data Contracts      │
│ (lib/prefillRules.ts - ENRICHED)     │  │ (components/factsTypes.ts)   │
│ - inferOvernightDestination()        │  │ - QuotationFacts Types       │
│ - deriveStaySegmentsFromItinerary()  │  │ - ensureFactsDefaults()      │
│ - syncHotelsFromStaySegments()       │  │ - createBrochureFacts()      │
│ - inferCommercialTotal/PerTraveler() │  │ - BROCHURE_DEFAULT_*         │
│ - inferPartyLabel / inferGreeting()  │  │ - serializeFactsForApi()     │
│ - getDefaultMealsForLang()           │  │                              │
└──────────────────────────────────────┘  └──────────────────────────────┘
```

## Hard Guardrails

1. **Never Execute Multi-step Inline State Mutations in Components**:
   - ❌ **BAD**: Calling multiple `patchFacts` or `setFacts` in sequence inside event handlers (e.g. updating `customer_name`, then `party_label`, then `greeting_name`).
   - ✅ **GOOD**: Call atomic facade updaters from `prefillEngine.ts`: `setFacts(current => updateCustomerName(current, name))`.

2. **Never Duplicate Derived State in React State**:
   - ❌ **BAD**: Saving dynamic calculations (like duration days/nights, party label badges, calculated pricing totals) into duplicate component state.
   - ✅ **GOOD**: Compute derived values dynamically using pure functions in `prefillRules.ts` or memoize with `useMemo`.

3. **Always Multilingual Default Meals**:
   - When initializing new itinerary days, always use `getDefaultMealsForLang(lang)`:
     - `en`: `["Breakfast", "Lunch", "Dinner"]`
     - `vi`: `["Bữa sáng", "Bữa trưa", "Bữa tối"]`
     - `ar`: `["الإفطار", "الغداء", "العشاء"]`

4. **Ensure O(1) Performance for Derivations**:
   - Use `Set` / `Map` for stay segment grouping (`deriveStaySegmentsFromItinerary`) and route destination reference aggregation (`routeDestinationRefsFromItinerary`).

## Available Facade Updaters (`lib/prefillEngine.ts`)

- `createItineraryDayWithDefaults({ index, startDate, lang })`: Creates an itinerary day initialized with ISO display date and localized default meals.
- `updateCustomerName(input, name)`: Single-pass update for customer name, auto-updating `party_label` and `greeting_name` if not manually overridden.
- `updateCustomerCounts(input, { adults, children })`: Single-pass update for adult/children counts, auto-updating `party_label`.
- `updateItineraryDayDestination(input, index, destination, ref)`: Single-pass update for day destination, auto-inferring overnight and rebuilding `routeDestinationRefs`.
- `applyRouteDates(input, startDate, endDate, nextLength)`: Updates travel dates and resizes itinerary while preserving day contents and localized meal defaults.
- `syncHotelsFromItineraryOvernights(input)`: Groups consecutive overnight stays and synchronizes accommodation slots in a single step.
- `patchPricingOptionWithInference(input, index, patch)`: Updates pricing options with automatic 2-way per traveler <-> group total price inference.

## References

- Contract documentation: `quote-generator/docs/prefill-system-contract.md`
- Core Engine: `quote-generator/lib/prefillEngine.ts`
- Domain Rules: `quote-generator/lib/prefillRules.ts`
