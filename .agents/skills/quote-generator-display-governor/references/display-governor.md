# Display Governor Notes

## Public scope

- In scope: brochure homepage, public sections, loading/error/not-found, `desktop`, `mobile`, `pdf`.
- Out of scope by default: `data-editable`, template switch modal, PWA prompts, publish bars, version checkers, notification overlays, editor diagnostics.

## Anti-patterns

- Editing JSX before deciding whether the change belongs in `display/types.ts`, `pageBuilder.ts`, or theme config.
- Treating a theme as colors only instead of section order + layout composition + shell rules.
- Solving responsive drift with random CSS overrides instead of explicit view-mode behavior.

## Required checks

- Theme/view-mode contract stays valid.
- Section ownership stays inside builder + theme + section renderer boundaries.
- Typography stays in semantic classes and has one font-loading owner.
- Typography-bearing molecules consume theme slots instead of inventing variants.
- Brand palette, theme color recipe, resolved color scope, and component color role remain separate owners.
- Every brand/theme/view-mode combination passes color resolution and contrast validation.
- Run the bundled typography audit; `npm run lint:typography` alone is not sufficient.
- Run `npm run lint:colors`; color lint is required for any display or button change.
- A task is incomplete when any post-edit gate fails, even if the visual result looks correct.
