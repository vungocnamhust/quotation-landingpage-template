import test from 'node:test';
import assert from 'node:assert/strict';
import { BRANDS_DATA } from '../../data/brandsData.ts';
import { buildDisplayDocumentFromQuoteDocument } from '../../display/runtimePageBuilder.ts';
import { resolvePreviewDocumentForViewMode } from '../previewDocumentColors.ts';

test('preview always refreshes route-map tokens instead of trusting a persisted color snapshot', () => {
  const selvara = BRANDS_DATA.selvara;
  const documentModel = buildDisplayDocumentFromQuoteDocument({
    document: {},
    brandProfile: {
      id: 'selvara',
      displayName: selvara.name,
      hostname: 'preview.selvara.test',
      logoUrl: '/assets/brands/selvara.svg',
      themeId: 'brochure',
      palette: selvara.themeTokens.palette,
      radii: selvara.themeTokens.radii,
    },
    lang: 'en',
    viewMode: 'desktop',
  });
  const staleDocument = {
    ...documentModel,
    colors: {
      ...documentModel.colors,
      sections: {
        ...documentModel.colors.sections,
        routeMap: {
          ...documentModel.colors.sections.routeMap,
          style: {
            ...documentModel.colors.sections.routeMap.style,
            '--filter-map-tiles': undefined,
            '--color-map-canvas-veil': undefined,
          },
        },
      },
    },
  };

  const desktop = resolvePreviewDocumentForViewMode(staleDocument, 'desktop');
  const pdf = resolvePreviewDocumentForViewMode(staleDocument, 'pdf');

  assert.equal(
    desktop.colors.sections.routeMap.style['--filter-map-tiles'],
    'sepia(0.7) hue-rotate(-10deg) saturate(0.4) contrast(1.05) brightness(0.98)',
  );
  assert.equal(pdf.colors.sections.routeMap.style['--filter-map-tiles'], 'none');
  assert.ok(desktop.colors.sections.routeMap.style['--color-map-canvas-veil']);
});
