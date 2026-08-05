# Color Contract

## Ownership chain

```text
BrandColorPalette
  -> ThemeColorRecipe
    -> ColorScopeRecipe
      -> ResolvedColorScope
        -> component color role / scoped CSS variables
```

- `data/brandsData.ts` owns opaque `#RRGGBB` palette values only.
- `display/themes/*.ts` owns semantic composition and view-mode adjustments.
- `config/themeTokens.ts` resolves alpha, scrim, border, shadow, action, timeline, and ornament variables server-side.
- `DisplayPage` applies the page and section scopes; `AppTopBar` applies `appChrome`.
- Components consume `colorRole` or `--color-*` variables and never receive raw hex values.

## Required contracts

- Every theme declares `colorRecipe` scopes for `page`, `appChrome`, and all section scopes.
- Every section config declares `colorScope` and `colorSlots` for `desktop`, `mobile`, and `pdf`.
- Button-like components receive both a typography variant and a semantic color role.
- `validateColorContracts()` must resolve every brand/theme/view-mode matrix and enforce contrast for surface text, actions, contrast surfaces, and focus.

## Anti-patterns

- Hex, `rgb(...)`, `rgba(...)`, or color fallbacks in JSX, layout registries, theme CSS, or `globals.css`.
- Reusing a section color scope for app chrome without an explicit theme decision.
- Adding alpha variants to `BrandColorPalette`; alpha belongs to the theme recipe.
- Making a component choose a palette color based on its name, emphasis, breakpoint, or brand key.
