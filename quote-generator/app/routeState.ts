import { type BrandKey, DEFAULT_BRAND_KEY, isBrandKey } from '../data/brandsData';
import {
  LANGUAGE_CODES,
  THEME_IDS,
  VIEW_MODES,
  type LanguageCode,
  type ThemeId,
  type ViewMode,
} from '../display/contracts';

type SearchParamsValue = string | string[] | undefined;

export type AppRouteState = {
  theme: ThemeId;
  brand: BrandKey;
  lang: LanguageCode;
  view?: ViewMode;
};

export type ResolvedAppRouteState = AppRouteState & {
  pathname: '/' | '/pdf';
  resolvedViewMode: ViewMode;
};

export interface TemplateOption {
  id: string;
  label: string;
  enabled: boolean;
}

export interface LanguageOption {
  code: LanguageCode;
  label: string;
}

export interface BrandOption {
  key: BrandKey;
  label: string;
  logoSrc: string;
}

export interface NewQuotationAction {
  href: string;
}

function readSingle(value: SearchParamsValue) {
  return Array.isArray(value) ? value[0] : value;
}

export function isThemeId(value: string | null | undefined): value is ThemeId {
  return THEME_IDS.some((themeId) => themeId === value);
}

export function isViewMode(value: string | null | undefined): value is ViewMode {
  return VIEW_MODES.some((viewMode) => viewMode === value);
}

export function isLanguageCode(value: string | null | undefined): value is LanguageCode {
  return LANGUAGE_CODES.some((languageCode) => languageCode === value);
}

function looksLikeMobileUserAgent(userAgent: string | null | undefined) {
  if (!userAgent) {
    return false;
  }

  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(userAgent);
}

export function resolveAppRouteState(input: {
  pathname: '/' | '/pdf';
  searchParams?: Record<string, SearchParamsValue>;
  cookieBrand?: string | null;
  userAgent?: string | null;
}): ResolvedAppRouteState {
  const requestedTheme = readSingle(input.searchParams?.theme);
  const requestedBrand = readSingle(input.searchParams?.brand);
  const requestedLang = readSingle(input.searchParams?.lang);
  const requestedView = readSingle(input.searchParams?.view);

  const theme: ThemeId = isThemeId(requestedTheme) ? requestedTheme : 'brochure';
  const brand = isBrandKey(requestedBrand)
    ? requestedBrand
    : isBrandKey(input.cookieBrand)
      ? input.cookieBrand
      : DEFAULT_BRAND_KEY;
  const lang: LanguageCode = isLanguageCode(requestedLang) ? requestedLang : 'en';
  const view: ViewMode | undefined = isViewMode(requestedView) ? requestedView : undefined;
  const resolvedViewMode =
    input.pathname === '/pdf'
      ? 'pdf'
      : view
        ? view
        : looksLikeMobileUserAgent(input.userAgent)
          ? 'mobile'
          : 'desktop';

  return {
    pathname: input.pathname,
    theme,
    brand,
    lang,
    view,
    resolvedViewMode,
  };
}

export function buildAppHref(
  state: ResolvedAppRouteState | AppRouteState,
  overrides: Partial<AppRouteState> = {},
  pathnameOverride?: '/' | '/pdf'
) {
  const pathname = pathnameOverride ?? ('pathname' in state ? state.pathname : '/');
  const finalState = {
    theme: overrides.theme ?? state.theme,
    brand: overrides.brand ?? state.brand,
    lang: overrides.lang ?? state.lang,
    view: overrides.view ?? state.view,
  };

  const params = new URLSearchParams();
  params.set('theme', finalState.theme);
  params.set('brand', finalState.brand);
  params.set('lang', finalState.lang);

  if (pathname !== '/pdf' && finalState.view) {
    params.set('view', finalState.view);
  }

  return `${pathname}?${params.toString()}`;
}

export function getTopbarLabels(lang: LanguageCode) {
  const labels = {
    en: {
      template: 'Template selector',
      language: 'Language selector',
      brand: 'Brand selector',
      newQuotation: 'Create quotation',
    },
    vi: {
      template: 'Bộ chọn template',
      language: 'Bộ chọn ngôn ngữ',
      brand: 'Bộ chọn thương hiệu',
      newQuotation: 'Tạo quotation mới',
    },
    ar: {
      template: 'محدد القالب',
      language: 'محدد اللغة',
      brand: 'محدد العلامة التجارية',
      newQuotation: 'إنشاء عرض جديد',
    },
  } as const;

  return labels[lang];
}
