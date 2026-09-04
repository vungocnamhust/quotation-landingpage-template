# Plan: Complete the Design Canvas editable-contract and canonical handoffs

**Generated:** 2026-08-09  
**Complexity:** High

## Outcome

Every text node intentionally exposed by the canonical brochure runtime is one of:

1. locally editable Design copy;
2. selectable and deep-linked to its canonical Content or Facts editor; or
3. explicitly read-only system/derived display copy.

The implementation must not add a second text source for route segments, day labels, travel dates, prices, brand identity, or Travel Designer profile data. The existing public brochure and PDF remain pure consumers of `DisplayDocument`; only the workspace `BoundaryCanvas` turns its markers into interactions.

It also closes the **render-effectiveness** gap: a field shown in an editor is not complete merely because it is persisted. Its canonical `EditableText` must be rendered in the screen brochure and dedicated PDF compositor, and an image's persisted `altText` must reach the actual image element that assistive technology reads.

## Root cause and design decision

`runtimePageBuilder.ts` already produces many `EditableText` values. `BoundaryCanvas` resolves a click only when both conditions hold:

- the renderer preserves that value as `data-editable`; and
- `editable-brochure-contract.json` has a descriptor whose `source` matches that exact path (including wildcard paths).

The current registry is incomplete and `editable_contract_payload()` derives a broad handoff from visual section names. That loses the required destination inside Facts and treats an unknown/system field as though it were Content. The permanent model is a registry-owned, explicit handoff target:

```ts
type Handoff = {
  stage: 'facts' | 'content';
  section: string;             // Content scope or Facts section
  anchor?: string;             // stable editor target, not a display path
  item?: 'day' | 'hotel' | 'pricingOption' | 'bookingTerm';
  indexFromSource?: number;    // resolve wildcard position at click time
};
```

`system` fields are registered with `editMode: 'readonly'` and no handoff. `fact-derived` fields use a handoff to the Fact inputs that derive them, never an independent text control.

### Evidence correction for the group-3 audit

The implementation work must use the actual runtime behavior as the source of truth, rather than preserve an audit claim that the current source contradicts:

- `letterSignOff` and `letterSender` are both exposed by `overview_letter` in `services/content_registry.py`, but `runtimePageBuilder.ts` only renders the latter and currently labels it as `/designer/name`, owner `fact`. This is a real ownership/render bug.
- `BrochureNavBar.tsx` currently reads `viewModel.sectionAriaLabel`; the literal default comes from `runtimePageBuilder.ts` through `labels.brochureSections`, not a navbar hard-code. The required fix is an executable default/override consumption test, not a needless replacement of the navbar API.
- `BrochureNavBar.tsx` also currently chooses `viewModel.brandLogoAlt` before `brandName`. It does not propagate that `EditableText` as `data-editable`, so Design Canvas cannot select the alt field. This is a marker-propagation gap; retain the existing value precedence.
- The runtime already passes `assetAlt(...)` into several image atoms. It nevertheless needs a complete slot-by-slot asset URL/alt coverage test, because a persisted media `altText` is only effective when the exact rendered image receives that matching `TextValue` rather than a string fallback.

The plan therefore treats group 3 as a contract-completion task, not as a broad visual rewrite.

## Scope and non-goals

In scope:

- Complete marker/descriptor coverage for the fields in the audit.
- Preserve canonical source paths through the runtime builder and display atoms/components.
- Make all `overview_letter` Content fields effective in both screen and PDF renderers, including the currently orphaned sign-off and mis-owned sender value.
- Prove Design-owned ARIA/logo-alt and Fact-media-alt values reach their real DOM attributes, not merely a view-model field or persistence record.
- Deep-link from Design Canvas to the correct existing Content Studio scope or Facts form/card, then focus the intended repeated editor item.
- Add a machine-verifiable coverage test and browser verification for desktop, mobile, and PDF marker parity.

Out of scope:

- Making labels in `display/labels.ts` per-quotation editable.
- Adding quote-local text fields for route/day/price/date/brand values that are derived from Facts.
- Changing public brochure or PDF visual layouts, color recipes, typography rules, or introducing a second renderer.
- Replacing the Travel Designer profile ownership model with quote-local contact fields.

## Proposed ownership and handoff matrix

