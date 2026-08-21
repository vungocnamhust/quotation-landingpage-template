import type { ThemeId, ViewMode } from '../display/contracts';
import type { BrandKey } from '../data/brandsData';

export type FontFamilyRole = 'heading' | 'body' | 'accent';

export type TypographyVariant =
  | 'hero'
  | 'sectionTitle'
  | 'cardTitle'
  | 'bodyLg'
  | 'bodyMd'
  | 'bodySm'
  | 'caption'
  | 'overline'
  | 'label'
  | 'price'
  | 'quote'
  | 'buttonPrimary'
  | 'buttonSecondary'
  | 'topbarSelectValue'
  | 'topbarActionValue'
  | 'topbarBrandName'
  | 'topbarSectionLink'
  | 'navTitle'
  | 'navMeta'
  | 'pageTitle'
  | 'chapterKicker'
  | 'chapterTitle'
  | 'heroLede'
  | 'heroMetaPrimary'
  | 'heroMetaSecondary'
  | 'letterTitle'
  | 'letterHighlight'
  | 'letterBody'
  | 'signatureName'
  | 'signatureMeta'
  | 'routeMapTitle'
  | 'routeMapBody'
  | 'timelineTitle'
  | 'timelineMeta'
  | 'dayTitle'
  | 'dayBody'
  | 'hotelTitle'
  | 'hotelMeta'
  | 'hotelBody'
  | 'investmentTitle'
  | 'investmentValue'
  | 'investmentMeta'
  | 'termTitle'
  | 'termLabel'
  | 'termBody'
  | 'designerTitle'
  | 'designerQuote'
  | 'footerText'
  | 'stateTitle';

export interface TypographyRule {
  fontFamilyRole: FontFamilyRole;
  fontSize: string;
  lineHeight: string;
  fontWeight: number | string;
  letterSpacing: string;
  textTransform?: 'uppercase' | 'lowercase' | 'capitalize' | 'none';
  fontStyle?: 'normal' | 'italic';
  maxWidth?: string;
}

interface FontDefinition {
  label: string;
  cssValue: string;
}

export interface BrandTypographyConfig {
  fonts: Record<FontFamilyRole, FontDefinition>;
  variants: Record<TypographyVariant, TypographyRule>;
}

interface TypographyContext {
  brandKey: BrandKey;
  themeId: ThemeId;
  viewMode: ViewMode;
}

type PartialTypographyRule = Partial<TypographyRule>;

const FONT_CATALOG = {
  cormorant: {
    label: 'Cormorant Garamond',
    cssValue: 'var(--font-cormorant), Georgia, serif',
  },
  montserrat: {
    label: 'Montserrat',
    cssValue: 'var(--font-montserrat), sans-serif',
  },
  notoSansArabic: {
    label: 'Noto Sans Arabic',
    cssValue: 'var(--font-noto-sans-arabic), sans-serif',
  },
  cairo: {
    label: 'Cairo',
    cssValue: 'var(--font-cairo), sans-serif',
  },
  amiri: {
    label: 'Amiri',
    cssValue: 'var(--font-amiri), serif',
  },
} satisfies Record<string, FontDefinition>;

const BASE_FONT_ROLES: Record<FontFamilyRole, FontDefinition> = {
  heading: FONT_CATALOG.cormorant,
  body: FONT_CATALOG.montserrat,
  accent: FONT_CATALOG.cormorant,
};

