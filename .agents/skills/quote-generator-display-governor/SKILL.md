---
name: quote-generator-display-governor
description: Govern display-system work in quote-generator. Use when requests mention quote-generator, brochure theme, section, layout, theme, desktop/mobile/pdf view modes, homepage composition, or display-system refactors. Enforce the 5-layer contract from theme through view mode, layout system, component system, and section view model, keep scope to public landing and state screens, and block editor or tooling concerns from leaking into display core.
---

# Quote Generator Display Governor

This is the entry skill for every `quote-generator` display change. It coordinates
the typography, section-builder, and parity-review skills; it is not a replacement
for their checks.

## Read First

- Read `quote-generator/docs/display-system-contract.md`.
- Read `quote-generator/docs/typography-contract.md` for any text-bearing change.
- Read `quote-generator/AGENTS.md`.
- Read `quote-generator/display/types.ts` when changing public contracts.
- Read `quote-generator/config/themeTokens.ts`, `quote-generator/display/validateColorContracts.ts`, and `quote-generator/scripts/lint-colors.mjs` for any color, button, surface, shell, map, or app-chrome change.

## Workflow

1. Classify the request into one or more layers: `theme`, `view mode`, `layout`, `component`, `section view model`.
2. Confirm the public scope. Exclude `data-editable`, template switch modal, PWA prompts, version checker, publish bars, notifications, or editor overlays unless the user explicitly changes app chrome.
3. For typography, invoke `quote-generator-typography-ssot` before editing JSX or CSS.
4. For section/layout work, invoke `quote-generator-section-builder` before editing renderers.
5. For color, button, surface, shell, map, or app-chrome work, follow the color ownership chain:
   `BrandColorPalette -> ThemeColorRecipe -> ColorScopeRecipe -> ResolvedColorScope -> component render`.
   Never skip the resolver by adding a hex, rgba, or component color prop.
6. Follow the dependency order:
   - Change `display/types.ts` before JSX when contracts move.
   - Change `data/brandsData.ts` only for opaque brand palette values.
   - Change `config/themeTokens.ts` and `display/validateColorContracts.ts` when color resolution or contrast rules move.
   - Change `display/pageBuilder.ts` before sections when data or resolved display inputs move.
   - Change `display/themes/*.ts` and registries before layout-specific CSS when composition or color scopes move.
7. Keep sections pure: consume only `viewModel + displayConfig + tokens + theme + viewMode + colorScope`.
8. Run the post-edit gate before finishing:
   - `bash .agents/skills/quote-generator-display-governor/scripts/audit_display_contract.sh`
   - `bash .agents/skills/quote-generator-display-governor/scripts/audit_typography_usage.sh`
   - `bash .agents/skills/quote-generator-display-governor/scripts/check_section_boundaries.sh`
   - `cd quote-generator && npm run lint && npm run build`
9. If any gate fails, report the failure and keep working. Do not declare the task complete with a lint-only pass.

## Hard Guardrails

- Do not let public sections read `useBrand()` directly.
- Do not let public sections import `BRANDS_DATA` directly.
- Do not reintroduce `no-print` or `no-screen`; use `visibilityByViewMode`.
- Do not bypass the builder with raw flat template fields in JSX.
- Brand owns only opaque palette values. Theme owns alpha, scrim, border, shadow, action, timeline, and view-mode color composition.
- Every rendered section must use a validated `colorScope`; every color-bearing component must consume semantic `colorRole` or scoped `--color-*` variables.
- Do not add color fallbacks, legacy color variables, hex, rgba, or raw color props in renderers, layout registries, or `globals.css`.
- App chrome uses the theme's `appChrome` scope; it must not silently reuse a section scope.
- Do not let `globals.css` become a typography source. Font loading and all text metrics must have an explicit owner in the typography contract.
- Typography-bearing molecules must receive their semantic slots from `displayConfig.typographySlots`; they must not invent variants or silently fall back to generic variants.
- Text-bearing actions must receive both a typography variant and a semantic color role; emphasis alone is not a color contract.
- A declared theme typography slot is not compliant until a runtime component consumes it.

## Use References

- For architecture and anti-patterns: `references/display-governor.md`
- For color ownership and contrast: `references/color-contract.md`
- For file ownership and change order: `references/file-map.md`
- For deterministic checks: `scripts/audit_display_contract.sh`, `scripts/audit_typography_usage.sh`, `scripts/check_section_boundaries.sh`