| Runtime source / descriptor family | Owner | Handoff destination | Notes |
|---|---|---|---|
| `/narrative/{journeyOverviewTitle,letterHighlight,letterGreeting,letterIntro,letterBody2,letterOutro,letterSignOff,letterSender}` | Content | `content / overview_letter` | Complete the overview scope, not one descriptor per Content input in the Studio. |
| `/narrative/letterSignOff` | Content | `content / overview_letter` | Render as the letter signature name; never replace it with the Travel Designer profile name once it is present. |
| `/narrative/letterSender` | Content | `content / overview_letter` | Render as the letter signature role/sender line with path and owner `content`; it must not point to `/designer/name`. |
| `/presentation/copyOverrides/a11y.brochureSections` | Design | local Design inspector | `NavViewModel.sectionAriaLabel` is the sole input to the nav landmark. The locale label is only its default strategy. |
| `/presentation/identityOverrides/logoAlt` | Design | local Design inspector | `NavViewModel.brandLogoAlt` is the sole preferred logo image alt; propagate its marker to the actual `<Image>`. |
| `/{assets.hero,assets.itineraryDivider,assets.hotelDivider,designer.image,itinerary.days.*/images/carousel/*,stays.hotels.*/{hotelImage,roomImage}}/altText` | Fact media | Facts media editor | A rendered image must consume the matching canonical media object’s `altText`; fallback copy is allowed only when the canonical alt is empty and must retain the canonical alt path. |
| `/designer/{subtitle,signature,quote,experience}` | Fact | `facts / seller`, anchor to its existing field | Quote Fact fields already exist. |
| `/designer/{name,email,phone,contact}` | Fact-derived profile snapshot | `facts / trip`, anchor `travel-designer` | Clicking changes/inspects the selected designer assignment; do not imply that a quote can edit a shared designer profile. If profile editing is required, add a separate explicit profile-workspace link later. |
| `/stays/roomNotes`, `/stays/hotels/*/{city,name,introduction,hotelDate,tel,roomType}` | Fact | `facts / services`, hotel index/anchor | Repeated hotel index is resolved from the wildcard source. |
| `/pricing/conditions`, `/pricing/options/*/{label,groupTotalAmountMinor,perTravelerAmountMinor}` | Fact | `facts / commercial`, option index/anchor | Amounts remain numeric Fact inputs; the formatted brochure price is never edited directly. |
| `/itinerary/days/*/{dayNumber,labelHighlights,overnight,meals/*,notes/*,segmentCity}` | Fact or fact-derived | `facts / programme`, day index/anchor | Day number/date and segment city are derived/read-only in the Facts UI when appropriate; handoff still lands on the inputs from which they derive. |
| `/route/staySegments/*/{displayName,daysLabel,nightsLabel,hotelName}` | Fact-derived | `facts / programme` or `facts / services` with an explanatory derived-state anchor | No route segment textbox. The click must state the value is derived from itinerary/accommodation Facts. |
| `/content/sections/booking_terms/blocks/*/{label,body}` | Fact | `facts / seller`, booking-term index/anchor | Runtime must preserve the actual block/item index; do not use the flattened display index as a canonical JSON pointer. |
| `/brand/displayName` | Fact-derived | `facts / trip`, anchor `brand` | The Brand selector owns it; no quote-local display-name field. |
| `/labels/{chatWhatsapp,sendEmail,classic,...state labels}` | System | Read-only inspector state | Labels are locale system copy. They must never open Facts or Content and cannot be saved as a presentation override. |

## Sprint 1: Make the contract expressive and safe

**Goal:** Version one explicit descriptor schema that can represent content, fact, fact-derived, and system fields without guessing destinations.

**Demo/validation:** The API `GET /document` returns a descriptor for every audited source, including correct `editMode` and handoff metadata; no system descriptor carries a handoff.

### Task 1.1: Extend the JSON schema and API payload

- **Locations:** `editable-brochure-contract.json`, `editable_brochure_contract.py`, `quote-generator/components/quotation-workspace/useQuotationWorkspace.ts`
- **Work:** Bump the contract version. Add explicit optional `handoff` metadata per descriptor and make `owner` include `fact-derived` and `system`. Derive API fields only from explicit registry metadata; remove the current broad section-to-handoff fallback for new descriptors.
- **Acceptance criteria:** A contract descriptor has one owner, one canonical `source` template, and either a valid handoff or `readonly`. `system` can never result in `handoffStage: 'content'`.
- **Validation:** Add JSON/contract unit tests for unique IDs, valid wildcard template syntax, permitted owner/edit-mode combinations, and no missing required handoff for Content/Fact fields.