const BASE_VARIANTS: Record<TypographyVariant, TypographyRule> = {
  hero: {
    fontFamilyRole: 'heading',
    fontSize: 'clamp(2.25rem, 5vw, 4rem)',
    lineHeight: '1.08',
    fontWeight: 700,
    letterSpacing: '-0.02em',
  },
  sectionTitle: {
    fontFamilyRole: 'heading',
    fontSize: 'clamp(1.75rem, 3.5vw, 2.75rem)',
    lineHeight: '1.15',
    fontWeight: 700,
    letterSpacing: '-0.01em',
  },
  cardTitle: {
    fontFamilyRole: 'heading',
    fontSize: 'clamp(1.125rem, 2vw, 1.5rem)',
    lineHeight: '1.2',
    fontWeight: 600,
    letterSpacing: '0em',
  },
  bodyLg: {
    fontFamilyRole: 'body',
    fontSize: 'clamp(1rem, 1.5vw, 1.125rem)',
    lineHeight: '1.65',
    fontWeight: 400,
    letterSpacing: '0em',
  },
  bodyMd: {
    fontFamilyRole: 'body',
    fontSize: '1rem',
    lineHeight: '1.6',
    fontWeight: 400,
    letterSpacing: '0em',
  },
  bodySm: {
    fontFamilyRole: 'body',
    fontSize: '0.875rem',
    lineHeight: '1.55',
    fontWeight: 400,
    letterSpacing: '0em',
  },
  caption: {
    fontFamilyRole: 'body',
    fontSize: '0.75rem',
    lineHeight: '1.45',
    fontWeight: 500,
    letterSpacing: '0.02em',
  },
  overline: {
    fontFamilyRole: 'body',
    fontSize: '0.75rem',
    lineHeight: '1.2',
    fontWeight: 700,
    letterSpacing: '0.18em',
    textTransform: 'uppercase',
  },
  label: {
    fontFamilyRole: 'body',
    fontSize: '0.75rem',
    lineHeight: '1.2',
    fontWeight: 700,
    letterSpacing: '0.12em',
    textTransform: 'uppercase',
  },
  price: {
    fontFamilyRole: 'heading',
    fontSize: 'clamp(1.25rem, 2.2vw, 1.75rem)',
    lineHeight: '1.2',
    fontWeight: 700,
    letterSpacing: '0.02em',
  },
  quote: {
    fontFamilyRole: 'body',
    fontSize: 'clamp(0.938rem, 1.3vw, 1.063rem)',
    lineHeight: '1.75',
    fontWeight: 400,
    letterSpacing: '0em',
    fontStyle: 'italic',
  },
  buttonPrimary: {
    fontFamilyRole: 'body',
    fontSize: '0.688rem',
    lineHeight: '1.2',
    fontWeight: 700,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
  },
  buttonSecondary: {
    fontFamilyRole: 'body',
    fontSize: '0.688rem',
    lineHeight: '1.2',
    fontWeight: 600,
    letterSpacing: '0.05em',
    textTransform: 'uppercase',
  },
  topbarSelectValue: {
    fontFamilyRole: 'body',
    fontSize: '0.688rem',
    lineHeight: '1.2',
    fontWeight: 700,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
  },
  topbarActionValue: {
    fontFamilyRole: 'body',
    fontSize: '0.9rem',
    lineHeight: '1.2',
    fontWeight: 700,
    letterSpacing: '0.12em',
    textTransform: 'uppercase',
  },
  topbarBrandName: {
    fontFamilyRole: 'body',
    fontSize: '0.98rem',
    lineHeight: '1.2',
    fontWeight: 700,
    letterSpacing: '0.12em',
    textTransform: 'uppercase',
  },
  topbarSectionLink: {
    fontFamilyRole: 'body',
    fontSize: '0.813rem',
    lineHeight: '1.2',
    fontWeight: 600,
    letterSpacing: '0.05em',
    textTransform: 'none',
  },
  navTitle: {
    fontFamilyRole: 'heading',
    fontSize: 'clamp(1.125rem, 1.5vw, 1.375rem)',
    lineHeight: '1.05',
    fontWeight: 700,
    letterSpacing: '-0.01em',
  },
  navMeta: {
    fontFamilyRole: 'body',
    fontSize: '0.75rem',
    lineHeight: '1.3',
    fontWeight: 500,
    letterSpacing: '0.02em',
  },
  pageTitle: {
    fontFamilyRole: 'heading',
    fontSize: 'clamp(2rem, 4.2vw, 3.25rem)',
    lineHeight: '1.1',
    fontWeight: 500,
    letterSpacing: '-0.01em',
  },
  chapterKicker: {
    fontFamilyRole: 'body',
    fontSize: '0.82rem',
    lineHeight: '1.25',
    fontWeight: 700,
    letterSpacing: '0.2em',
    textTransform: 'uppercase',
  },
  chapterTitle: {
    fontFamilyRole: 'heading',
    fontSize: 'clamp(2rem, 4vw, 3.2rem)',
    lineHeight: '1.05',
    fontWeight: 700,
    letterSpacing: '-0.025em',
  },
  heroLede: {
    fontFamilyRole: 'body',
    fontSize: 'clamp(1rem, 1.8vw, 1.2rem)',
    lineHeight: '1.7',
    fontWeight: 400,
    letterSpacing: '0em',
  },
  heroMetaPrimary: {
    fontFamilyRole: 'body',
    fontSize: '0.94rem',
    lineHeight: '1.4',
    fontWeight: 600,
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
  },
  heroMetaSecondary: {
    fontFamilyRole: 'body',
    fontSize: '0.875rem',
    lineHeight: '1.5',
    fontWeight: 500,
    letterSpacing: '0.02em',
  },
  letterTitle: {
    fontFamilyRole: 'heading',
    fontSize: 'clamp(2.125rem, 4.5vw, 3.5rem)',
    lineHeight: '1.15',
    fontWeight: 500,
    letterSpacing: '-0.02em',
  },
  letterHighlight: {
    fontFamilyRole: 'heading',
    fontSize: '1rem',
    lineHeight: '1.4',
    fontWeight: 500,
    letterSpacing: '0em',
    fontStyle: 'italic',
  },
  letterBody: {
    fontFamilyRole: 'body',
    fontSize: '1rem',
    lineHeight: '1.75',
    fontWeight: 400,
    letterSpacing: '0em',
  },
  signatureName: {
    fontFamilyRole: 'heading',
    fontSize: 'clamp(1.15rem, 1.7vw, 1.5rem)',
    lineHeight: '1.2',
    fontWeight: 600,
    letterSpacing: '-0.01em',
  },
  signatureMeta: {
    fontFamilyRole: 'body',
    fontSize: '0.85rem',
    lineHeight: '1.45',
    fontWeight: 500,
    letterSpacing: '0.06em',
    textTransform: 'none',
  },
  routeMapTitle: {
    fontFamilyRole: 'heading',
    fontSize: 'clamp(1.8rem, 3.2vw, 2.65rem)',
    lineHeight: '1.08',
    fontWeight: 700,
    letterSpacing: '-0.02em',
  },
  routeMapBody: {
    fontFamilyRole: 'body',
    fontSize: '1rem',
    lineHeight: '1.72',
    fontWeight: 400,
    letterSpacing: '0em',
  },
  timelineTitle: {
    fontFamilyRole: 'heading',
    fontSize: '1.25rem',
    lineHeight: '1.2',
    fontWeight: 600,
    letterSpacing: '-0.01em',
  },
  timelineMeta: {
    fontFamilyRole: 'body',
    fontSize: '0.8125rem',
    lineHeight: '1.5',
    fontWeight: 600,
    letterSpacing: '0em',
  },
  dayTitle: {
    fontFamilyRole: 'heading',
    fontSize: 'clamp(1.5rem, 2.8vw, 2.15rem)',
    lineHeight: '1.14',
    fontWeight: 700,
    letterSpacing: '-0.015em',
  },
  dayBody: {
    fontFamilyRole: 'body',
    fontSize: '0.98rem',
    lineHeight: '1.72',
    fontWeight: 400,
    letterSpacing: '0em',
  },
  hotelTitle: {
    fontFamilyRole: 'heading',
    fontSize: 'clamp(1.35rem, 2.3vw, 1.9rem)',
    lineHeight: '1.16',
    fontWeight: 700,
    letterSpacing: '-0.015em',
  },
  hotelMeta: {
    fontFamilyRole: 'body',
    fontSize: '0.82rem',
    lineHeight: '1.5',
    fontWeight: 600,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
  },
  hotelBody: {
    fontFamilyRole: 'body',
    fontSize: '0.96rem',
    lineHeight: '1.7',
    fontWeight: 400,
    letterSpacing: '0em',
  },
  investmentTitle: {
    fontFamilyRole: 'body',
    fontSize: '1.125rem',
    lineHeight: '1.3',
    fontWeight: 600,
    letterSpacing: '-0.01em',
  },
  investmentValue: {
    fontFamilyRole: 'body',
    fontSize: '1.5rem',
    lineHeight: '1.2',
    fontWeight: 600,
    letterSpacing: '-0.01em',
  },
  investmentMeta: {
    fontFamilyRole: 'body',
    fontSize: '0.95rem',
    lineHeight: '1.65',
    fontWeight: 400,
    letterSpacing: '0em',
  },
  termTitle: {
    fontFamilyRole: 'heading',
    fontSize: 'clamp(1.8rem, 3vw, 2.55rem)',
    lineHeight: '1.08',
    fontWeight: 700,
    letterSpacing: '-0.02em',
  },
  termLabel: {
    fontFamilyRole: 'heading',
    fontSize: '1.25rem',
    lineHeight: '1.3',
    fontWeight: 500,
    letterSpacing: '0em',
  },
  termBody: {
    fontFamilyRole: 'body',
    fontSize: '0.95rem',
    lineHeight: '1.7',
    fontWeight: 400,
    letterSpacing: '0em',
  },
  designerTitle: {
    fontFamilyRole: 'heading',
    fontSize: 'clamp(1.9rem, 3.2vw, 2.75rem)',
    lineHeight: '1.08',
    fontWeight: 700,
    letterSpacing: '-0.02em',
  },
  designerQuote: {
    fontFamilyRole: 'heading',
    fontSize: 'clamp(1.08rem, 2vw, 1.42rem)',
    lineHeight: '1.55',
    fontWeight: 500,
    letterSpacing: '0em',
    fontStyle: 'italic',
  },
  footerText: {
    fontFamilyRole: 'body',
    fontSize: '0.88rem',
    lineHeight: '1.55',
    fontWeight: 500,
    letterSpacing: '0.02em',
  },
  stateTitle: {
    fontFamilyRole: 'heading',
    fontSize: 'clamp(2rem, 4vw, 3.2rem)',
    lineHeight: '1.05',
    fontWeight: 700,
    letterSpacing: '-0.025em',
    maxWidth: '12ch',
  },
};

