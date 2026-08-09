# Plan: Travel Designer CRUD for Quotation Workspace

Portraits use the contextual `team/{user-name}` R2 contract in [11-r2-media-file-contract.md](./refactor-tech-stack/11-r2-media-file-contract.md).

**Generated**: 2026-08-05  
**Estimated Complexity**: Medium

## Overview

Replace the current static `Travel designer` `<select>` in the new Quotation Workspace with a searchable profile picker that can select an existing designer, create one inline, and open a small management drawer. The profile directory remains temporary Quote Generator-owned data, mapped by normalized email until DMC Core becomes the identity owner.

The selected profile is a presentation choice. The quote must store the selected profile ID at quote level and snapshot the render-relevant fields (`name`, `email`, `phone`, portrait) into every current language document. A later profile edit must affect only future assignments; it must never mutate a previously saved or published quotation.

## Root Cause Analysis

The new UI has the visual location for the feature but not the domain integration:

- [`FactsForm.tsx`](../../quote-generator/components/quotation-workspace/FactsForm.tsx) renders `Travel designer` as a native `<select>` populated from `options.travelDesigners`. It has no search, portrait, create, edit, status, or default action.
- [`GET /api/v2/quotation-options`](../../main.py) embeds the active profiles into a broad options payload. This makes the directory an incidental dropdown data source instead of an explicit CRUD resource.
- [`TravelDesignerRepository`](../../repositories/travel_designer_repository.py) can create/list/look up/default profiles, but does not yet expose update/status operations through FastAPI.
- [`_apply_presentation_snapshot`](../../main.py) writes only when a profile is present. Clearing a selection would leave prior designer snapshot data behind. The presentation-options endpoint currently updates only the baseline document, while a designer assignment must keep all existing language documents aligned.
- `core/auth.py` exists, but the current V2 routes shown in `main.py` do not consistently depend on an authenticated editor principal. Browser calls from the Next.js workspace must reach the API through the trusted gateway path; the browser must never synthesize DMC identity headers.

## Scope and Decisions

- Every authenticated Quote Generator editor may create, edit, deactivate, select, and set the default Travel Designer in this release.
- A profile contains only `name`, normalized unique `email`, `phone`, and an optional global portrait asset/image URL. There is no temporary user/role table.
- Profiles are soft-deactivated. They are never hard-deleted from the UI or API.
- Default selection precedence when creating a quotation is: active profile matching the authenticated actor email, then active brand default, then unassigned.
- Creating a profile is explicit. An unknown actor email must not auto-create a profile.
- Quote assignment accepts a profile ID only. The server resolves, validates, snapshots, and persists it; clients never submit designer contact values as the assignment payload.
- Existing manual designer copy such as `kicker`, `title`, `quote`, and `experience` remains editable content. Clearing a selected profile clears only profile-owned snapshot fields (`profileId`, name, email, phone, portrait), not editorial copy.
- The React display components remain pure. The picker and management drawer live in `quotation-workspace`, not in `components/display` or the public display system.

## Prerequisites

- Apply Alembic migration `20260804_02_travel_designer_profiles` in each target environment before enabling the UI.
- Confirm the public Quote Generator gateway path proxies browser API calls to FastAPI and injects trusted DMC headers. Set the frontend API base to that protected same-origin path or a trusted gateway URL; do not use a browser-set `X-DMC-*` header.
- Configure `QUOTE_AUTH_REQUIRED=true` and a server-only `QUOTE_SERVICE_TOKEN` in production. Keep local bypass explicitly disabled in production.

## Sprint 1: Complete the Profile and Assignment Backend

**Goal**: Make Travel Designer an authenticated, standalone backend resource and make quote assignment durable across all current languages.

**Demo/Validation**:

- An authenticated editor can list, create, edit, and deactivate a designer through documented APIs.
- Selecting a profile changes the quote snapshot in English, Vietnamese, and Arabic current documents, then creates a revision for each changed document.
- Editing the profile afterward does not change the quote snapshot.

