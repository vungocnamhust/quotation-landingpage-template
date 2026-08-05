---
name: quote-generator-section-builder
description: Build or refactor quote-generator sections, layouts, and section-facing components. Use when adding a new section, rebuilding a brochure section, changing layout composition, wiring section data, or introducing a new layout variant. Keep work inside PageViewModel, SectionDisplayConfig, theme, and view-mode contracts rather than ad-hoc JSX composition.
---

# Quote Generator Section Builder

Build sections through contracts, not shortcuts. A section contract includes its
typography ownership, not only its data and layout.

## Read First

- Read `quote-generator/docs/display-system-contract.md`.
- Read `quote-generator/display/pageBuilder.ts`.
- Read `quote-generator/display/themes/brochureTheme.ts`.
- Read `quote-generator/display/layoutRegistry.ts`.
- Read `quote-generator/config/themeTokens.ts` and `quote-generator/display/validateColorContracts.ts` when the section changes color, surfaces, actions, map markers, ornaments, or PDF treatment.

## Workflow

1. Identify the affected section and target view modes.
2. Update `PageViewModel` or section view model types in `display/types.ts` before rendering if data shape changes.
3. Map content in `display/pageBuilder.ts`.
4. Update theme orchestration and layout slots before touching section JSX.
5. Define both ownership maps before touching section JSX:
   - `typographySlots` for text metrics.
   - `colorScope` and `colorSlots` for color semantics.
6. Rebuild section renderers in `components/display/` as thin orchestrators. Pass the resolved `colorScope`; do not pass raw color values.
7. Verify responsive and pdf behavior explicitly, including the color scope and contrast changes for each mode.
8. Run the display, typography, and color contract audits; do not rely on the normal utility lint alone.

## Hard Guardrails

- Do not let sections read `BRANDS_DATA` or `useBrand()` directly.
- Do not hardcode breakpoint strategy in a section when it belongs in theme/layout config.
- Do not reuse generic card/panel abstractions if they break brochure composition.
- Do not create typography-bearing molecules with hidden defaults. Pass `TypographySlotMap` or an explicit `TypographyVariant` from the section renderer.
- Do not let a molecule bypass `displayConfig.typographySlots` with literal variant names or fixed `typo-*` classes.
- Do not let a section or molecule bypass `displayConfig.colorScope` with hex, rgba, CSS fallbacks, or a brand-key conditional.
- Button/link/map/marker components must receive a semantic `colorRole` and render inside the validated scope.
- Do not add a theme typography slot unless the section/component tree consumes it in desktop, mobile, and pdf paths as applicable.
- Do not add a theme color slot unless the section/component tree consumes it in desktop, mobile, and pdf paths as applicable.
- If a component needs a new text measure such as max width, add it to the typography contract before adding JSX classes.

## Use References

- Change order and ownership: `references/build-flow.md`
- Color ownership: `.agents/skills/quote-generator-display-governor/references/color-contract.md`
- Section and file map: `references/file-map.md`
