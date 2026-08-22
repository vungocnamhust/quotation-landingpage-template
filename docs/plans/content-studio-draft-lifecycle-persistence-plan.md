# Plan: Content Studio Draft Lifecycle and Persistence Repair

**Generated**: 2026-08-22  
**Estimated Complexity**: High

## Overview

Repair Content Studio around one explicit state model:

`canonical document` is the only brochure source of truth; an `unapplied draft` is a review artifact for exactly one scope and base revision; `stale`, `discarded`, and `applied` records are history, never candidates that may be rendered as current or applied again.

The work removes automatic draft creation from action labels that imply navigation, makes manual editing an LLM-free path, and proves every successful Apply is atomically persisted in Postgres as both the current document and an immutable document revision.

## Prerequisites

- A disposable V2 Compose database and a seeded owned quotation with at least two content scopes and itinerary days.
- Browser test access to the workspace routes and authenticated editor session.
- Preserve existing V2 API/auth/error/revision contracts unless a versioned replacement is explicitly approved.

## Sprint 1: Establish lifecycle contract and forensic coverage

**Goal**: Freeze the intended state transitions before changing behavior.

**Demo/Validation**:

- A transition test shows which records can be rendered, edited, applied, discarded, or retained only as history.
- A database assertion proves an Apply changes `quotation_documents.document_json`, increments its revision, and writes one `quotation_document_revisions` row with `change_source=apply_content_draft` in the same committed transaction.

### Task 1.1: Define the persisted draft lifecycle contract

- **Location**: `docs/plans/refactor-tech-stack/08-quotation-content-studio-contract.md`, new focused lifecycle contract under `docs/contracts/` if the existing document should remain immutable.
- **Description**: Define status transitions and allowed operations: `draft -> applied | discarded | stale`; prohibit re-edit/re-apply of `stale`; make `applied` immutable historical provenance. Define the exact semantic difference between Save draft, Apply, Apply all, and Proceed to Design.
- **Dependencies**: None.
- **Acceptance Criteria**:
  - Only `draft` records are actionable.
  - A stale record cannot be rendered as the editable current candidate or passed to Apply/Apply all.
  - A content UI view has one selected source: local unsaved edit, current actionable draft, or canonical document.
- **Validation**: Unit test table covering every state/action combination.

### Task 1.2: Add persistence and revision integration tests

- **Location**: `tests/` (new API/repository integration module), `e2e/browser_pdf_compose_v2.py`.
- **Description**: Test manual Apply and generated Apply against real Postgres; reload through `GET /document` and query the repository to verify the exact field, current revision, revision provenance, and applied draft status. Assert failed revision conflicts leave all three unchanged.
- **Dependencies**: Task 1.1.
- **Acceptance Criteria**:
  - Response success alone is insufficient; committed database state is asserted after a fresh session.
  - Per-draft Apply is atomic: no partial document/revision/draft state on error.
  - Existing browser test keeps asserting that merely opening Content sends no POST to `/content-drafts`.
- **Validation**: Focused pytest plus Compose browser/PDF acceptance report.

## Sprint 2: Make backend draft operations safe and deterministic

**Goal**: Eliminate stale-draft replay and silent partial batch writes.

**Demo/Validation**:

- After applying one scope, sibling drafts become visible historical `stale` records but Apply all reports zero actionable candidates until fresh drafts are deliberately created.
- A malformed or no-longer-applicable draft fails the batch endpoint atomically with a precise error; no exception is swallowed.

### Task 2.1: Restrict Apply and Apply all to current drafts

- **Location**: `routers/v2/quotation_document.py`, `repositories/quotation_repository.py`.
- **Description**: Change `apply_all_content_drafts_v2` to select only `status == "draft"`; revalidate candidate scope and revision/facts freshness before merge. Do not accept `stale` in the single-Apply endpoint. Keep applied provenance immutable and stale only unresolved sibling records.
- **Dependencies**: Sprint 1.
- **Acceptance Criteria**:
  - No stale candidate can overwrite canonical content.
  - Single Apply returns a clear conflict/unprocessable response for stale input.
  - Status changes are language-scoped where that is the intended contract.
