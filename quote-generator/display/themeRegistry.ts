import { brochureTheme } from './themes/brochureTheme.ts';
import type { ThemeDefinition } from './types.ts';
import type { ThemeId } from './contracts.ts';
import { validateThemeDefinition } from './validateTheme.ts';

export const themeRegistry: Record<ThemeId, ThemeDefinition> = {
  brochure: validateThemeDefinition(brochureTheme),
};

export function getThemeDefinition(themeId: ThemeId) {
  return themeRegistry[themeId];
}
