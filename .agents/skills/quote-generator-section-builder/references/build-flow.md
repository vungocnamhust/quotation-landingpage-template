# Section Build Flow

1. Update `display/types.ts` if section or item shape changes.
2. Update `display/pageBuilder.ts` to map raw content into the section view model.
3. Update `display/themes/brochureTheme.ts` and registries if layout, shell, spacing, or visibility changes.
4. Define typography slot ownership and color scope/slot ownership before rebuilding atoms or molecules.
5. Rebuild `components/display/sections.tsx` or molecules as thin renderers inside the resolved color scope.
6. Verify `desktop`, `mobile`, and `pdf`, including contrast and app-chrome scope where relevant.
7. Run the bundled display, typography, and color contract audits.

Do not start by patching JSX blindly.