- **Validation**: API integration tests for old draft replay, sibling invalidation, and locale isolation.

### Task 2.2: Make batch apply transactional and observable

- **Location**: `routers/v2/quotation_document.py`, `services/content_draft_service.py`.
- **Description**: Replace `except Exception: pass` with upfront validation and deterministic failure reporting. Merge a stable ordered set of eligible drafts, save the document once, append one revision, then mark exactly those IDs applied in the same transaction. Return applied and skipped IDs only if partial behavior is explicitly approved; default to all-or-nothing.
- **Dependencies**: Task 2.1.
- **Acceptance Criteria**:
  - No successful response can conceal a skipped/failed scope.
  - Duplicate scope candidates are resolved deterministically or rejected; they are never dependent on `created_at` ordering alone.
  - `appliedCount` equals the persisted status transitions.
- **Validation**: Tests for duplicate scope, schema-invalid candidate, non-existent itinerary day, and rollback after document save failure.

### Task 2.3: Consolidate context loading and typed route contracts

- **Location**: `routers/v2/quotation_document.py`, `services/content_draft_service.py`, `schemas/v2/`.
- **Description**: Extract repeated quotation/request/document/brand loading from every content endpoint to typed dependencies/service methods; retain `Annotated[..., Depends(...)]`, explicit return schemas, and one HTTP operation per function.
- **Dependencies**: Task 2.1.
- **Acceptance Criteria**:
  - Every endpoint enforces the same ownership, language, current-document, and revision semantics.
  - No blocking database work is introduced into async code beyond the current async repository model.
- **Validation**: OpenAPI manifest and route contract tests.

## Sprint 3: Repair Content UI ownership and explicit user intent

**Goal**: Ensure manual editing never generates content, navigation never mutates content, and the UI cannot resurrect old candidates.

**Demo/Validation**:

- Opening Content and navigating Design -> Content produces no content POST.
- Typing changes only local state; Save creates a manual draft with `llmCalled=false`; Apply persists it exactly once.
- Returning after Apply displays the canonical document projection, not an old draft or locally reconciled fallback.

### Task 3.1: Make manual mode a first-class state, not an implicit fallback

- **Location**: `quote-generator/components/content-studio/useContentStudioState.ts`, `useContentGeneration.ts`, `ContentStudioClient.tsx`, `ContentGenerationPanel.tsx`.
- **Description**: Model `manual` separately from generation modes or explicitly label it as edit mode. Hide/disable Generate in manual editing and preserve the `POST /manual` path only for explicit Save/Apply. Ensure no effect, mount, or selection path invokes generation.
- **Dependencies**: Sprint 1.
- **Acceptance Criteria**:
  - Manual Save/Apply sends no call to LLM generation and stores metadata `llmCalled=false`.
  - Mode choices, prompt preview, and selected pills cannot claim to alter a request when their values are not sent to the backend.
  - Switching scopes resets only unsaved local state after an explicit discard/confirmation policy.
- **Validation**: Mocked request tests and Playwright request capture.

### Task 3.2: Remove mutating navigation behavior

- **Location**: `quote-generator/components/content-studio/useContentGeneration.ts`, `ContentStudioClient.tsx`, `QuotationWorkspaceClient.tsx`.
- **Description**: Make Proceed to Design a pure navigation unless the user explicitly chooses an Apply action. Replace the ambiguous combined CTA with separate Apply selected/Apply all and Proceed actions; warn only when unsaved local edits exist.
- **Dependencies**: Task 3.1.
- **Acceptance Criteria**:
  - Design navigation never creates a manual draft, patches a draft, or calls Apply all.
  - Apply all makes scope selection and exact count visible before commit.
- **Validation**: Browser request assertions for navigation with draft, stale history, and unsaved local edit.

### Task 3.3: Render only the correct current source

