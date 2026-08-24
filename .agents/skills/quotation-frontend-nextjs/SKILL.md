---
name: quotation-frontend-nextjs
description: Govern quote-generator frontend work (Next.js 16 App Router, React 19, Tailwind v4, port 8115). Use when editing anything under quote-generator/ - pages, workspace forms, content studio, display sections, lib/rules reconcilers, API clients, or proxy.ts. Routes the work to the right specialist governor, enforces RSC-first boundaries, the 4-layer reconciler contract, Typography SSOT, and the full lint gate.
---

# Quote Generator Frontend Governor

Router skill for `quote-generator/`. It decides which specialist governor owns
the change and enforces the gates none of them can skip.

## Stack Facts (verify before trusting memory)

- `next@16.2.12`, `react@19.2.4`, Tailwind v4 via `@tailwindcss/postcss`, `output: 'standalone'`.
- Interception/auth/rewrite logic lives in `quote-generator/proxy.ts` (Next 16 name),
  **not** `middleware.ts`. Do not create `middleware.ts`.
- `next.config.ts` rewrites `/api/v1/*` to the FastAPI backend
  (`QUOTATION_INTERNAL_API_URL` → `NEXT_PUBLIC_QUOTATION_API_URL` → `http://localhost:8111`).
  V2 calls go through `lib/quotationApi.ts` / `lib/publicQuotationApi.ts`; do not
  hardcode a backend origin in a component.
- Tests are `node --test` + `--experimental-strip-types` over `lib/__tests__/*.test.ts`.
  There is no Jest/Vitest — write plain `node:test` + `node:assert` files.

## Route The Request

| Request touches | Invoke first |
| :-- | :-- |
| brochure theme, view modes, layout, colors, section composition | `quote-generator-display-governor` |
| a new/rebuilt brochure section or layout variant | `quote-generator-section-builder` |
| any text metric (size, weight, tracking, leading) | `quote-generator-typography-ssot` |
| form fields, defaults, dates/nights, pricing, party labels, stays | `quote-generator-prefill-governor` |
| a new selector/picker/modal or duplicated input control | `react-component-reuse-governor` |
| drift vs `templates/prototype_itinerary_imagery*.html` | `quote-generator-parity-review` |

If two apply, invoke both before editing. This skill does not replace their checks.

## Non-Negotiables

1. **RSC-first.** Pages under `app/` stay async Server Components. Add `"use client"`
   only for real DOM interaction/state. Wrap Leaflet maps, TipTap editors, and
   drawer/modal stacks in `dynamic(..., { ssr: false })` (see `RouteMapClientIsland.tsx`).
   Load independent server data with `Promise.all`, never sequential awaits.
2. **No derived state in `useEffect`.** Compute during render, or call a pure
   function from `lib/rules/*`. A `useEffect` that mirrors one state into another
   is a defect in this codebase.
3. **4-layer reconciler contract.** Domain math never lives in an event handler:
   `lib/rules/*Reconciler.ts` (pure) ↔ `lib/rules/*Adapter.ts` (shape bridge) ↔
   `lib/prefillEngine.ts` / hooks (single-pass state update) ↔ React UI (one call).
   Reconcilers in play: `tripReconciler`, `staysReconciler`, `pricingReconciler`,
   `partyReconciler`, `presentationReconciler`, `contentReconciler`, `workflowReconciler`.
   Adding domain math means adding/extending a reconciler **plus** its
   `lib/__tests__/*Reconciler.test.ts` case in the same change.
4. **Typography SSOT.** Only `typo-*` classes from `config/typography.ts` in
   brochure/display code. No `text-*`, `font-*`, `tracking-*`, `leading-*` there.
5. **Display isolation.** `components/display/**` consumes only
   `viewModel + displayConfig + tokens + theme + viewMode + colorScope`.
   Never import `workspace/`, `content-studio/`, or editor tooling into it, or vice versa.
6. **Colors through the resolver.** No raw hex/rgba in components; go through
   `config/themeTokens.ts` → resolved color scope.
7. **Keys and lists.** `key={item.id}`/`key={item.code}` in any list that can be
   reordered, added to, or removed from. Never `key={index}`.
8. **Optimistic concurrency.** Mutations send `baseRevision`; on a 409
   `REVISION_CONFLICT` surface the reload recovery path instead of retrying blind.
9. **File size.** Split past ~400 lines; hard ceiling 500 for a component.
   Decompose into atoms/molecules/sections.

## Post-Edit Gate (all of it)

```bash
cd quote-generator && npm run lint && npm test && npm run build
```

`npm run lint` chains eslint + `lint:typography` + `lint:typography-contract` +
`lint:display-system` + `lint:colors` + `lint:v2-runtime-imports`. A green eslint
alone is not a pass. If a gate fails, fix it — do not report completion.
