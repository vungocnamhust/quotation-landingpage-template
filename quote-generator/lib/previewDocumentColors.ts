import { resolveColorSlotsFromProfile } from '../config/runtimeThemeTokens.ts';
import type { ViewMode } from '../display/contracts.ts';
import { textValue } from '../display/types.ts';
import type { DisplayDocument } from '../display/runtimePageBuilder.ts';

/**
 * Preview documents can arrive with a persisted color snapshot from an older
 * renderer. Resolve the current theme contract for every preview view mode so
 * newly introduced semantic tokens are never silently omitted.
 */
export function resolvePreviewDocumentForViewMode(
  documentModel: DisplayDocument,
  viewMode: ViewMode,
): DisplayDocument {
  const colors = resolveColorSlotsFromProfile({
    profile: {
      id: documentModel.tokens.brandKey,
      displayName: textValue(documentModel.page.nav.brandName) || documentModel.tokens.brandKey,
      hostname: '',
      logoUrl: documentModel.page.nav.brandLogoSrc || '',
      themeId: documentModel.theme.id,
      palette: documentModel.tokens.palette,
      radii: documentModel.tokens.radii,
    },
    theme: documentModel.theme,
    viewMode,
  });

  return {
    ...documentModel,
    viewMode,
    colors,
  };
}
