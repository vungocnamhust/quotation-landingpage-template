import { brochureTheme } from './themes/brochureTheme';
import type { ThemeDefinition } from './types';
import type { ThemeId } from './contracts';
import { validateThemeDefinition } from './validateTheme';

export const themeRegistry: Record<ThemeId, ThemeDefinition> = {
  brochure: validateThemeDefinition(brochureTheme),
};

export function getThemeDefinition(themeId: ThemeId) {
  return themeRegistry[themeId];
}
