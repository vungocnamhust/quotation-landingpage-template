# Brochure text data inventory

This inventory is the contract for the brochure template. Runtime brochure rendering must consume `PageViewModel` produced by `display/runtimePageBuilder.ts`; `display/pageBuilderFixtures.ts` is test/demo data only and is not a production source.

Classification:

1. `fact-derived`: deterministic from facts, itinerary, stays, pricing, terms, designer, or seller data.
2. `viewmodel`: already represented by the runtime `PageViewModel`.
3. `missing`: cannot be safely inferred and needs a canonical field or editor input.
4. `llm`: narrative copy may be generated only as a reviewed content candidate; it must not silently overwrite canonical document state.

| Section | Text/data-value | Classification | Canonical path / action |
| --- | --- | --- | --- |
| nav | brand name, logo alt, section links | fact-derived + viewmodel | `brandProfile.displayName`; `page.nav.*` |
| nav | PDF Download/action label | missing | `page.nav.actions[].label`; localised UI label is presentation copy |
| nav | language labels and aria labels | viewmodel | `display/labels.ts`; keep outside quotation facts |
| hero | kicker | llm | `narrative.coverKicker` candidate, review then apply |
| hero | title | fact-derived | `trip.title` |
| hero | lede | llm | `trip.lede` candidate, review then apply |
| hero | duration and route metadata | fact-derived | `trip.durationText`, `trip.routeText` |
| hero | begin-journey CTA | viewmodel | `page.hero.primaryCta` |
| hero | footer brand meta | fact-derived | `brandProfile.displayName` |
| letter | chapter/title | llm or missing | `narrative.journeyOverviewTitle`; require reviewed candidate |
| letter | highlight, greeting, intro, body, outro | llm | `narrative.letter*`; candidate-only until Apply |
| letter | signature name/role/contact | fact-derived + viewmodel | designer/seller profile; `page.letter.*` |
| routeMap | title and lead | llm or missing | `route.title`, `route.description`; no generic destination copy fallback |
| routeMap | segment title, city, duration, hotel, description | fact-derived | `route.staySegments[]` |
| routeMap | map mode labels, attribution | viewmodel | `page.routeMap.mapModeOptions[]` |
| itinerary divider | kicker, title, tagline | fact-derived + llm | itinerary title/description; generated narrative requires review |
| itinerary divider | duration, nights, route summary | fact-derived | derived only from itinerary days and route segments |
| itinerary | day label, city, title | fact-derived | day number/segment city/title |
| itinerary | day description, highlights, notes | fact-derived or llm | source facts when present; candidate generation otherwise |
| itinerary | overnight, meals, detail labels | fact-derived + viewmodel | day data + localised labels |
| hotels | section title | viewmodel | `labels.stayPlanning` |
| hotels | city, hotel, room type, date, telephone | fact-derived | `stays.hotels[]` |
| hotels | hotel introduction and room notes | fact-derived or llm | persisted fields; do not invent missing operational facts |
| stays divider | kicker/title/tagline/closing | viewmodel, missing, or llm | labels/title from stays; narrative fields need canonical fields |
| pricing | kicker/title/description and important-note label | design/theme override | `presentation.copyOverrides`; never collected as sales facts or LLM-generated |
| pricing | ordered option label, currency, per-traveler amount and group-total amount | fact-derived | typed `pricing.options[]`; both amounts are explicit minor-unit values |
| pricing | pricing note | fact-derived, optional | `pricing.conditions`; brochure hides the note block when empty |
| inclusions/exclusions | section and panel titles | viewmodel | localised labels / canonical override fields |
| inclusions/exclusions | lead, inclusion items, exclusion items | fact-derived or llm | persisted document arrays; generation requires review |
| paymentTerms | kicker/title/description | llm or missing | `bookingTerms.*`; candidate-only when generated |
| paymentTerms | term labels and bodies | fact-derived or missing | `bookingTerms.items[]`; never infer legal terms |
| paymentTerms | CTA | design/theme override | `presentation.copyOverrides.bookingTerms.cta` or localised label |
| designer | kicker/title/quote | llm or missing | `designer.*`; reviewed candidate only |
| designer | name, subtitle, signature, experience, avatar | fact-derived | designer profile/document |
| designer | WhatsApp/email actions and captions | fact-derived + viewmodel | seller/designer contact fields + localised labels |
| footer | footer text | llm or missing | `narrative.footerText`; require canonical field/review |
| footer | secondary brand meta | fact-derived | `brandProfile.displayName` |

## Editor marker rule

Every text-bearing display atom emits `data-editable="true"` (or a future canonical path in the same attribute). The path inventory above is the mapping source for replacing the generic marker with field-specific paths. Labels that are pure presentation chrome remain viewmodel-owned and are still marked so the editor can override them without changing fact ownership.

## Workflow gate

`facts -> content -> design -> publish` is enforced by the V2 workspace APIs. Facts are saved with `baseRevision`; content generation creates reviewed candidates; Apply updates the canonical document; design writes presentation fields only; publish requires review readiness and the same revision contract.