### Task 1.1: Finalize quote-level relationship and repository operations

- **Location**: `db/models/quotation.py`, `alembic/versions/20260804_02_travel_designer_profiles.py`, `repositories/quotation_repository.py`, `repositories/travel_designer_repository.py`
- **Description**:
  - Add nullable `quotations.designer_profile_id` with a foreign key to `travel_designer_profiles` and an index. Update the migration safely if it has not been deployed; create a follow-up migration if any environment has already applied it.
  - Add repository methods for profile update, status update, brand-default retrieval/upsert, quote designer update, and `list_current_documents(quotation_id)`.
  - Enforce normalized lowercase email before persistence. Map the unique-constraint conflict to a domain error suitable for HTTP 409.
- **Dependencies**: Existing profile tables and repository.
- **Acceptance Criteria**:
  - An inactive profile cannot be assigned or made a brand default.
  - A duplicate email that differs only in case/whitespace is rejected.
  - Deactivating a selected profile does not modify any historical quote snapshot.
- **Validation**: Async repository tests using SQLite/Postgres-compatible constraints.

### Task 1.2: Add authenticated Travel Designer CRUD APIs

- **Location**: `main.py`, `core/auth.py`, `services/media_service.py` or existing media validation boundary, new `tests/test_travel_designer_api.py`
- **Description**:
  - Add editor-only endpoints:
    - `GET /api/v2/travel-designers?active=true&search=&limit=`
    - `POST /api/v2/travel-designers`
    - `PUT /api/v2/travel-designers/{profile_id}`
    - `PATCH /api/v2/travel-designers/{profile_id}/status`
    - `PUT /api/v2/brands/{brand_id}/travel-designer-default`
  - Use a single response shape: `id`, `name`, `email`, `phone`, `imageAssetId`, `imageUrl`, `isActive`, timestamps, and optional `isBrandDefault` where relevant.
  - Reuse `POST /api/v2/media/upload` with no `quotationId` for portraits. Validate that `imageAssetId` resolves to an allowed, ready global media asset. Do not create a second profile-upload storage path.
  - Apply `Depends(require_editor)` to these routes. Preserve local development bypass only through the existing explicit configuration.
- **Dependencies**: Task 1.1; production gateway/API origin decision.
- **Acceptance Criteria**:
  - Inactive profiles are excluded by default, but can be listed for management with `active=false`/`active=all`.
  - A profile can be created without a portrait and later updated with one.
  - API error responses distinguish invalid input (422), duplicate email (409), missing profile/media (404), and forbidden/unauthenticated access (403/401).
- **Validation**: FastAPI API tests for CRUD, normalized uniqueness, soft deactivation, global-media validation, and principal permissions.

### Task 1.3: Replace presentation-options assignment with a dedicated quote assignment operation

- **Location**: `main.py`, `quote_document.py`, `repositories/quotation_repository.py`, `tests/test_brochure_v2_contract.py`, new `tests/test_travel_designer_assignment.py`
- **Description**:
  - Add `PUT /api/v2/quotations/{quotation_id}/travel-designer` with `{ designerProfileId: string | null, baseRevision, lang }`.
  - Load the active profile server-side, update `quotations.designer_profile_id`, and write a controlled snapshot into `document.designer`.
  - On assignment, apply the snapshot to every current language document. For the actively edited language, require `baseRevision`; for other current language documents, update from their freshly loaded revision inside the same transaction. Append a `assign_travel_designer` revision for each language.
  - On unassign, remove `designer.profileId`, name, email, phone, and portrait only; retain editorial designer content.
  - Change `_apply_presentation_snapshot` to call the same dedicated snapshot helper so create, facts rebuild, and assignment use identical behavior.
  - Keep `PUT /presentation-options` temporarily for template choice/backward compatibility, but have it delegate designer changes to the same service or reject the designer field after the frontend cutover. Do not leave two divergent write paths.
