import test from 'node:test';
import assert from 'node:assert/strict';
import { BRANDS_DATA, type BrandKey } from '../../data/brandsData.ts';
import { resolveColorSlots, getContrastRatio } from '../../config/themeTokens.ts';
import { VIEW_MODES } from '../../display/contracts.ts';
import { themeRegistry } from '../../display/themeRegistry.ts';
import { buildDisplayDocumentFromQuoteDocument } from '../../display/runtimePageBuilder.ts';

test('validateColorContracts resolves valid tokens for all brands and view modes', () => {
  for (const brandKey of Object.keys(BRANDS_DATA) as BrandKey[]) {
    for (const theme of Object.values(themeRegistry)) {
      for (const viewMode of VIEW_MODES) {
        const colors = resolveColorSlots({ brandKey, theme, viewMode });
        assert.ok(colors.page.style['--color-surface'], `Missing page surface for ${brandKey}/${theme.id}/${viewMode}`);
        assert.ok(colors.appChrome.style['--color-action-primary-surface'], `Missing action surface for ${brandKey}/${theme.id}/${viewMode}`);
        assert.ok(colors.page.style['--color-accent-text'], `Missing accent-text for ${brandKey}/${theme.id}/${viewMode}`);
        assert.ok(colors.page.style['--color-on-accent'], `Missing on-accent for ${brandKey}/${theme.id}/${viewMode}`);

        for (const sectionId of theme.sectionOrder) {
          const sectionColors = colors.sections[sectionId];
          assert.ok(sectionColors.style['--color-surface'], `Missing section color scope for ${brandKey}/${theme.id}/${viewMode}/${sectionId}`);
          assert.ok(sectionColors.style['--color-accent-text'], `Missing section accent-text for ${brandKey}/${theme.id}/${viewMode}/${sectionId}`);
        }

        // On PDF print mode, pricing section MUST use paper surface and ink text for clean printing
        if (viewMode === 'pdf') {
          const pricingColors = colors.sections.pricing;
          const p = BRANDS_DATA[brandKey].themeTokens.palette;
          assert.equal(pricingColors.style['--color-surface'], p.paper, `${brandKey} PDF pricing surface must be paper`);
          assert.equal(pricingColors.style['--color-on-surface'], p.ink, `${brandKey} PDF pricing text must be ink`);
        }
      }
    }
  }
});

test('BrandColorPalette meets WCAG 2.1 AA contrast requirements', () => {
  for (const [brandKey, brand] of Object.entries(BRANDS_DATA)) {
    const p = brand.themeTokens.palette;
    
    // 1. Normal body text on canvas >= 4.5:1
    const inkCanvasRatio = getContrastRatio(p.ink, p.canvas);
    assert.ok(inkCanvasRatio >= 4.5, `${brandKey}: ink on canvas contrast is ${inkCanvasRatio.toFixed(2)} (required >= 4.5)`);
    
    // 2. Muted text on canvas >= 4.5:1
    const mutedCanvasRatio = getContrastRatio(p.mutedInk, p.canvas);
    assert.ok(mutedCanvasRatio >= 4.5, `${brandKey}: mutedInk on canvas contrast is ${mutedCanvasRatio.toFixed(2)} (required >= 4.5)`);
    
    // 3. Contrast text on contrast surface >= 4.5:1
    const contrastRatio = getContrastRatio(p.onContrast, p.contrast);
    assert.ok(contrastRatio >= 4.5, `${brandKey}: onContrast on contrast is ${contrastRatio.toFixed(2)} (required >= 4.5)`);
    
    // 4. Story contrast text on storyContrast surface >= 4.5:1
    const storyContrastRatio = getContrastRatio(p.onContrast, p.storyContrast);
    assert.ok(storyContrastRatio >= 4.5, `${brandKey}: onContrast on storyContrast is ${storyContrastRatio.toFixed(2)} (required >= 4.5)`);
    
    // 5. Investment text on investmentSurface >= 4.5:1
    const investmentRatio = getContrastRatio(p.investmentText, p.investmentSurface);
    assert.ok(investmentRatio >= 4.5, `${brandKey}: investmentText on investmentSurface is ${investmentRatio.toFixed(2)} (required >= 4.5)`);
    
    // 6. Action contrast (either ink or onContrast on accent >= 4.5:1)
    const actionContrast = Math.max(getContrastRatio(p.ink, p.accent), getContrastRatio(p.onContrast, p.accent));
    assert.ok(actionContrast >= 4.5, `${brandKey}: primary action contrast is ${actionContrast.toFixed(2)} (required >= 4.5)`);
    
    // 7. Focus ring on canvas >= 3.0:1
    const focusRatio = getContrastRatio(p.focus, p.canvas);
    assert.ok(focusRatio >= 3.0, `${brandKey}: focus ring on canvas is ${focusRatio.toFixed(2)} (required >= 3.0)`);
  }
});

test('normalizeBrandRenderProfile protects against legacy muddy mustard snapshots', () => {
  const legacySelvaraProfile = {
    id: 'selvara',
    displayName: 'Selvara Journeys',
    hostname: 'my.selvarajourneys.com',
    logoUrl: '/assets/brands/selvara.svg',
    palette: {
      canvas: '#f9f6f0',
      paper: '#f9f6f0',
      ink: '#11130f',
      mutedInk: '#2c2a29',
      accent: '#a98338',
      accentAlt: '#a98338',
      contrast: '#524018',
      onContrast: '#ffffff',
      focus: '#7a591a',
      storyContrast: '#17412e',
      investmentSurface: '#a98338', // Old muddy mustard
      investmentText: '#11130f',    // Old black ink on mustard
    },
    radii: { card: '0.5rem', button: '0.375rem', frame: '0.625rem', pill: '999px' },
  };

  const doc = buildDisplayDocumentFromQuoteDocument({
    document: {},
    brandProfile: legacySelvaraProfile,
    lang: 'en',
    viewMode: 'desktop',
  });

  // Safety normalizer guard must normalize investmentSurface to safe contrast (#524018) and text to #ffffff
  assert.equal(doc.tokens.palette.investmentSurface, '#524018');
  assert.equal(doc.tokens.palette.investmentText, '#ffffff');
});