### Task 1.2: Declare the audited descriptor families

- **Locations:** `editable-brochure-contract.json`
- **Work:** Add the Content, Fact, Fact-derived, and System descriptor families in the matrix above. Use one wildcard family for repeated day/hotel/price/booking-term fields, with an `item` resolver rather than per-quotation generated JSON entries.
- **Acceptance criteria:** Every source in the audit maps to exactly one descriptor; no duplicate overlapping wildcard template exists.
- **Validation:** Extend `tests/test_editable_brochure_contract.py` with the complete expected source matrix and matching of a representative index for each wildcard family.

## Sprint 2: Correct runtime marker provenance

**Goal:** Every declared source has a marker in the actual rendered canonical `DisplayDocument`, with paths that identify the real canonical origin.

**Demo/validation:** A generated display model contains the expected `EditableText.path/owner/mode` for overview, hotel, pricing, itinerary, route, booking, designer, brand, and labels.

### Task 2.1: Inventory and close builder/renderer gaps

- **Locations:** `quote-generator/display/runtimePageBuilder.ts`, `quote-generator/components/display/atoms.tsx`, `molecules.tsx`, `sections.tsx`, `BrochureNavBar.tsx`, `PdfBrochureDocument.tsx`
- **Work:** Verify each audited field passes through an atom/component that emits `data-editable`, `data-edit-owner`, and `data-edit-mode`. Wrap any raw `textValue(...)` rendering that bypasses `editableProps` without modifying display layout.
- **Acceptance criteria:** Boundary Canvas sees one focusable target for each click-worthy DOM marker; public and PDF markup preserve the same source path when rendering the same value.
- **Validation:** Add a focused render test that traverses rendered markup/model for the source matrix. Keep a separate PDF-marker parity test; PDF does not need Design Canvas interaction.

### Task 2.2: Repair booking-term source provenance

- **Locations:** `quote-generator/display/runtimePageBuilder.ts`, canonical rich-content helper if needed, tests
- **Work:** Replace flattened `blocks/${index}/label|body` paths with paths calculated from the actual canonical block and item indices. Keep the descriptor wildcard aligned with the generated marker. If payment-schedule items have a different shape, declare a distinct family rather than pretending both have one path.
- **Acceptance criteria:** Clicking a displayed booking term resolves the exact seller Fact term that created it, even when paragraph, term-list, and payment-schedule blocks coexist or reorder.
- **Validation:** Unit fixture with multiple blocks and at least two items per block; assert path/descriptor/handoff index agreement.

### Task 2.3: Classify derived and system output

- **Locations:** `runtimePageBuilder.ts`, `editable-brochure-contract.json`, `ContextualInspector.tsx`
- **Work:** Preserve markers for derived values so staff can learn their provenance, but use a read-only/derived inspector message and the appropriate Fact handoff. Add system label descriptors only as read-only targets and never expose a save/handoff action.
- **Acceptance criteria:** Route segment, day label, travel date, brand display name, and system labels cannot be edited as text. The inspector explains the derivation and offers the appropriate real editor only where one exists.
- **Validation:** Contract and component tests assert no `system`/`fact-derived` descriptor can execute a direct save; browser test asserts the derived explanation is visible.

### Task 2.4: Repair the letter, a11y, logo-alt, and media-alt render contracts

