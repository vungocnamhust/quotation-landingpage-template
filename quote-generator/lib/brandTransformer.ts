/**
 * Canonical Multi-Brand Definitions and Dynamic PDF HTML Transformer.
 * Ensures 100% brand parity when rendering or previewing PDF quotations.
 */

export interface BrandConfig {
  id: string;
  name: string;
  domain: string;
  logo: string;
  color_primary: string;
  color_primary_dark: string;
  color_accent: string;
  color_accent_light: string;
  font_serif: string;
  font_sans: string;
  font_accent: string;
}

export const CANONICAL_BRANDS: Record<string, BrandConfig> = {
  capella_travel: {
    id: 'capella_travel',
    name: 'Capella Travel',
    domain: 'journeys.capellatravel.com',
    logo: '/assets/brands/capella_travel.png',
    color_primary: '#CBA135',
    color_primary_dark: '#B7894B',
    color_accent: '#333333',
    color_accent_light: '#4F4F4F',
    font_serif: 'Cormorant Garamond',
    font_sans: 'Montserrat',
    font_accent: 'Cormorant Garamond',
  },
  vietnam_safar: {
    id: 'vietnam_safar',
    name: 'Vietnam Safar',
    domain: 'journeys.vietnamsafar.vn',
    logo: '/assets/brands/vietnam_safar.png',
    color_primary: '#17412e',
    color_primary_dark: '#0e2f22',
    color_accent: '#b7894b',
    color_accent_light: '#d8bd85',
    font_serif: 'Cormorant Garamond',
    font_sans: 'Montserrat',
    font_accent: 'Allura',
  },
  selvara: {
    id: 'selvara',
    name: 'Selvara Journeys',
    domain: 'my.selvarajourneys.com',
    logo: '/assets/brands/selvara.svg',
    color_primary: '#A98338',
    color_primary_dark: '#8C6A29',
    color_accent: '#4F5D4E',
    color_accent_light: '#6B7A6A',
    font_serif: 'Cormorant Garamond',
    font_sans: 'Jost',
    font_accent: 'Cormorant Garamond',
  },
};

const BRAND_ALIASES: Record<string, string> = {
  'capella-travel': 'capella_travel',
  'capellatravel': 'capella_travel',
  'capella': 'capella_travel',
  'vietnam-safar': 'vietnam_safar',
  'vietnamsafar': 'vietnam_safar',
  'safar': 'vietnam_safar',
  'selvara-journeys': 'selvara',
  'selvarajourneys': 'selvara',
  'selvara': 'selvara',
};

const ALL_BRAND_LOGOS = [
  '/assets/brands/vietnam_safar.png',
  '/assets/brands/capella_travel.png',
  '/assets/brands/selvara.svg',
  '/assets/vietnam-safar-logo.png',
];

const ALL_BRAND_NAMES = [
  'Vietnam Safar',
  'Capella Travel',
  'Selvara Journeys',
];

const ALL_BRAND_DOMAINS = [
  'journeys.vietnamsafar.vn',
  'vietnamsafar.vn',
  'journeys.capellatravel.com',
  'capellatravel.com',
  'my.selvarajourneys.com',
  'selvarajourneys.com',
];

/**
 * Resolves the target BrandConfig from query parameter, hostname header, or ctx.json data.
 */
export function resolveBrand(
  brandParam?: string | null,
  hostHeader?: string | null,
  ctxData?: Record<string, unknown> | null
): BrandConfig {
  // 1. Direct query param
  if (brandParam) {
    const normalized = brandParam.trim().toLowerCase();
    const canonicalKey = BRAND_ALIASES[normalized] || normalized;
    if (CANONICAL_BRANDS[canonicalKey]) {
      return CANONICAL_BRANDS[canonicalKey];
    }
  }

  // 2. Host header matching
  if (hostHeader) {
    const hostLower = hostHeader.toLowerCase();
    if (hostLower.includes('capellatravel') || hostLower.includes('capella')) {
      return CANONICAL_BRANDS.capella_travel;
    }
    if (hostLower.includes('selvarajourneys') || hostLower.includes('selvara')) {
      return CANONICAL_BRANDS.selvara;
    }
    if (hostLower.includes('vietnamsafar') || hostLower.includes('safar')) {
      return CANONICAL_BRANDS.vietnam_safar;
    }
  }

  // 3. Fallback from ctxData
  if (ctxData) {
    const sellerEmail = typeof ctxData.seller_email === 'string' ? ctxData.seller_email.toLowerCase() : '';
    const contactWeb = typeof ctxData.contact_web === 'string' ? ctxData.contact_web.toLowerCase() : '';
    const brandId = typeof ctxData.brand === 'string' ? ctxData.brand.toLowerCase() : '';

    if (brandId && (CANONICAL_BRANDS[brandId] || BRAND_ALIASES[brandId])) {
      const key = BRAND_ALIASES[brandId] || brandId;
      return CANONICAL_BRANDS[key];
    }
    if (sellerEmail.includes('capellatravel') || contactWeb.includes('capellatravel')) {
      return CANONICAL_BRANDS.capella_travel;
    }
    if (sellerEmail.includes('selvara') || contactWeb.includes('selvara')) {
      return CANONICAL_BRANDS.selvara;
    }
  }

  // 4. Default brand
  return CANONICAL_BRANDS.vietnam_safar;
}

