# Sprint 04 — Frontend Impact Center and Content Studio

## Sprint objective & deliverables

Deliver a client-island Actionable Impact Center and Content Studio wiring that makes draft versus bypass explicit, preserves URL state, and never leaks editing logic into public display components.

## Targeted file manifest

- **[MODIFY]** `quote-generator/components/quotation-workspace/ImpactCenter.tsx`
- **[NEW]** `quote-generator/components/quotation-workspace/useContentActionPlan.ts`
- **[NEW]** `quote-generator/components/quotation-workspace/useContentActionExecution.ts`
- **[MODIFY]** `quote-generator/components/quotation-workspace/QuotationWorkspaceClient.tsx`
- **[MODIFY]** `quote-generator/components/quotation-workspace/useQuotationWorkspace.ts`
- **[MODIFY]** `quote-generator/components/content-studio/ContentStudioClient.tsx`
- **[MODIFY]** `quote-generator/components/content-studio/useContentGeneration.ts`
- **[MODIFY]** `quote-generator/components/content-studio/useContentStudioState.ts`
- **[MODIFY]** `quote-generator/lib/quotationFastTrack.ts`
- **[NEW]** `quote-generator/components/quotation-workspace/__tests__/ImpactCenter.test.tsx`
- **[NEW]** `quote-generator/components/content-studio/__tests__/contentActions.test.tsx`

## Typed interfaces & schemas

```ts
type ContentAutomationPolicy = 'manual' | 'auto' | 'bypass';
type ContentActionState = 'pending' | 'draft_created' | 'applied' | 'skipped' | 'failed';

type ContentAction = {
  id: string;
  scope: string;
  entityKey: string;
  policy: ContentAutomationPolicy;
  state: ContentActionState;
  reason: string;
  before: HumanReadableChange | null;
  after: HumanReadableChange | null;
  affectedFields: string[];
  deepLink: { section: string; focus?: string };
};
```

## Step-by-step task breakdown

1. Make URL query state canonical.
   - Derive workspace stage from search params rather than one-time `useState` initialization.
   - Preserve `stage`, `section`, `focus`, `factsSection`, `impactAction`, `lang` and quotation ID in all navigation.
   - Fix immutable quotation edit eligibility without requiring `source.kind === "manual"`.

2. Refactor Impact Center into Actionable Content Plan.
   - Group by semantic change and show human-readable before/after values, preservation decision and affected fields.
   - Render no Design groups, media/map/layout auto-apply claims, raw JSON, or stale impact badges.
   - Checkboxes appear only for actionable `auto`/`bypass` items and selections are scoped by policy.
   - Retry revalidates SWR data; loading/error/empty plan states are accessible and real.

3. Add execution UI.
   - Primary CTA: `Generate review drafts (N)` for selected auto actions.
   - Primary CTA: `Generate & apply selected content (N)` for selected bypass actions; show a confirmation dialog listing exact scope/fields.
   - Tertiary safe navigation: Review Facts and Open Content manually. It performs no generation.
   - After execution, route to Content with first affected scope/focus; bypass refreshes document before route.

4. Extend Content Studio.
   - Display action provenance, draft state and inherited-reference status only while directly relevant to the selected scope; do not show a global Impact banner after leaving the plan.
   - Continue user-controlled individual generation/review/apply.
   - Add pricing editorial, hotel editorial and inclusion/exclusion editorial controls according to policy. Fact values remain read-only previews.
   - Preserve 4-layer reconcilers: no inline date, stay or pricing calculations in handlers.

5. Retire Fast Track coupling.
   - Remove calls to Fast Track, `batch-generate`, or `apply-all` from successor and Impact Center flows.
   - If Fast Track remains for a separate new-quotation product flow, mark it feature-isolated and remove catch-and-continue behavior before it can be enabled for V2 versioning.

6. Meet UI contracts.
   - Use `getTypographyClassName()` for all textual UI.
   - Keep selectors/headless logic in hooks, support keyboard checkbox/dialog controls, and dynamically import heavy Content/Design islands where existing boundary requires it.

## Isolated verification protocol

```bash
cd quote-generator
npm run lint
npm run lint:typography
npm run lint:display-system
npm run build
```

Component acceptance: selecting auto never calls apply; selecting bypass cannot run without confirmation; Review Facts/Open Content cause no AI request; no Impact Center UI is fetched/rendered after leaving `stage=impact`.
