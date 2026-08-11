import { BRANDS_DATA, type BrandKey } from '../data/brandsData';
import type {
  BrandColorPalette,
  BrandRenderProfile,
  BrandThemeTokens,
  ColorReference,
  ColorScopeRecipe,
  ResolvedColorScope,
  ResolvedColorSlots,
  ThemeDefinition,
} from '../display/types';
import type { ViewMode } from '../display/contracts';

function assert(condition: unknown, message: string): asserts condition {
  if (!condition)
  {
    throw new Error(message);
  }
}

function parseHex(hex: string) {
  assert(/^#[0-9a-fA-F]{6}$/.test(hex), `Brand palette value "${hex}" must be an opaque #RRGGBB color.`);
  return {
    r: Number.parseInt(hex.slice(1, 3), 16),
    g: Number.parseInt(hex.slice(3, 5), 16),
    b: Number.parseInt(hex.slice(5, 7), 16),
  };
}

function withOpacity(hex: string, opacity: number) {
  assert(opacity >= 0 && opacity <= 1, `Color opacity "${opacity}" must be between 0 and 1.`);
  const { r, g, b } = parseHex(hex);
  return `rgb(${r} ${g} ${b} / ${opacity})`;
}

function resolveReference(palette: BrandColorPalette, reference: ColorReference) {
  return reference === 'transparent' ? 'transparent' : palette[reference];
}

function relativeLuminance(hex: string) {
  const { r, g, b } = parseHex(hex);
  const channels = [r, g, b].map((channel) => {
    const normalized = channel / 255;
    return normalized <= 0.03928
      ? normalized / 12.92
      : ((normalized + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * channels[0]! + 0.7152 * channels[1]! + 0.0722 * channels[2]!;
}

export function getContrastRatio(foreground: string, background: string) {
  const lighter = Math.max(relativeLuminance(foreground), relativeLuminance(background));
  const darker = Math.min(relativeLuminance(foreground), relativeLuminance(background));
  return (lighter + 0.05) / (darker + 0.05);
}

function assertContrast(
  foreground: ColorReference,
  background: ColorReference,
  palette: BrandColorPalette,
  label: string,
  minimum: number
) {
  if (foreground === 'transparent' || background === 'transparent')
  {
    return;
  }
  const ratio = getContrastRatio(palette[foreground], palette[background]);
  assert(ratio >= minimum, `${label} contrast is ${ratio.toFixed(2)}:1; required minimum is ${minimum}:1.`);
}

function mergeRecipe(recipe: ColorScopeRecipe, viewMode: ViewMode): ColorScopeRecipe {
  const adjustment = recipe.viewModeAdjustments?.[viewMode];
  if (!adjustment)
  {
    return recipe;
  }
  return {
    ...recipe,
    ...adjustment,
    viewModeAdjustments: recipe.viewModeAdjustments,
  };
}

function resolveScope({
  id,
  palette,
  recipe,
  viewMode,
  tokens,
}: {
  id: ResolvedColorScope['id'];
  palette: BrandColorPalette;
  recipe: ColorScopeRecipe;
  viewMode: ViewMode;
  tokens: BrandThemeTokens;
}): ResolvedColorScope {
  const resolved = mergeRecipe(recipe, viewMode);
  const primary = resolved.action.primary;
  const secondary = resolved.action.secondary;
  const focus = resolved.surface === 'contrast' || resolved.surface === 'accent' || resolved.surface === 'storyContrast' ? 'onContrast' : resolved.surface === 'investmentSurface' ? 'investmentText' : 'focus';

  const primarySurfaceHex = primary.surface === 'transparent' ? 'transparent' : palette[primary.surface];
  const preferredTextRef = primary.text;
  const primaryTextRef =
    primarySurfaceHex === 'transparent' || preferredTextRef === 'transparent' || getContrastRatio(palette[preferredTextRef], primarySurfaceHex) >= 4.5
      ? preferredTextRef
      : getContrastRatio(palette.onContrast, primarySurfaceHex) >= getContrastRatio(palette.ink, primarySurfaceHex)
        ? 'onContrast'
        : 'ink';

  assertContrast(resolved.onSurface, resolved.surface, palette, `${id} surface text`, 4.5);
  assertContrast(primaryTextRef, primary.surface, palette, `${id} primary action`, 4.5);
  assertContrast('onContrast', 'contrast', palette, `${id} contrast text`, 4.5);
  assertContrast(focus, resolved.surface, palette, `${id} focus ring`, 3);

  return {
    id,
    style: {
      '--color-surface': resolveReference(palette, resolved.surface),
      '--color-surface-white': '#faf9f8',
      '--color-paper': palette.paper,
      '--color-card': palette.paper,
      '--color-surface-muted': palette.canvas,
      '--color-on-surface': resolveReference(palette, resolved.onSurface),
      '--color-muted': resolveReference(palette, resolved.muted),
      '--color-accent': resolveReference(palette, resolved.accent),
      '--color-accent-alt': resolveReference(palette, resolved.accentAlt),
      '--color-contrast': palette.contrast,
      '--color-on-contrast': palette.onContrast,
      '--color-accent-wash': withOpacity(palette.accent, 0.1),
      '--color-border': withOpacity(palette[resolved.border.color], resolved.border.opacity),
      '--color-border-strong': withOpacity(palette[resolved.strongBorder.color], resolved.strongBorder.opacity),
      '--color-action-primary-surface': resolveReference(palette, primary.surface),
      '--color-action-primary-text': resolveReference(palette, primaryTextRef),
      '--color-action-primary-border': withOpacity(palette[primary.border.color], primary.border.opacity),
      '--color-action-secondary-surface': resolveReference(palette, secondary.surface),
      '--color-action-secondary-text': resolveReference(palette, secondary.text),
      '--color-action-secondary-border': withOpacity(palette[secondary.border.color], secondary.border.opacity),
      '--color-focus': resolveReference(palette, focus),
      '--color-map-surface': resolveReference(palette, resolved.surface),
      '--color-map-route': palette[resolved.timeline.route],
      '--color-map-marker': palette[(resolved.timeline.marker === 'contrast' || resolved.timeline.marker === 'storyContrast' || resolved.timeline.marker === 'ink' || resolved.timeline.marker === 'investmentSurface') ? 'accent' : resolved.timeline.marker],
      '--color-map-marker-active': palette[(resolved.timeline.active === 'contrast' || resolved.timeline.active === 'storyContrast' || resolved.timeline.active === 'ink' || resolved.timeline.active === 'investmentSurface') ? 'accentAlt' : resolved.timeline.active],
      '--color-overlay-start': resolved.overlay
        ? withOpacity(palette[resolved.overlay.start.color], resolved.overlay.start.opacity)
        : 'transparent',
      '--color-overlay-end': resolved.overlay
        ? withOpacity(palette[resolved.overlay.end.color], resolved.overlay.end.opacity)
        : 'transparent',
      '--color-shadow': withOpacity(palette[resolved.shadow.color], resolved.shadow.opacity),
      '--color-ornament': resolved.accent === 'transparent'
        ? 'transparent'
        : withOpacity(palette[resolved.accent], resolved.ornamentOpacity),
      '--radius-card': tokens.radii.card,
      '--radius-button': tokens.radii.button,
      '--radius-frame': tokens.radii.frame,
      '--radius-pill': tokens.radii.pill,
      '--elevation-card': `0 20px 45px -16px ${withOpacity(palette[resolved.shadow.color], resolved.shadow.opacity)}`,
      '--ornament-opacity': String(resolved.ornamentOpacity),
    },
  };
}

export function getBrandThemeTokens(brandKey: BrandKey): BrandThemeTokens {
  return {
    brandKey,
    themeId: 'brochure',
    ...BRANDS_DATA[brandKey].themeTokens,
  };
}

export function getBrandThemeTokensFromProfile(profile: BrandRenderProfile): BrandThemeTokens {
  return {
    brandKey: profile.id,
    themeId: profile.themeId ?? 'brochure',
    palette: profile.palette,
    radii: profile.radii,
  };
}

export function resolveColorSlots({
  brandKey,
  theme,
  viewMode,
}: {
  brandKey: BrandKey;
  theme: ThemeDefinition;
  viewMode: ViewMode;
}): ResolvedColorSlots {
  const tokens = getBrandThemeTokens(brandKey);
  const palette = tokens.palette;
  const resolve = (scopeId: ResolvedColorScope['id']) => {
    const recipe = theme.colorRecipe.scopes[scopeId];
    assert(recipe, `Theme "${theme.id}" is missing color scope "${scopeId}".`);
    return resolveScope({ id: scopeId, palette, recipe, viewMode, tokens });
  };

  return {
    page: resolve('page'),
    appChrome: resolve('appChrome'),
    sections: Object.fromEntries(
      theme.sectionOrder.map((sectionId) => [
        sectionId,
        resolve(
          theme.sectionConfigs[sectionId][viewMode].brandColorScopes?.[brandKey]
          ?? theme.sectionConfigs[sectionId][viewMode].colorScope
        ),
      ])
    ) as ResolvedColorSlots['sections'],
  };
}

/** Production V2 entrypoint: tokens originate from the backend brand SSoT. */
export function resolveColorSlotsFromProfile({
  profile,
  theme,
  viewMode,
}: {
  profile: BrandRenderProfile;
  theme: ThemeDefinition;
  viewMode: ViewMode;
}): ResolvedColorSlots {
  const tokens = getBrandThemeTokensFromProfile(profile);
  const palette = tokens.palette;
  const resolve = (scopeId: ResolvedColorScope['id']) => {
    const recipe = theme.colorRecipe.scopes[scopeId];
    assert(recipe, `Theme "${theme.id}" is missing color scope "${scopeId}".`);
    return resolveScope({ id: scopeId, palette, recipe, viewMode, tokens });
  };

  return {
    page: resolve('page'),
    appChrome: resolve('appChrome'),
    sections: Object.fromEntries(
      theme.sectionOrder.map((sectionId) => [
        sectionId,
        resolve(
          theme.sectionConfigs[sectionId][viewMode].brandColorScopes?.[profile.id]
          ?? theme.sectionConfigs[sectionId][viewMode].colorScope
        ),
      ])
    ) as ResolvedColorSlots['sections'],
  };
}