- **Dependencies**: Tasks 1.1 and 1.2.
- **Acceptance Criteria**:
  - A selected profile updates web/PDF source data for every existing language.
  - An inactive or unknown ID cannot be assigned.
  - A stale revision returns 409 with the current document for the active language.
  - Profile edits never back-propagate into existing documents or publication artifacts.
- **Validation**: Regression tests for assign, reassign, unassign, multilingual updates, conflict behavior, and snapshot immutability.

### Task 1.4: Apply default selection during V2 quotation creation

- **Location**: `main.py`, `core/auth.py`, `quote-generator/components/quotation-workspace/factsTypes.ts`, backend tests
- **Description**:
  - Protect V2 creation with `require_editor_or_service`.
  - Resolve the initial profile as actor-email match, then brand default, then an explicit valid `presentationOptions.travelDesignerId` selected in the form; reject a client-provided inactive/unknown ID.
  - Service-token creation may use a valid supplied profile only if server-side policy permits it; otherwise use brand default/unassigned. It must never infer a person from an arbitrary payload email.
  - Return the resolved designer selection in create/facts responses so the UI can show the true saved state.
- **Dependencies**: Tasks 1.1–1.3.
- **Acceptance Criteria**:
  - A new quote defaults to the logged-in sales person's active profile when available.
  - An unknown actor gets the brand default or no selection; no new profile is silently created.
- **Validation**: Principal/default-precedence tests and create-quotation API tests.

## Sprint 2: Build the New UI Picker and Inline Create Flow

**Goal**: Replace the native dropdown with a fast, accessible Travel Designer picker in both `/quotations/new` and the workspace Facts stage.

**Demo/Validation**:

- User can search by name/email, see portrait/contact context, select a designer, add one in place, and continue the quotation flow without losing entered facts.
- A DMC handoff quote retains locked facts while its Travel Designer choice remains editable.

### Task 2.1: Introduce a typed API client and Travel Designer domain types

- **Location**: new `quote-generator/lib/quotationApi.ts`, `quote-generator/components/quotation-workspace/factsTypes.ts`, `NewQuotationClient.tsx`, `QuotationWorkspaceClient.tsx`
- **Description**:
  - Centralize API base URL, JSON error parsing, designer API calls, and the authenticated same-origin request convention.
  - Add `TravelDesignerProfile` and paged-list response types separately from `QuotationOptions`.
  - Remove `travelDesigners` as the frontend source of truth from `QuotationOptions` after the picker is live; retain backend compatibility only while old clients exist.
- **Dependencies**: Sprint 1 API contract.
- **Acceptance Criteria**:
  - Both create and existing-quote flows use the identical data source and response types.
  - Errors can be shown adjacent to the picker instead of only in the page-level status message.
- **Validation**: TypeScript compile, lint, and API-client unit coverage if a test harness is introduced; otherwise browser smoke coverage in Task 2.4.

### Task 2.2: Implement `TravelDesignerPicker`

- **Location**: new `quote-generator/components/quotation-workspace/TravelDesignerPicker.tsx`, `FactsForm.tsx`
- **Description**:
  - Replace `SelectField` for Travel Designer with a combobox-style picker displaying name, email, phone, active state, and portrait fallback.
  - Fetch active profiles on open; debounce search; retain the selected value even if the current profile was subsequently deactivated so existing quotes can be understood and changed.
  - Provide actions: `Add designer`, `Edit selected`, `Manage designers`, and `Clear selection`.
  - Keep all typography and color use within existing semantic contracts. This is workspace UI, not a public display section.
- **Dependencies**: Task 2.1.
- **Acceptance Criteria**:
  - Fully keyboard navigable, labelled, and announces loading/empty/error states.
  - Selected option shows enough identity context to disambiguate designers with similar names.
  - Selection changes only local `presentation_options.travel_designer_id` until the user presses the existing save/create action.
