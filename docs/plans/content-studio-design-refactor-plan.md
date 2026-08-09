# Plan: Content Studio and Design Canvas Refactor

**Generated:** 2026-08-09  
**Estimated complexity:** High

## Outcome

Replace automatic generation and JSON cards with a two-pane Content Studio.
Replace Design's global input inventory with a two-pane canvas and contextual
inspector. Preserve canonical document ownership, explicit candidate Apply,
revision checks, and the public/PDF runtime rendering contract.

## Confirmed contracts

### Section content

Brochure composition is fixed in code. A section consumes typed content blocks
and its fixed section layout; staff never edit raw HTML.

```ts
type ContentBlock =
  | { type: 'paragraph'; text: string }
  | { type: 'bulletList'; items: string[] }
  | { type: 'twoColumnList'; left: string[]; right: string[] }
  | { type: 'termList'; items: Array<{ label: string; body: string }> }
  | { type: 'paymentSchedule'; rows: Array<{ milestone: string; amount: string; dueDate?: string }> }
  | { type: 'callout'; title?: string; body: string };
```

`inclusionsExclusions` owns `twoColumnList`; `paymentTerms` owns `termList`
and `paymentSchedule`. Blocks cannot choose arbitrary DOM, section layout,
typography, or color.

### Readiness

- **Chưa đủ nội dung** — required facts exist, but required canonical fields or
  blocks are empty or invalid.
- **Cần thông tin** — an authoritative fact is absent or contradictory. Show
  the exact missing fact and link to Facts; disable AI generation.

When neither condition applies, show only a quiet check. Candidate/draft/
applied/stale is provenance in history, never the primary section status.

### Prompt ownership

The editable UI field is **Writing instruction**, not a raw system prompt.
The client submits `{ scope, generationMode, instruction? }`; the backend owns
the actual system prompt and assembles it from: versioned section recipe,
scope-limited fact snapshot, mode rules, then staff instruction at lower
priority. Cache identity includes recipe/schema version, language, mode,
facts hash, and normalized instruction hash.

The custom Writing instruction is one-shot: it applies only to the request that
submits it. It is never saved as a quotation or section default. A draft may
retain only its normalized hash and recipe metadata for cache/audit purposes.

### Publish completeness and legacy HTML

Every enabled brochure section is required to be content-complete before
Publish. The review gate must report each incomplete section; it cannot treat
content generation as optional. Legacy HTML that cannot be safely converted is
read-only during one compatibility release, visibly flagged for migration, then
must be replaced through the typed block editor before the compatibility window
is removed.

## Target UX

### Content Studio

```text
[ Section outline ]              [ Selected section ]
8 / 12 complete                  Overview letter
○ Hero — Chưa đủ nội dung         [Storytelling] [Detailed]
! Day 2 — Cần thông tin           Writing instruction
✓ Inclusions                      [seeded, editable text]
✓ Payment terms                   Facts used / required facts
                                  [AI generate]
                                  Typed editor · preview · Apply
```

- Opening Content sends no generation request.
- Selection changes the right pane only.
- AI generate is per section and disabled only by factual blockers/pending.
- Narrative, lists, terms, and payment tables use different structured editors.
- The generated output is explicitly applied; diff/history is secondary.

### Design

```text
[ Live brochure canvas ] [ Contextual inspector ]
```

Clicking a preview element resolves its editable descriptor. The inspector
edits only design-owned presentation controls. A fact/content selection shows a
read-only explanation and `Open in Facts` or `Open in Content Studio` action.

## Sprint 1: Typed content and readiness

**Goal:** define a shared contract before changing UI or prompting.

### 1.1 Create a section registry

- **Locations:** `quote_document.py`, `quote_document_adapter.py`, a new
  backend registry module, `quote-generator/display/types.ts`, and new
  `quote-generator/display/contentBlocks.ts`.
