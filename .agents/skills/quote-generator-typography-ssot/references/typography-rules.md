# Typography Rules

## Source of truth

- Define metrics in `quote-generator/config/typography.ts`.
- Keep font loading and role aliases in the declared typography owner; do not duplicate them in `app/globals.css`.
- Consume them through `typo-*` classes or `getTypographyClassName(...)`.
- Keep `quote-generator/app/globals.css` for chrome only.
- Color is a separate contract: use the resolved section/app-chrome color scope and semantic `colorRole`; do not encode color into typography variants.

## Forbidden shortcuts

- `text-*`
- `font-*`
- `leading-*`
- `tracking-*`
- raw `uppercase` or `italic` for content typography
- `@font-face`, raw `font-family`, `font:`, or `--font-*` aliases in `globals.css`
- `max-w-[ch]` for content measure
- fixed typography variants inside reusable molecules
- raw color props or color literals added to typography-bearing components

## Decision rule

- Reuse a semantic role when the meaning is the same.
- Add a variant only when semantics truly differ, not because one screen wants a slightly different look.
- Pass the chosen variant from the theme/section slot map into typography-bearing atoms and molecules.
- A new variant is valid only when it has a runtime consumer and a contract test.