const BRAND_FONT_OVERRIDES: Partial<
  Record<BrandKey, Partial<Record<FontFamilyRole, FontDefinition>>>
> = {};

const BRAND_VARIANT_OVERRIDES: Partial<
  Record<BrandKey, Partial<Record<TypographyVariant, PartialTypographyRule>>>
> = {
  'capella-travel': {
    pageTitle: {
      fontSize: 'clamp(3.2rem, 7.5vw, 5.7rem)',
      lineHeight: '0.94',
      letterSpacing: '-0.04em',
    },
    chapterTitle: {
      fontSize: 'clamp(2.1rem, 4vw, 3.35rem)',
      lineHeight: '1.02',
    },
    investmentValue: {
      fontSize: 'clamp(1.5rem, 2.5vw, 2rem)',
    },
    overline: {
      letterSpacing: '0.22em',
    },
    label: {
      letterSpacing: '0.18em',
    },
    buttonPrimary: {
      letterSpacing: '0.12em',
    },
    topbarActionValue: {
      letterSpacing: '0.14em',
    },
    topbarBrandName: {
      letterSpacing: '0.14em',
    },
  },
  selvara: {
    heroLede: {
      lineHeight: '1.8',
    },
    bodyLg: {
      lineHeight: '1.72',
    },
    bodyMd: {
      lineHeight: '1.68',
    },
    chapterTitle: {
      lineHeight: '1.12',
    },
    dayBody: {
      lineHeight: '1.78',
    },
    designerQuote: {
      lineHeight: '1.7',
    },
    footerText: {
      lineHeight: '1.6',
    },
  },
};