/**
 * Transforms an existing static PDF HTML document to match the target brand tokens,
 * logos, typography, headers, footers, and watermarks in single-pass memory operations.
 */
export function transformPdfHtmlWithBrand(
  html: string,
  targetBrandOrKey: string | BrandConfig
): string {
  const brand =
    typeof targetBrandOrKey === 'string'
      ? resolveBrand(targetBrandOrKey)
      : targetBrandOrKey;

  let result = html;

  // 1. Transform CSS :root brand tokens
  result = result.replace(
    /(--primary:\s*)(#[0-9a-fA-F]{3,8}|rgb\([^)]+\)|var\([^)]+\))(\s*;)/gi,
    `$1${brand.color_primary}$3`
  );
  result = result.replace(
    /(--primary-dark:\s*)(#[0-9a-fA-F]{3,8}|rgb\([^)]+\)|var\([^)]+\))(\s*;)/gi,
    `$1${brand.color_primary_dark}$3`
  );
  result = result.replace(
    /(--accent:\s*)(#[0-9a-fA-F]{3,8}|rgb\([^)]+\)|var\([^)]+\))(\s*;)/gi,
    `$1${brand.color_accent}$3`
  );
  result = result.replace(
    /(--accent-light:\s*)(#[0-9a-fA-F]{3,8}|rgb\([^)]+\)|var\([^)]+\))(\s*;)/gi,
    `$1${brand.color_accent_light}$3`
  );
  result = result.replace(
    /(--emerald:\s*)(#[0-9a-fA-F]{3,8}|rgb\([^)]+\)|var\([^)]+\))(\s*;)/gi,
    `$1${brand.color_primary}$3`
  );
  result = result.replace(
    /(--emerald-2:\s*)(#[0-9a-fA-F]{3,8}|rgb\([^)]+\)|var\([^)]+\))(\s*;)/gi,
    `$1${brand.color_primary_dark}$3`
  );
  result = result.replace(
    /(--gold:\s*)(#[0-9a-fA-F]{3,8}|rgb\([^)]+\)|var\([^)]+\))(\s*;)/gi,
    `$1${brand.color_accent}$3`
  );
  result = result.replace(
    /(--gold-2:\s*)(#[0-9a-fA-F]{3,8}|rgb\([^)]+\)|var\([^)]+\))(\s*;)/gi,
    `$1${brand.color_accent_light}$3`
  );
  result = result.replace(
    /(--line:\s*)color-mix\(in srgb,\s*#[0-9a-fA-F]{3,8}\s*28%,\s*transparent\)(\s*;)/gi,
    `$1color-mix(in srgb, ${brand.color_accent} 28%, transparent)$2`
  );
  result = result.replace(
    /(--font-accent:\s*["']?)([^"',;]+)(["']?[^;]*;)/gi,
    `$1${brand.font_accent}$3`
  );

  // 2. Transform Brand Logos
  for (const oldLogo of ALL_BRAND_LOGOS) {
    if (oldLogo !== brand.logo) {
      result = result.replaceAll(oldLogo, brand.logo);
    }
  }

  // 3. Transform Brand Names in Titles, Headings, Header/Footer & Watermark
  for (const oldName of ALL_BRAND_NAMES) {
    if (oldName !== brand.name) {
      // Compound phrases
      result = result.replaceAll(`${oldName} — Travel Proposal`, `${brand.name} — Travel Proposal`);
      result = result.replaceAll(`${oldName} — Luxury Quotation`, `${brand.name} — Luxury Quotation`);
      result = result.replaceAll(`${oldName} ·`, `${brand.name} ·`);
      result = result.replaceAll(`${oldName} —`, `${brand.name} —`);
      result = result.replaceAll(`“${oldName} ·`, `“${brand.name} ·`);
      result = result.replaceAll(`>${oldName}<`, `>${brand.name}<`);
    }
  }

  // 4. Transform Brand Contact Web Domains in Footer
  for (const oldDomain of ALL_BRAND_DOMAINS) {
    if (oldDomain !== brand.domain) {
      result = result.replaceAll(oldDomain, brand.domain);
    }
  }

  return result;
}