- **Locations:** `quote-generator/display/runtimePageBuilder.ts`, `quote-generator/display/types.ts`, `quote-generator/components/display/sections.tsx`, `quote-generator/components/display/BrochureNavBar.tsx`, `quote-generator/components/display/PdfBrochureDocument.tsx`, `quote-generator/components/display/atoms.tsx`, `editable-brochure-contract.json`
- **Work:**
  1. Map `narrative.letterSignOff` to `LetterViewModel.signatureName` and `narrative.letterSender` to its sender/role line, using `contentCopy(..., '/narrative/...')` for both. Retain a narrowly documented legacy fallback only while a canonical document lacks the new value; the emitted path and owner must remain Content even during fallback. Do not re-use `/designer/name` or `/designer/subtitle` as an ownership shortcut.
  2. Make screen and PDF letter compositors consume the same two `LetterViewModel` values. Add a fixture where the Content sign-off/sender deliberately differ from the selected Travel Designer, so a profile fallback cannot falsely pass.
  3. Keep `sectionAriaLabel` as the sole navbar landmark input and `brandLogoAlt` as the sole preferred logo alt input. Propagate their `EditableText` metadata to their actual DOM nodes (including the Next `<Image>`), using the existing shared marker helper rather than open-coding another marker shape.
  4. Audit every canonical image slot in the media registry: asset URL, canonical alt path, `DisplayDocument` property, screen renderer, and PDF renderer. Wire any missing consumer to the paired `assetAlt` result. Decorative ornaments remain `alt=""` and are deliberately absent from the Fact-media registry.
  5. Add descriptors for `letterSignOff` and `letterSender` if absent; retain the existing `a11y.brochureSections`, `identity.logoAlt`, and media-alt descriptor identities rather than creating aliases.
- **Acceptance criteria:** A saved Content sign-off/sender changes the visible signature in both screen and PDF and Design Canvas opens `overview_letter` for either. A Design ARIA override changes `nav[aria-label]`; a Design logo-alt override changes the logo `<img alt>` and is selectable in the canvas. For every registered non-decorative image slot with an image, its `altText` reaches the matching public/PDF image; no media alt is substituted with `brandName` while a non-empty canonical `altText` exists.
- **Validation:** Runtime-builder unit tests inspect `TextValue.value/path/owner/mode`; render tests inspect `aria-label`, image `alt`, and marker attributes; PDF component tests cover the letter and at least hero, itinerary gallery, hotel, divider, and designer media slots. Include an accessibility assertion that decorative assets remain empty-alt and no actionable image has an empty accessible name when its canonical alt is populated.

## Sprint 3: Implement exact workspace handoff navigation

**Goal:** Clicking a Design Canvas target opens the existing editor at the right section and repeated item, not merely the right stage.

**Demo/validation:** Click an overview field, a day fact, a hotel fact, a price, a booking term, and a route-derived segment from the canvas; each lands at the intended editor and focus ring/expanded card.

### Task 3.1: Resolve wildcard paths to a stable editor target

- **Locations:** `BoundaryCanvas.tsx`, `DesignCanvas.tsx`, `ContextualInspector.tsx`, `useQuotationWorkspace.ts`
- **Work:** Parse a matched descriptor source against `data-editable`, capture wildcard indices, and pass a typed resolved handoff object instead of `stage + section` strings. Prefer canonical stable IDs from the loaded document where list reordering is possible; index is only a lookup hint.
- **Acceptance criteria:** `itinerary.days.2.*`, `stays.hotels.1.*`, and `pricing.options.1.*` resolve different editor targets. An unmatched marker is not made focusable or selectable.
- **Validation:** Unit tests for exact/wildcard resolution, repeated blocks, and invalid path rejection.

### Task 3.2: Add URL-driven Facts deep links and focus behavior

- **Locations:** `QuotationWorkspaceClient.tsx`, `FactsForm.tsx`, `FactsNavigator.tsx`, `DayEditor`/`HotelEditor`/pricing/booking components as applicable
- **Work:** Support a typed query payload such as `stage=facts&factsSection=programme&focus=day:<stable-id>` or `hotel:<stable-id>`, expand the required accordion/card, scroll it into view after mount, and focus its labelled control. Preserve Content’s existing `section` query behavior.
- **Acceptance criteria:** Facts stage remains source-of-truth and does not acquire duplicate inline fields. Direct URLs work after refresh and degrade to the parent Facts card when an item no longer exists.
- **Validation:** Component/browser tests for direct URL, reload, stale item fallback, and keyboard-selected BoundaryCanvas targets.

### Task 3.3: Refine inspector language and no-op state

- **Locations:** `ContextualInspector.tsx`, `DesignCanvas.tsx`
- **Work:** Label Content, Fact, Fact-derived, and System actions distinctly. Show the canonical source and a concise explanation for derived/system values. Disable action buttons when no editor exists.
- **Acceptance criteria:** No wording claims that an editable profile/system value can be edited in Facts; `system` shows no Open button.
- **Validation:** Component tests for all four owner classes.

## Sprint 4: Acceptance and regression coverage