- **Work:** define section IDs, fixed layout IDs, block schemas, required
  fields, fact paths, readable labels, owners, and AI output allowlists. Export
  a frontend-safe registry rather than duplicating paths in React.
- **Acceptance:** unknown fields/blocks/owners are rejected; rich sections map
  to typed layouts.
- **Validation:** schema and ownership tests.

### 1.2 Normalize legacy HTML at the document boundary

- **Locations:** `quote_document.py`, `quote_document_adapter.py`, migration
  script under `scripts/`, Alembic only if stored JSON changes, and
  `tests/test_brochure_v2_contract.py`.
- **Work:** parse supported booking terms markup and existing inclusion/
  exclusion strings into blocks. Sanitize input and produce a manual-repair
  report for unsupported markup rather than silently dropping text.
- **Acceptance:** legal wording is preserved as text; two-column output stays
  identical; arbitrary HTML cannot reach a renderer.
- **Validation:** fixture migration, sanitization, and display snapshots.

### 1.3 Add server-owned readiness resolver

- **Locations:** new `services/content_readiness_service.py`, `main.py`, and
  `quote-generator/components/quotation-workspace/useQuotationWorkspace.ts`.
- **Work:** resolve statuses from canonical facts and canonical content rather
  than `QuotationContentDraft.status`; return label, missing paths, message,
  and destination stage.
- **Acceptance:** only the two specified statuses can be returned; workflow and
  review gates use this resolver; all enabled sections must be complete before
  publish.
- **Validation:** API tests for the two labels, ready state, and revision 409.

## Sprint 2: Per-section AI generation

**Goal:** typed, token-bounded generation with an editable instruction.

### 2.1 Implement versioned server recipes

- **Locations:** new `services/content_prompt_recipes.py`,
  `services/content_draft_service.py`, and `quote_generation.py`.
- **Work:** replace broad scopes with a recipe per section: fact allowlist,
  output schema, token budget, detailed/storytelling rules, forbidden claims,
  and output parser.
- **Rules:** hero/title uses route/duration/audience; letter keeps a coherent
  designer voice; a day uses local facts plus one-line prior/next continuity;
  inclusions/exclusions/terms can only group or clarify approved facts and may
  not invent services, values, deadlines, or legal terms.
- **Validation:** prompt tests assert facts included/excluded and no full JSON.

### 2.2 Extend the generation API

- **Locations:** `main.py`, content draft service/repository/model, Alembic,
  and `useQuotationWorkspace.ts`.
- **Work:** introduce `{ scope, generationMode, instruction? }`; maintain old
  `scopes[]` only during transition. Store instruction text within a strict
  length limit, normalized hash, recipe/schema version, and compact snapshot.
- **Acceptance:** client instruction never becomes trusted system prompt; cache
  lookup includes instruction hash; invalid scope/length/schema returns 422.
- **Validation:** fail-fast curl for 200, 422, and Apply 409; cache tests.

### 2.3 Validate candidates and registry-defined Apply

- **Locations:** `main.py`, content draft service, `quote_document.py`, and
  `tests/test_brochure_v2_contract.py`.
- **Work:** validate model and manual candidate edits before persistence; merge
  only to the section target defined by registry, replacing generic JSON merge.
- **Acceptance:** no raw HTML, unknown block, or Fact/Design path can be saved;
  Apply changes one section and creates one canonical revision.
- **Validation:** ownership, stale candidate, idempotence, render/PDF tests.

## Sprint 3: Content Studio UI

**Goal:** two panes, readable section editors, and no automatic generation.

### 3.1 Replace the Content Studio shell

- **Locations:** refactor `components/content-studio/ContentStudioClient.tsx`;
  add focused components under `components/content-studio/`.
- **Work:** render server readiness as the outline and selected workspace.
  Remove the current auto-generation `useEffect` and regenerate-all header.
- **Acceptance:** only two labels; fact blockers deep-link to Facts; selection
  survives SWR refresh and reload.