const THEME_VIEW_MODE_OVERRIDES: Record<
  ThemeId,
  Partial<Record<ViewMode, Partial<Record<TypographyVariant, PartialTypographyRule>>>>
> = {
  brochure: {
    mobile: {
      pageTitle: {
        fontSize: 'clamp(2rem, 8vw, 2.85rem)',
        lineHeight: '1.05',
      },
      chapterTitle: {
        fontSize: 'clamp(1.65rem, 7vw, 2.3rem)',
      },
      heroLede: {
        fontSize: '1rem',
        lineHeight: '1.65',
      },
      routeMapTitle: {
        fontSize: 'clamp(1.55rem, 6vw, 2rem)',
      },
      dayTitle: {
        fontSize: 'clamp(1.45rem, 5.5vw, 1.85rem)',
      },
      investmentTitle: {
        fontSize: 'clamp(1.35rem, 5.5vw, 1.8rem)',
      },
      designerTitle: {
        fontSize: 'clamp(1.65rem, 6vw, 2.2rem)',
      },
      letterBody: {
        fontSize: '0.96rem',
      },
      termBody: {
        fontSize: '0.92rem',
      },
      termLabel: {
        fontSize: '1.125rem',
      },
      topbarSelectValue: {
        fontSize: '0.84rem',
      },
      topbarActionValue: {
        fontSize: '0.84rem',
      },
      topbarBrandName: {
        fontSize: '0.84rem',
        letterSpacing: '0.1em',
      },
      topbarSectionLink: {
        fontSize: '0.78rem',
        letterSpacing: '0.12em',
      },
    },
    pdf: {
      navTitle: {
        fontSize: '12pt',
        lineHeight: '1.05',
      },
      navMeta: {
        fontSize: '8.5pt',
        lineHeight: '1.3',
      },
      pageTitle: {
        fontSize: '25pt',
        lineHeight: '1.0',
      },
      chapterKicker: {
        fontSize: '8.5pt',
      },
      chapterTitle: {
        fontSize: '21pt',
        lineHeight: '1.06',
      },
      heroLede: {
        fontSize: '10.5pt',
        lineHeight: '1.45',
      },
      heroMetaPrimary: {
        fontSize: '8.5pt',
      },
      heroMetaSecondary: {
        fontSize: '8.5pt',
      },
      letterTitle: {
        fontSize: '19pt',
      },
      letterHighlight: {
        fontSize: '10pt',
      },
      letterBody: {
        fontSize: '10pt',
        lineHeight: '1.6',
      },
      signatureName: {
        fontSize: '12pt',
      },
      signatureMeta: {
        fontSize: '8pt',
      },
      routeMapTitle: {
        fontSize: '18pt',
      },
      routeMapBody: {
        fontSize: '10pt',
        lineHeight: '1.55',
      },
      timelineTitle: {
        fontSize: '11.5pt',
      },
      timelineMeta: {
        fontSize: '8.5pt',
        lineHeight: '1.45',
      },
      dayTitle: {
        fontSize: '16pt',
      },
      dayBody: {
        fontSize: '9.6pt',
        lineHeight: '1.42',
      },
      hotelTitle: {
        fontSize: '14pt',
      },
      hotelMeta: {
        fontSize: '8.2pt',
      },
      hotelBody: {
        fontSize: '9.4pt',
        lineHeight: '1.55',
      },
      investmentTitle: {
        fontSize: '16pt',
      },
      investmentValue: {
        fontSize: '15pt',
      },
      investmentMeta: {
        fontSize: '9.2pt',
      },
      termTitle: {
        fontSize: '18pt',
      },
      termLabel: {
        fontSize: '13pt',
      },
      termBody: {
        fontSize: '9.4pt',
        lineHeight: '1.55',
      },
      designerTitle: {
        fontSize: '19pt',
      },
      designerQuote: {
        fontSize: '11pt',
        lineHeight: '1.55',
      },
      footerText: {
        fontSize: '8.5pt',
        lineHeight: '1.4',
      },
      buttonPrimary: {
        fontSize: '8pt',
      },
      buttonSecondary: {
        fontSize: '8.5pt',
      },
      topbarSelectValue: {
        fontSize: '8.5pt',
      },
      topbarActionValue: {
        fontSize: '8pt',
      },
      topbarBrandName: {
        fontSize: '8pt',
      },
      topbarSectionLink: {
        fontSize: '8pt',
      },
    },
  },
};