- **Validation**: Manual keyboard and narrow/mobile visual check; `npm run lint` and `npm run build`.

### Task 2.3: Implement profile form and management drawer

- **Location**: new `TravelDesignerProfileDrawer.tsx` and `TravelDesignerProfileForm.tsx` under `quote-generator/components/quotation-workspace/`; reuse `MediaDrawer.tsx` patterns where suitable
- **Description**:
  - Implement a small drawer/modal for create, edit, portrait upload/select, deactivate/reactivate, and brand-default assignment.
  - On a successful create, refresh the picker cache and select the returned profile in the unsaved quote form.
  - Keep deactivation recoverable: show active/inactive status, require a short confirmation, and never offer destructive delete.
  - Use the existing media upload flow without `quotationId` for global portraits; update the form with returned `imageAssetId` and URL.
- **Dependencies**: Tasks 1.2, 2.1, and existing `MediaDrawer` behavior.
- **Acceptance Criteria**:
  - Duplicate-email error is shown against the email input without clearing the user's other form values.
  - The drawer can create a profile during the initial quote flow and the new profile is immediately selectable.
  - Profile management does not directly mutate an already-assigned quote preview.
- **Validation**: Browser smoke for create/edit/deactivate/default and focused responsive visual verification.

### Task 2.4: Wire selection to creation and existing quote save paths

- **Location**: `NewQuotationClient.tsx`, `QuotationWorkspaceClient.tsx`, `FactsForm.tsx`
- **Description**:
  - For `/quotations/new`, include only `presentationOptions.travelDesignerId` in the create payload. Display the resolved server result after creation.
  - For the existing workspace, replace the designer portion of `savePresentation` with the dedicated quote assignment API. Template choice may remain in the existing endpoint.
  - After a successful assignment, revalidate facts, document, designer list, and preview state. For 409, retain the picker choice and offer reload/try again rather than silently overwriting it.
- **Dependencies**: Task 1.3 and Tasks 2.1–2.3.
- **Acceptance Criteria**:
  - DMC handoff quotes permit selection and save only presentation data.
  - Manual quote facts remain unchanged by selecting a designer.
  - The Design preview reflects the selected snapshot after revalidation.
- **Validation**: End-to-end browser flows for manual and DMC handoff quote creation/editing.

## Sprint 3: Security, Regression Coverage, and Cutover

**Goal**: Make the feature safe through both direct Cloudflare Access and DMC Control Panel iframe entry, then remove the old dropdown data dependency.

**Demo/Validation**:

- Direct quote domain login and Control Panel iframe entry both show the same profile directory and can save an assignment.
- Public quotation/PDF endpoints remain public; editor/master-data routes reject anonymous callers.

### Task 3.1: Close authenticated route coverage and deployment path

- **Location**: `main.py`, `core/auth.py`, quote deployment env/config, sibling DMC gateway configuration if needed
- **Description**:
  - Require editor principals for profile CRUD, facts/presentation editing, document editing, media operations, narrative generation, assignment, and publish.
  - Allow service token only for server-to-server quote creation; forbid it for profile management and interactive mutations.
  - Verify the Next.js workspace calls the protected API origin and receives gateway-injected headers on the API request itself. Add a proxy/route-handler only if this is necessary to preserve the identity boundary.
  - Keep published HTML/PDF customer routes outside this dependency.
- **Dependencies**: Sprint 1 and actual gateway deployment configuration.
- **Acceptance Criteria**:
  - Spoofed browser headers cannot authenticate a public origin request.
  - Direct and iframe flows converge on the same authorization decision.
- **Validation**: Principal tests, gateway configuration validation, and two browser smoke paths.

### Task 3.2: Add focused regression and browser tests