- **Validation:** component tests and browser assertion of no automatic POST.

### 3.2 Add mode, instruction, and generate action

- **Locations:** new `ContentGenerationPanel.tsx`, Content Studio client, and
  workspace hook.
- **Work:** add Storytelling/Detailed mode, seeded editable instruction,
  facts-used disclosure, and per-section `AI generate` action.
- **Acceptance:** browser sends typed data only; pending/factual blockers are
  the only button-disabled states; returned draft records selected mode/prompt.
- **Validation:** mocked UI tests and browser network assertion.

### 3.3 Build block-specific editors

- **Locations:** `NarrativeSectionEditor.tsx`, `ListBlockEditor.tsx`,
  `TermsBlockEditor.tsx`, `PaymentScheduleEditor.tsx`, and candidate preview.
- **Work:** use registry selection; implement list add/remove/reorder and a
  readable preview. Keep history/diff under a secondary control.
- **Acceptance:** no raw JSON/HTML textarea; edit → Apply → reload maintains
  fixed brochure layout.
- **Validation:** unit tests per editor and browser flow.

## Sprint 4: Design canvas and inspector

**Goal:** direct selection without leaking Content/Facts fields into Design.

### 4.1 Enrich editable descriptors

- **Locations:** `editable-brochure-contract.json`,
  `editable_brochure_contract.py`, `runtimePageBuilder.ts`, display atoms/
  molecules/sections, and `tests/test_editable_editor_coverage.py`.
- **Work:** add stable field ID, section ID, owner, edit mode, and inspector
  control kind. Retain descriptors as editor-only annotations.
- **Acceptance:** every design field maps to one inspector control; all
  Fact/Content fields provide a handoff route.
- **Validation:** descriptor coverage and display-system audits.

### 4.2 Implement two-pane canvas editor

- **Locations:** replace `DesignMediaPanel.tsx` with `DesignCanvas.tsx`,
  `ContextualInspector.tsx`, inspector controls; update
  `QuotationWorkspaceClient.tsx`.
- **Work:** wrap canonical `DisplayPage` in workspace-only selection overlay;
  add hover/focus selection and owner-aware inspector output.
- **Acceptance:** primary composition is canvas + inspector only; inspector is
  empty before selection and never lists every design field; public render is
  unchanged outside the workspace overlay.
- **Validation:** mouse/keyboard Playwright tests, desktop/mobile/PDF shots,
  and public DOM snapshot.

### 4.3 Persist only Design-owned fields

- **Locations:** presentation override validation in `main.py`, workspace hook,
  and inspector save flow.
- **Work:** reuse revision-checked presentation APIs but filter payload through
  registry. Add crop/media only if the existing canonical media API owns it;
  otherwise show a handoff rather than creating a second media source.
- **Acceptance:** presentation API cannot modify Fact/Content; 409 preserves
  local state for refresh/retry; web and PDF agree after reload.
- **Validation:** ownership/409 API plus browser/PDF checks.

## Sprint 5: Cutover and verification

- Update workflow/review gates in `main.py` to use readiness resolver while
  keeping a measured read-compatible path for legacy documents.
- Extend `scripts/run_compose_e2e.sh` and `e2e/playwright_compose_v2.py` for
  facts → section generate → edit/apply → reload → Design save → publish/PDF.
- Run Alembic, backend tests, display/typography/color audits, lint, build, and
  real Compose acceptance at desktop, 980px, mobile, and PDF.
- Ensure `.env.local` provider credentials never enter browser/E2E logs.

## Risks and rollback

- Keep recipes server-owned to prevent rule bypass or prompt injection.
- Migrate only recognized HTML; flag the remainder for manual repair.
- Preserve local content/inspector changes after 409; never overwrite silently.
- Feature-flag Studio/Inspector for one release and keep old documents
  read-compatible. If block validation/render fails, block Apply for that
  section and render prior valid canonical content; never publish failure.