const VARIANT_TO_CLASSNAME: Record<TypographyVariant, string> = {
  hero: 'typo-hero',
  sectionTitle: 'typo-section-title',
  cardTitle: 'typo-card-title',
  bodyLg: 'typo-body-lg',
  bodyMd: 'typo-body-md',
  bodySm: 'typo-body-sm',
  caption: 'typo-caption',
  overline: 'typo-overline',
  label: 'typo-label',
  price: 'typo-price',
  quote: 'typo-quote',
  buttonPrimary: 'typo-button-primary',
  buttonSecondary: 'typo-button-secondary',
  topbarSelectValue: 'typo-topbar-select-value',
  topbarActionValue: 'typo-topbar-action-value',
  topbarBrandName: 'typo-topbar-brand-name',
  topbarSectionLink: 'typo-topbar-section-link',
  navTitle: 'typo-nav-title',
  navMeta: 'typo-nav-meta',
  pageTitle: 'typo-page-title',
  chapterKicker: 'typo-chapter-kicker',
  chapterTitle: 'typo-chapter-title',
  heroLede: 'typo-hero-lede',
  heroMetaPrimary: 'typo-hero-meta-primary',
  heroMetaSecondary: 'typo-hero-meta-secondary',
  letterTitle: 'typo-letter-title',
  letterHighlight: 'typo-letter-highlight',
  letterBody: 'typo-letter-body',
  signatureName: 'typo-signature-name',
  signatureMeta: 'typo-signature-meta',
  routeMapTitle: 'typo-route-map-title',
  routeMapBody: 'typo-route-map-body',
  timelineTitle: 'typo-timeline-title',
  timelineMeta: 'typo-timeline-meta',
  dayTitle: 'typo-day-title',
  dayBody: 'typo-day-body',
  hotelTitle: 'typo-hotel-title',
  hotelMeta: 'typo-hotel-meta',
  hotelBody: 'typo-hotel-body',
  investmentTitle: 'typo-investment-title',
  investmentValue: 'typo-investment-value',
  investmentMeta: 'typo-investment-meta',
  termTitle: 'typo-term-title',
  termLabel: 'typo-term-label',
  termBody: 'typo-term-body',
  designerTitle: 'typo-designer-title',
  designerQuote: 'typo-designer-quote',
  footerText: 'typo-footer-text',
  stateTitle: 'typo-state-title',
};

