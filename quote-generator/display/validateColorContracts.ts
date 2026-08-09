import { BRANDS_DATA, type BrandKey } from '../data/brandsData';
import { resolveColorSlots } from '../config/themeTokens';
import { VIEW_MODES } from './contracts';
import { themeRegistry } from './themeRegistry';

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