- **Location**: `tests/test_travel_designer_api.py`, `tests/test_travel_designer_assignment.py`, `tests/test_quote_auth.py`, optionally a browser smoke script under `scripts/`
- **Description**:
  - Cover CRUD, normalized email, active filtering, default validation, global portrait media validation, assignment snapshot, unassign behavior, multilingual document updates, profile-edit immutability, and 409 conflicts.
  - Cover creation precedence: actor email, brand default, unassigned, and service-token behavior.
  - Exercise UI flows: select existing, create inline, save an existing DMC quote, deactivate a profile, publish, and compare the designer block in web/PDF output.
- **Dependencies**: Tasks 1.1–3.1.
- **Acceptance Criteria**:
  - Tests prove document and published snapshot stability, not only API status codes.
  - Browser evidence verifies actual picker clicks and upload behavior.
- **Validation**:
  - `python -m pytest tests/test_travel_designer.py tests/test_travel_designer_api.py tests/test_travel_designer_assignment.py tests/test_quote_auth.py -q`
  - `cd quote-generator && npm run lint && npm run build`
  - Display-contract audits remain green.

### Task 3.3: Cut over and document the future DMC Core migration

- **Location**: `docs/plans/refactor-tech-stack/`, `.env.example`, deployment runbook
- **Description**:
  - Remove frontend reliance on `quotation-options.travelDesigners` once all supported clients use the dedicated endpoint.
  - Document environment variables, migration order, gateway prerequisites, and rollback procedure.
  - Document the future migration: add nullable `dmc_person_id`, exact normalized-email backfill, transfer uniqueness/ownership to DMC identity, retain email/contact snapshots for quote rendering.
- **Dependencies**: Successful Sprint 3.1 and 3.2 verification.
- **Acceptance Criteria**:
  - Deployment can be rolled back by hiding the picker and retaining existing profile/quote data.
  - No browser-visible service token or DMC identity secret is introduced.
- **Validation**: Migration rehearsal against a copy of production-like data and direct/iframe smoke test after deploy.

## Testing Strategy

- Backend: repository and API tests prove uniqueness, active-only behavior, soft deactivation, media validity, quote-level linkage, per-language snapshot writes, revision conflicts, and authorization.
- Frontend: run lint, display/typography/color guards, production build, then verify the picker using keyboard and responsive layouts.
- Integration: test manual and DMC handoff quotes separately because facts ownership differs but presentation selection must work in both.
- Render regression: after assignment and after profile edit, inspect the current document, rendered web quotation, and PDF route. They must agree for the assigned snapshot; profile edits must not change any historical artifact.

## Potential Risks and Mitigations

- **Two assignment write paths**: keeping both `presentation-options` and a new assignment endpoint can create drift. Route both through one service during transition, then remove the old designer field from the former.
- **Stale clear selection**: the current snapshot helper leaves a stale designer block when the selected ID is empty. Add an explicit profile-owned-field clear helper and regression test.
- **Multi-language revision races**: assignment must update all current documents atomically and enforce conflict protection for the language the editor is viewing.
- **Gateway/header loss across origins**: direct browser calls to an unprotected FastAPI origin would lose trusted identity. Verify the deployment path before enabling `QUOTE_AUTH_REQUIRED`.
- **Profile edits rewriting history**: never render from the profile table after assignment; render only from the canonical document snapshot.
- **Incomplete previous verification**: run the full suite separately and classify any legacy dirty-fixture failure; do not mask or overwrite user-generated `published/` artifacts.

## Rollback Plan

- Disable the new picker behind a frontend feature flag and temporarily retain the existing read-only options select.
- Keep all created profiles, defaults, quote profile IDs, and document revisions; they are additive and recoverable.
- If an API deployment must roll back, stop exposing CRUD routes but retain the migration. Do not drop profile tables or erase portrait assets.
- If a bad assignment reaches a draft, reassign or clear it through the assignment endpoint; if it is published, publish a corrected new version rather than editing the historical artifact.
