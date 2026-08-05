---
name: quote-generator-typography-ssot
description: Protect quote-generator typography as a single source of truth. Use when creating or changing button text, headings, body copy, labels, nav text, CTA copy, topbar typography, or print typography. Route all text metrics through quote-generator/config/typography.ts and keep app/globals.css limited to chrome, spacing, color, border, and motion.
---

# Quote Generator Typography SSoT

Keep font loading, font roles, text metrics, view-mode overrides, and print
typography under one executable contract. This skill owns both the config and the
component API that consumes it.

## Read First

- Read `quote-generator/docs/typography-contract.md`.
- Read `quote-generator/config/typography.ts`.
- Read `quote-generator/app/fonts.ts`, `quote-generator/app/layout.tsx`, and `quote-generator/app/globals.css` before changing font behavior.
- Read `quote-generator/display/types.ts`, `quote-generator/config/themeTokens.ts`, and `quote-generator/display/themes/brochureTheme.ts` when changing buttons, links, nav, badges, map labels, or any text-bearing component with color.

## Workflow

1. Decide whether an existing semantic variant already fits.
2. If not, add the variant, its class mapping, brand/view-mode overrides, and print behavior in `config/typography.ts` first.
3. Keep font loading in `quote-generator/app/fonts.ts` using the approved `next/font` integration. `app/layout.tsx` attaches its variables; `config/typography.ts` consumes those variables. `globals.css` must not own `@font-face`, raw font aliases, or a second font catalog.
4. Consume the variant through `getTypographyClassName(...)` or an atom whose `variant` is supplied by the section/theme contract. For a text-bearing action, consume the matching `colorRole` from the section's `colorSlots` as a separate contract.
5. Typography-bearing molecules must accept `TypographySlotMap` or an explicit `TypographyVariant` prop. Do not hardcode `variant="cardTitle"`, `variant="bodySm"`, or `typo-body-sm` inside a reusable molecule.
6. Keep `app/globals.css` for shell/chrome, spacing, color, border, and motion only. Remove any `font-size`, `font-weight`, `letter-spacing`, `line-height`, `text-transform`, `font-family`, or `font:` rules that represent content typography.
7. Put typographic measure such as `maxWidth` in the typography rule; do not use `max-w-[ch]` in content JSX.
8. Run the deterministic typography audit, `npm run lint:colors`, project lint, and production build before finishing. A passing utility lint alone is insufficient.

## Hard Guardrails

- Do not add `text-*`, `font-*`, `leading-*`, `tracking-*`, `uppercase`, or `italic` for content typography in `app/` or `components/`.
- Do not import raw typography config into sections to inline styles.
- Do not create a second print-typography source outside `config/typography.ts`.
- Do not add `@font-face`, `--font-*` role aliases, or hardcoded font family names to `globals.css`.
- Do not let a component infer typography from `emphasis`, component name, or breakpoint when a theme slot exists.
- Do not let a component infer color from `emphasis`, component name, or brand key; use `colorRole` inside a validated color scope.
- Do not introduce color literals while fixing typography. Color remains owned by `BrandColorPalette` and `ThemeColorRecipe`.
- Do not accept a dead variant: every new variant needs a consumer and a contract test.

## Completion gate

Before reporting completion, run:

```bash
bash .agents/skills/quote-generator-display-governor/scripts/audit_typography_usage.sh
cd quote-generator && npm run lint:colors
cd quote-generator && npm run lint && npm run build
```

If the audit finds pre-existing violations, report them as blockers instead of
silently treating the task as complete.

## Use References

- Variant map and anti-patterns: `references/typography-rules.md`
- Current typography contract: `references/variant-map.md`