function mergeTypographyRule(
  baseRule: TypographyRule,
  ...overrides: Array<PartialTypographyRule | undefined>
): TypographyRule {
  return Object.assign({}, baseRule, ...overrides);
}

function getBrandFonts(brandKey: BrandKey): Record<FontFamilyRole, FontDefinition> {
  return {
    ...BASE_FONT_ROLES,
    ...BRAND_FONT_OVERRIDES[brandKey],
  };
}

function getThemeViewOverrides(themeId: ThemeId, viewMode: ViewMode) {
  return THEME_VIEW_MODE_OVERRIDES[themeId]?.[viewMode] ?? {};
}

export function getTypographyConfig({
  brandKey,
  themeId,
  viewMode,
}: TypographyContext): BrandTypographyConfig {
  const fonts = getBrandFonts(brandKey);
  const brandOverrides = BRAND_VARIANT_OVERRIDES[brandKey] ?? {};
  const themeOverrides = getThemeViewOverrides(themeId, viewMode);

  const variants = (Object.keys(BASE_VARIANTS) as TypographyVariant[]).reduce(
    (acc, variant) => {
      acc[variant] = mergeTypographyRule(
        BASE_VARIANTS[variant],
        brandOverrides[variant],
        themeOverrides[variant]
      );
      return acc;
    },
    {} as Record<TypographyVariant, TypographyRule>
  );

  return { fonts, variants };
}

export function getBrandTypographyConfig(brandKey: BrandKey) {
  return getTypographyConfig({
    brandKey,
    themeId: 'brochure',
    viewMode: 'desktop',
  });
}

export function getTypographyClassName(variant: TypographyVariant) {
  return VARIANT_TO_CLASSNAME[variant];
}

function buildVariableBlock(brandKey: BrandKey, themeId: ThemeId, viewMode: ViewMode) {
  const config = getTypographyConfig({ brandKey, themeId, viewMode });
  const selectors = [
    `:root[data-brand="${brandKey}"][data-theme="${themeId}"][data-view-mode="${viewMode}"]`,
    ...(brandKey === 'vietnam-safar' && viewMode === 'desktop'
      ? [
          `:root:not([data-brand="capella-travel"]):not([data-brand="selvara"])`,
          `:root[data-brand="runtime"]`,
        ]
      : []),
  ].join(',\n');
  const lines = [
    `${selectors} {`,
    `  --font-heading: ${config.fonts.heading.cssValue};`,
    `  --font-body: ${config.fonts.body.cssValue};`,
    `  --font-accent: ${config.fonts.accent.cssValue};`,
  ];

  for (const [variant, rule] of Object.entries(config.variants) as Array<
    [TypographyVariant, TypographyRule]
  >) {
    const prefix = `  --${getTypographyClassName(variant)}`;
    lines.push(`${prefix}-font-family: var(--font-${rule.fontFamilyRole});`);
    lines.push(`${prefix}-font-size: ${rule.fontSize};`);
    lines.push(`${prefix}-line-height: ${rule.lineHeight};`);
    lines.push(`${prefix}-font-weight: ${rule.fontWeight};`);
    lines.push(`${prefix}-letter-spacing: ${rule.letterSpacing};`);
    lines.push(`${prefix}-text-transform: ${rule.textTransform ?? 'none'};`);
    lines.push(`${prefix}-font-style: ${rule.fontStyle ?? 'normal'};`);
    lines.push(`${prefix}-max-width: ${rule.maxWidth ?? 'none'};`);
  }

  lines.push('}');
  return lines.join('\n');
}