- **Location**: `quote-generator/components/content-studio/useContentStudioState.ts`, `services/content_registry.py`, `quote-generator/lib/rules/contentReconciler.ts`.
- **Description**: Select at most one current `draft` per scope by a deterministic server contract. Exclude stale/applied history from editor selection and badges. Keep `reconcileCandidateWithFacts` for facts-derived presentation only; do not allow it to silently replace persisted content values or mutate field ownership on re-entry.
- **Dependencies**: Sprint 2.
- **Acceptance Criteria**:
  - A canonical candidate loaded after Apply round-trips field-for-field through Content.
  - The Content screen cannot show a stale candidate as editable current content.
  - The sidebar distinguishes “current draft” from historical stale/applied records and never counts history as Apply-able.
- **Validation**: React unit tests for source precedence plus browser Design -> Content regression test.

## Sprint 4: Acceptance, migration, and observability

**Goal**: Safely clean existing bad state and make future drift diagnosable.

**Demo/Validation**:

- An operator can inspect a quotation’s history without risking replay.
- Full Compose test passes the four reported user journeys with real Postgres, API, browser, and PDF output.

### Task 4.1: Add a safe historical-draft remediation command

- **Location**: New audited one-shot script/service under `scripts/` or an explicit Compose profile.
- **Description**: Report duplicate, stale, and invalid drafts by quotation/lang/scope; require an explicit approved action to archive/discard unsafe unresolved history. Do not delete production records automatically.
- **Dependencies**: Sprint 2.
- **Acceptance Criteria**:
  - Dry-run is the default and outputs affected IDs/statuses.
  - Mutation is idempotent, scope-limited, and logged.
- **Validation**: Fixture database tests and dry-run output snapshot.

### Task 4.2: Run end-to-end acceptance and release gates

- **Location**: `e2e/browser_pdf_compose_v2.py`, `scripts/run_compose_e2e.sh`, related focused tests.
- **Description**: Cover: Apply persistence; manual edit without LLM; Content entry with zero actionable drafts; and Design -> Content retaining the last applied canonical content. Then run backend, frontend, Compose/browser/PDF gates.
- **Dependencies**: Tasks 4.1 and all prior sprints.
- **Acceptance Criteria**:
  - Acceptance report records revision before/after, DB provenance, observed POST list, and canonical values after navigation.
  - `npm run lint`, `npm run lint:typography`, `npm run lint:display-system`, and `npm run build` pass in a clean worktree.
- **Validation**: Saved `artifacts/e2e/compose-acceptance-report.json` plus command logs.

## Testing Strategy

- Unit: state machine, candidate merge, reconciliation preservation, and UI source precedence.
- API/repository integration: real transaction commit/rollback, revision conflict, stale rejection, batch atomicity, and multiple locales.
- Browser: request capture proves no POST on tab entry or navigation; manual save/apply proves no generation endpoint.
- Compose: verify Postgres rows directly after a fresh API read; verify the canvas and generated PDF use the same canonical revision.

## Potential Risks & Gotchas

- Existing rows have no explicit supersedes/active-draft identifier, so cleanup must never assume newest-by-timestamp is safe.
- Facts updates currently stale both draft and applied provenance; history semantics must be preserved without allowing an applied record to become Apply-able.
- Design Canvas can write content-owned fields directly to `/document`; its revision update must stay compatible with Content’s compare-and-swap policy.
- Current workspace retry behavior reloads then re-submits an old full document. Keep conflicts user-visible and do not reintroduce automatic mutation retries during this repair.
- The current worktree contains unrelated dirty display/PDF/map changes; validate this work against an isolated clean checkout or exclude unrelated failures from the evidence.

## Rollback Plan

- Ship backend eligibility changes before any optional history cleanup; they immediately prevent stale replay without deleting data.
- Retain all old rows as non-actionable history until a reviewable remediation report is approved.
- If a UI rollout regresses, revert only its deployment while the backend keeps stale drafts non-applyable; canonical document revisions remain recoverable through the existing revision history.
