# Reality Check — Actionable Content Plan

**Baseline audited:** 2026-08-24  
**Database baseline:** Alembic `20260823_34`  
**Scope:** new-model V2 quotations only. A quotation without `quotation_family_id` remains on its legacy path.

## Target decision

Use a hybrid-minimum Actionable Content Plan. Facts are immutable and always win. Deterministic code protects entity identity, document projections, carry-forward, and document revisions. The plan then exposes selected Content actions:

- `auto`: generate a reviewed draft only;
- `bypass`: generate, validate, and apply only whitelisted editorial fields after an explicit confirmation;
- `manual`: no AI action; use Fact defaults and a manual Content editor.

`storytelling` and `detailed` remain writing styles. They must not be reused as execution policies.

## Reality-check findings

| Area | Evidence | Current state | Required direction |
|---|---|---|---|
| Version router | `routers/v2/quotation_versions.py:create_quotation_business_version` | Router imports `main.py`, canonicalizes Facts, builds skeleton, copies content, applies media, persists rows and outbox. | Extract factory/service/repository orchestration; router only validates/authenticates/calls service. |
| Successor copy | `routers/v2/quotation_versions.py:_copy_successor_owned_values` | Day prose/media overrides copy by `sourceFactId`, with a semantic comparison; global editorial content is not handled by a dedicated service. Dead `_clear_incompatible_day_carry_forward` still uses day number. | One semantic carry-forward service; sourceFactId mandatory for new-model, no day-number path except legacy adapter. |
| Stable day identity | `_ensure_itinerary_fact_ids` | Missing IDs are derived from index/date/destination. Inserting or reordering old ID-less facts can change identity. | First creation assigns a permanent Fact ID. New-model successor refuses or deterministically repairs a missing ID before persistence. |
| Impact engine | `services/quotation_impact_analysis.py` | `FactDependency` hardcodes `impact_policy`, targets and deep links; parent impact is often one target. Itinerary source path is broad (`trip_facts.itinerary`), not a persisted leaf change. | Replace with small Change Plan service based on semantic lifecycle and Content scope input projections. No Design targets. |
| Content registry | `services/content_registry.py` | Both `fact_allowlist` and `fact_used` exist, while batch generation creates independent snapshots. `pricing`, `hotel_plan`, `inclusions_exclusions` are Fact-owned and cannot generate. | One scope contract for prompt context, ownership and automation policy; separate authoritative facts from editorial display copy. |
| Content generation | `services/content_draft_service.py:create_batch`, `services/section_content_generator.py:generate_itinerary_days_batch` | Batch uses separate manually-built snapshots; day generator references undefined `day` while setting `source_fact_id`. No inherited predecessor context contract. | Repair batch identity and use one context builder. Add typed inherited-reference audit metadata. |
| Apply semantics | `routers/v2/quotation_document.py:apply_content_draft_v2` | Applying a draft silently resolves matching pending impacts. `apply-all` remains available. | Draft application must not resolve an unrelated plan implicitly. Bypass uses a dedicated atomic selected-scope execution service; no Fast Track reuse. |
| Persistence | migrations `31`–`34`, `db/models/quotation.py` | `34` removes Design target rows but retains parent Design rows/status fields. Impact targets/acceptances store selection but no action execution audit. | Add Action Plan/action execution records; stop reading Design impact data. Retain compatibility reads for 31–34 new-model rows only. |
| Impact Center | `quote-generator/components/quotation-workspace/ImpactCenter.tsx` | Selection records IDs only; text says nothing is generated/applied; object values render as `Changed`; only Review Facts after accept. | Render actionable, human-readable plan with `auto` and `bypass` CTAs plus safe navigation. |
| Workspace routing | `QuotationWorkspaceClient.tsx` | `stage` is initialized once from URL; an `impact` → `content` replacement can leave local state at Facts. | URL is canonical stage state; preserve `stage`, `section`, `focus`, `impactAction`, `lang`, and facts section. |
| Fast Track | `quote-generator/lib/quotationFastTrack.ts` | Generates all drafts and calls `apply-all`; catches media/content failures and continues. | It must not be callable from successor/Impact flow. Either retire it or restrict it to an explicitly separate onboarding feature after contract review. |
| Translation | `routers/v1/translations.py` | Translation exists only in V1 routes and is not a V2 business-version workflow. | English is authoring source; V2 translation becomes a later, reviewed localized-document workflow. |
| E2E | `scripts/test_v2_brochure_workflow.py`, `tests/test_quotation_impact_analysis.py` | No complete predecessor → successor → action plan → draft/bypass coverage. | Add API/browser/Compose evidence with document hashes, request log and outbox records. |

## Current ownership drift

- `QuoteDocumentPricing` already owns editorial fields (`kicker`, `title`, `description`, `ctaLabel`), but registry marks the whole `pricing` scope as Fact-owned.
- `QuoteDocumentHotel.introduction` is currently populated from `service_facts.hotels[].intro`, even though the content budget includes `hotel_plan.hotel_intro`.
- Inclusion/exclusion bullet lists are rendered from Facts. They are commercial/legal commitments and must remain authoritative; Content may own heading/introduction/context copy, not silently rewrite the canonical items.
- `trip.priceBasis` is currently treated as content-owned by helper code but has no complete Content scope contract.

## Legacy retirement list

Do not delete physically in the first rollout; first remove all runtime readers/writers.

- `ImpactAnalysisService` as a field-level Content/Design dependency engine.
- `FactDependency.impact_policy`, `target_paths` and deep-link behavior as impact metadata.
- Design stage rows/filters, `design_count` outbox payloads, and `auto_applied` audit claims.
- `POST /impacts/generate-selected` after its documented compatibility window.
- implicit “apply draft resolves impact” behavior.
- `apply-all` and `quotationFastTrack` from every successor/Impact Center path.
- `_clear_incompatible_day_carry_forward` day-number implementation for new-model quotations.

## Guardrails that remain non-negotiable

1. Facts and required media defaults are created before the successor is visible.
2. AI never writes Facts, Design, pricing values, contractual conditions or canonical inclusion/exclusion items.
3. AI never auto-publishes.
4. External LLM calls are outside a database transaction; persistence after successful generation is atomic and revision-checked.
5. Every execution has a correlation ID, idempotency key, actor audit and transactional outbox event.
