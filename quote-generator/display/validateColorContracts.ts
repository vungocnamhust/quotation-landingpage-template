import { BRANDS_DATA, type BrandKey } from '../data/brandsData.ts';
import { resolveColorSlots } from '../config/themeTokens.ts';
import { VIEW_MODES } from './contracts.ts';
import { themeRegistry } from './themeRegistry.ts';

export function validateColorContracts() {
  for (const brandKey of Object.keys(BRANDS_DATA) as BrandKey[]) {
    for (const theme of Object.values(themeRegistry)) {
      for (const viewMode of VIEW_MODES) {
        const colors = resolveColorSlots({ brandKey, theme, viewMode });
        if (!colors.page.style['--color-surface'] || !colors.appChrome.style['--color-action-primary-surface']) {
          throw new Error(`Missing resolved color slots for ${brandKey}/${theme.id}/${viewMode}.`);
        }
        for (const sectionId of theme.sectionOrder) {
          if (!colors.sections[sectionId].style['--color-surface']) {
            throw new Error(`Missing section color scope for ${brandKey}/${theme.id}/${viewMode}/${sectionId}.`);
          }
        }
      }
    }
  }
}