**Goal:** Prove the contract is complete end-to-end without treating static checks as runtime evidence.

**Demo/validation:** A real quotation’s canonical document drives Design Canvas → correct editor → save → reload → public brochure and PDF retain the canonical update.

### Task 4.1: Static contract and source-coverage gates

- **Locations:** `tests/test_editable_brochure_contract.py`, `tests/test_editable_editor_coverage.py`, new focused runtime-builder tests
- **Work:** Add a maintained coverage manifest of source template, owner, descriptor ID, expected handoff/read-only behavior, renderer location, and (for ARIA/media) DOM attribute. Fail when a runtime `EditableText` is not declared, when an editable descriptor is not emitted, when an owner differs, or when an alt/ARIA `TextValue` has no attribute consumer in the screen/PDF renderer.
- **Acceptance criteria:** The audit table becomes executable coverage, not a one-time document.
- **Validation:** `python -m pytest` focused contract suite.

### Task 4.2: Browser workflow tests

- **Locations:** existing browser/Playwright test harness and new test file
- **Work:** Use a real seeded V2 quotation. Test desktop click and keyboard selection for: overview Content including sign-off/sender; itinerary day; hotel; pricing option; booking term; designer assignment; a derived route segment; and a system label. Assert the nav landmark and logo image use saved Design a11y/alt overrides, then save a permitted field, reload, and confirm the Design Canvas/public view value.
- **Acceptance criteria:** Fact and Content changes obey `baseRevision`; no Design Canvas click writes canonical state directly. System/derived fields never present a text save. The browser DOM reflects the saved ARIA/logo-alt values rather than just the editor state.
- **Validation:** Browser suite at desktop and mobile widths.

### Task 4.3: Public/PDF parity and quality gates

- **Locations:** existing Compose/browser/PDF acceptance runner
- **Work:** Render public web and PDF from the updated canonical document. Assert no editor-only chrome appears, marker propagation does not alter visible text, Content letter sign-off/sender have the same values in both outputs, and canonical image alts survive into the HTML/PDF accessibility tree where supported by the PDF renderer.
- **Acceptance criteria:** Public/PDF remain display-only and preserve canonical content plus accessibility-attribute parity.
- **Validation:** display-governor audits, frontend lint/build, backend suite, then the existing real Compose/browser/PDF acceptance flow when explicitly authorized.

## Execution order and dependencies

1. Sprint 1 is the schema boundary and must land first.
2. Sprint 2 can start after the descriptor schema, but booking provenance and the group-3 render-contract task must finish before their browser/PDF tests.
3. Sprint 3 depends on explicit handoffs from Sprint 1 and marker provenance from Sprint 2.
4. Sprint 4 depends on all previous work. Static coverage is required before runtime acceptance.

## Risks and safeguards

- **A renderer marker and descriptor diverge:** test source template matching in both directions, including wildcard sample paths.
- **Repeated-list index becomes stale:** resolve to a stable canonical ID before navigating; fall back to parent card with an explanatory notice.
- **Derived value is accidentally editable:** enforce `editMode: readonly` server-side and client-side; no direct-save endpoint accepts these descriptors.
- **Booking source path is flattened incorrectly:** test real multi-block rich content rather than a single-term fixture.
- **Shared Travel Designer data becomes quote-local:** route name/contact clicks to assignment/profile context, not to synthetic Facts fields.
- **System labels become editable per quotation:** keep them `system`, read-only, and out of presentation-copy validation allowlists.
- **Letter Content silently falls back to profile text:** use a fixture where Content and Fact values differ; assert the visible PDF and screen signature remains Content-owned.
- **A11y is only correct in the view model:** test the rendered `nav[aria-label]` and logo `<img alt>` attributes, not just `DisplayDocument` fields.
- **Media alt is paired with the wrong image after list reorder:** test image URL plus source path as a pair for gallery/hotel repeaters, and resolve repeaters by stable ID for editor navigation.
- **PDF cannot preserve an image alt in its generated artifact:** distinguish React/PDF component attribute propagation from downstream PDF tagging capability; fail the component contract and report renderer-tagging limitations separately rather than claiming full tagged-PDF compliance.

## Rollback

The contract is additive and versioned. If a new family causes a regression, remove its descriptor and runtime marker together; unmatched markers stay inert in `BoundaryCanvas`. No canonical document migration or public-layout rollback is required.