function buildSemanticClassBlock() {
  return (Object.values(VARIANT_TO_CLASSNAME) as string[])
    .map(
      (className) => `.${className} {
  font-family: var(--${className}-font-family);
  font-size: var(--${className}-font-size);
  line-height: var(--${className}-line-height);
  font-weight: var(--${className}-font-weight);
  letter-spacing: var(--${className}-letter-spacing);
  text-transform: var(--${className}-text-transform);
  font-style: var(--${className}-font-style);
  max-width: var(--${className}-max-width);
}`
    )
    .join('\n\n');
}

function buildArabicBlock() {
  return `html[lang="ar"],
:root[data-lang="ar"],
[dir="rtl"] {
  --font-heading: var(--font-amiri), var(--font-noto-sans-arabic), Georgia, serif !important;
  --font-body: var(--font-noto-sans-arabic), var(--font-cairo), sans-serif !important;
  --font-accent: var(--font-amiri), var(--font-noto-sans-arabic), serif !important;
  --serif: var(--font-amiri), var(--font-noto-sans-arabic), Georgia, serif !important;
  --sans: var(--font-noto-sans-arabic), var(--font-cairo), sans-serif !important;
  --font-accent: var(--font-amiri), var(--font-noto-sans-arabic), serif !important;
}

html[lang="ar"] body,
:root[data-lang="ar"] body,
[dir="rtl"] body {
  font-family: var(--font-body) !important;
}

html[lang="ar"] [class*="typo-"],
:root[data-lang="ar"] [class*="typo-"],
[dir="rtl"] [class*="typo-"] {
  letter-spacing: normal !important;
}`;
}

function buildPrintBlock() {
  const brandBlocks = (['vietnam-safar', 'capella-travel', 'selvara'] as BrandKey[]).map(
    (brandKey) => {
      const config = getTypographyConfig({
        brandKey,
        themeId: 'brochure',
        viewMode: 'pdf',
      });
      const lines = [
        `  :root[data-brand="${brandKey}"] body {`,
        `    font-family: ${config.fonts.body.cssValue} !important;`,
        '  }',
      ];

      for (const [variant, rule] of Object.entries(config.variants) as Array<
        [TypographyVariant, TypographyRule]
      >) {
        const className = VARIANT_TO_CLASSNAME[variant];
        lines.push(`  :root[data-brand="${brandKey}"] .${className} {`);
        lines.push(`    font-size: ${rule.fontSize} !important;`);
        lines.push(`    line-height: ${rule.lineHeight} !important;`);
        lines.push(`    font-weight: ${rule.fontWeight} !important;`);
        lines.push(`    letter-spacing: ${rule.letterSpacing} !important;`);
        lines.push(`    max-width: ${rule.maxWidth ?? 'none'} !important;`);
        lines.push('  }');
      }

      return lines.join('\n');
    }
  );

  return `@media print {
  body {
    font-family: var(--font-body) !important;
  }

${brandBlocks.join('\n\n')}
}`;
}

export function buildTypographyStyleSheet() {
  const variableBlocks = (
    ['vietnam-safar', 'capella-travel', 'selvara'] as BrandKey[]
  ).flatMap((brandKey) =>
    (['desktop', 'mobile', 'pdf'] as ViewMode[]).map((viewMode) =>
      buildVariableBlock(brandKey, 'brochure', viewMode)
    )
  );

  return [
    ...variableBlocks,
    `body {
  font-family: var(--font-body);
  font-size: var(--typo-body-md-font-size);
  line-height: var(--typo-body-md-line-height);
  letter-spacing: var(--typo-body-md-letter-spacing);
  font-weight: var(--typo-body-md-font-weight);
}`,
    `h1, h2, h3, h4, h5, h6, p, button, input, textarea, label, a, li, dd, dt {
  font: inherit;
}`,
    buildSemanticClassBlock(),
    buildArabicBlock(),
    buildPrintBlock(),
  ].join('\n\n');
}
