import { BRANDS_DATA, type BrandKey } from '../data/brandsData';
import { getBrandThemeTokens, resolveColorSlots } from '../config/themeTokens';
import type { LanguageCode, ThemeId, ViewMode } from './contracts';
import { getThemeDefinition } from './themeRegistry';
import { validateColorContracts } from './validateColorContracts';
import type {
  BrandThemeTokens,
  AppChromeViewModel,
  PageViewModel,
  PublicSectionId,
  RouteSegmentViewModel,
  ResolvedColorSlots,
  ThemeDefinition,
} from './types';
import { textValue } from './types';

export interface DisplayDocument {
  theme: ThemeDefinition;
  tokens: BrandThemeTokens;
  colors: ResolvedColorSlots;
  appChrome: AppChromeViewModel;
  viewMode: ViewMode;
  lang: LanguageCode;
  page: PageViewModel;
}

validateColorContracts();

const I18N_LABELS = {
  en: {
    beginJourney: 'BEGIN THE JOURNEY',
    brochureTheme: 'BROCHURE THEME',
    classic: 'Classic',
    image: 'Image',
    routeMapTitle: 'Your Journey, Mapped',
    routeMapLead:
      'Follow a curated path through Vietnam, from timeless landmarks to refined luxury stopovers. Select a destination on the map or list to explore the highlights along the way.',
    daySingular: 'DAY',
    dayPlural: 'DAYS',
    highlights: 'Highlights',
    overnight: 'Overnight',
    meals: 'Meals',
    privateServices: 'Private Services',
    stayPlanning: 'Stay Planning',
    inclusionsTitle: 'Inclusions',
    exclusionsTitle: 'Exclusions',
    importantNote: 'Important Note',
    explore: 'Explore',
    chatWhatsapp: 'CHAT ON WHATSAPP',
    sendEmail: 'SEND AN EMAIL',
    tryAgain: 'Try Again',
    returnHome: 'Return Home',
    duration: 'Duration',
    route: 'Route',
    routeMapNav: 'Route Map',
    itineraryNav: 'Itinerary',
    quotationNav: 'Quotation',
    termsNav: 'Terms',
  },
  vi: {
    beginJourney: 'BẮT ĐẦU HÀNH TRÌNH',
    brochureTheme: 'BROCHURE THEME',
    classic: 'Bản đồ',
    image: 'Hình ảnh',
    routeMapTitle: 'Hành Trình Được Vẽ Thành Bản Đồ',
    routeMapLead:
      'Theo dấu một hành trình được tuyển chọn qua Việt Nam, từ những địa danh vượt thời gian đến các điểm dừng nghỉ sang trọng. Hãy chọn một điểm trên bản đồ hoặc trong danh sách để khám phá các điểm nhấn dọc đường.',
    daySingular: 'NGÀY',
    dayPlural: 'NGÀY',
    highlights: 'Điểm nhấn',
    overnight: 'Lưu trú',
    meals: 'Bữa ăn',
    privateServices: 'Dịch vụ riêng',
    stayPlanning: 'Lưu trú chọn lọc',
    inclusionsTitle: 'Bao gồm',
    exclusionsTitle: 'Không bao gồm',
    importantNote: 'Lưu ý quan trọng',
    explore: 'Khám phá',
    chatWhatsapp: 'NHẮN WHATSAPP',
    sendEmail: 'GỬI EMAIL',
    tryAgain: 'Thử lại',
    returnHome: 'Về trang chủ',
    duration: 'Thời lượng',
    route: 'Hành trình',
    routeMapNav: 'Bản đồ hành trình',
    itineraryNav: 'Lịch trình',
    quotationNav: 'Báo giá',
    termsNav: 'Điều khoản',
  },
  ar: {
    beginJourney: 'ابدأ الرحلة',
    brochureTheme: 'نمط الكتيب',
    classic: 'الخريطة',
    image: 'الصور',
    routeMapTitle: 'رحلتك مرسومة على الخريطة',
    routeMapLead:
      'اتبع مسارا منسقا عبر فيتنام، من المعالم الخالدة إلى محطات التوقف الفاخرة. اختر وجهة من الخريطة أو من القائمة لاستكشاف أبرز اللحظات على الطريق.',
    daySingular: 'اليوم',
    dayPlural: 'الأيام',
    highlights: 'أبرز المحطات',
    overnight: 'الإقامة',
    meals: 'الوجبات',
    privateServices: 'الخدمات الخاصة',
    stayPlanning: 'تنسيق الإقامة',
    inclusionsTitle: 'يشمل',
    exclusionsTitle: 'لا يشمل',
    importantNote: 'ملاحظة مهمة',
    explore: 'استكشف',
    chatWhatsapp: 'التواصل عبر واتساب',
    sendEmail: 'إرسال بريد إلكتروني',
    tryAgain: 'حاول مرة أخرى',
    returnHome: 'العودة للرئيسية',
    duration: 'المدة',
    route: 'المسار',
    routeMapNav: 'خريطة الرحلة',
    itineraryNav: 'برنامج الرحلة',
    quotationNav: 'عرض السعر',
    termsNav: 'الشروط',
  },
} as const;

const ITINERARY_LAYOUT_PRESETS: Record<
  BrandKey,
  Record<string, { layoutType: 'single' | 'multi'; isAlternate: boolean }>
> = {
  'vietnam-safar': {
    'Day 01': { layoutType: 'single', isAlternate: false },
    'Day 02': { layoutType: 'single', isAlternate: true },
    'Day 03': { layoutType: 'single', isAlternate: false },
  },
  'capella-travel': {
    'Day 01': { layoutType: 'single', isAlternate: false },
    'Day 02': { layoutType: 'single', isAlternate: true },
    'Day 03': { layoutType: 'single', isAlternate: false },
  },
  selvara: {
    'Day 01': { layoutType: 'single', isAlternate: false },
    'Day 02': { layoutType: 'single', isAlternate: true },
    'Day 03': { layoutType: 'single', isAlternate: false },
  },
};

function buildBrandLogoSrc(brandKey: BrandKey) {
  switch (brandKey)
  {
    case 'vietnam-safar':
      return '/assets/brands/vietnam_safar.png';
    case 'capella-travel':
      return '/assets/brands/capella_travel.png';
    case 'selvara':
      return '/assets/brands/selvara.svg';
    default:
      return '/assets/vietnam-safar-logo.png';
  }
}

function buildMapViewport(segments: RouteSegmentViewModel[]) {
  const latitudes = segments.map((segment) => segment.coordinates[0]);
  const longitudes = segments.map((segment) => segment.coordinates[1]);
  const minLat = Math.min(...latitudes);
  const maxLat = Math.max(...latitudes);
  const minLng = Math.min(...longitudes);
  const maxLng = Math.max(...longitudes);

  return {
    center: [(minLat + maxLat) / 2, (minLng + maxLng) / 2] as [number, number],
    latSpan: Math.max(maxLat - minLat, 0.5),
    lngSpan: Math.max(maxLng - minLng, 0.5),
  };
}

function getLanguageLabels(lang: LanguageCode) {
  return I18N_LABELS[lang] ?? I18N_LABELS.en;
}

function getRouteSummary(routeSegments: RouteSegmentViewModel[]) {
  return routeSegments.map((segment) => textValue(segment.city)).join(' — ');
}

function parseDurationCount(duration?: string | import('./types').TextValue) {
  duration = duration ? textValue(duration) : undefined;
  if (!duration)
  {
    return null;
  }

  const matched = duration.match(/\d+/);
  if (!matched)
  {
    return null;
  }

  const parsed = Number.parseInt(matched[0] ?? '', 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function buildRouteTimelineLabel({
  startDay,
  count,
  labels,
}: {
  startDay: number;
  count: number;
  labels: ReturnType<typeof getLanguageLabels>;
}) {
  const endDay = startDay + count - 1;

  if (count <= 1)
  {
    return `${labels.daySingular} ${startDay}`;
  }

  return `${labels.dayPlural} ${startDay}-${endDay}`;
}

function buildRouteTimelineSegments({
  segments,
  labels,
}: {
  segments: RouteSegmentViewModel[];
  labels: ReturnType<typeof getLanguageLabels>;
}) {
  let runningDay = 1;

  return segments.map((segment) => {
    const durationCount = parseDurationCount(segment.duration) ?? 1;
    const sidebarLabel = segment.sidebarLabel
      ? segment.sidebarLabel
      : buildRouteTimelineLabel({
        startDay: runningDay,
        count: durationCount,
        labels,
      });

    runningDay += durationCount;

    return {
      ...segment,
      sidebarLabel,
    };
  });
}

function buildLetterSignatureContact({
  contactLine,
  email,
  phone,
}: {
  contactLine?: string;
  email: string;
  phone: string;
}) {
  return contactLine || `${email} · ${phone}`;
}

export function buildPageViewModel({
  brandKey,
  lang,
}: {
  brandKey: BrandKey;
  lang: LanguageCode;
}): PageViewModel {
  const brand = BRANDS_DATA[brandKey];
  const brochure = brand.brochure;
  const labels = getLanguageLabels(lang);
  const routeSegments = buildRouteTimelineSegments({
    segments: brochure.routeMap.segments,
    labels,
  });
  const itineraryLayouts = ITINERARY_LAYOUT_PRESETS[brandKey];
  const routeSummary = getRouteSummary(routeSegments);
  const durationDays = brochure.itinerary.days.length;
  const letterSignatureName = brochure.letter.signatureName || brochure.designer.name;
  const letterSignatureRole =
    brochure.letter.signatureRole || brochure.designer.signatureLabel || brochure.designer.subtitle;
  const letterSignatureContactLine = buildLetterSignatureContact({
    contactLine: brochure.letter.contactLine,
    email: brand.contact.email,
    phone: brand.contact.phone,
  });

  return ({
    nav: {
      brandName: brand.name,
      brandLogo: brand.logoGlyph,
      brandLogoSrc: buildBrandLogoSrc(brandKey),
      links: [
        { label: labels.routeMapNav, href: '#route-map' },
        { label: labels.itineraryNav, href: '#itinerary' },
        { label: labels.quotationNav, href: '#pricing' },
        { label: labels.termsNav, href: '#payment-terms' },
      ],
      actions: [
        {
          label: 'PDF Download',
          href: `/pdf?brand=${brandKey}&lang=${lang}`,
          emphasis: 'primary',
        },
      ],
      scrollStateBehavior: 'hero-overlay',
    },
    hero: {
      ...brochure.hero,
      primaryCta: {
        label: labels.beginJourney,
        href: '#route-map',
        emphasis: 'primary',
      },
      footerMeta: `${brand.name} • ${labels.brochureTheme}`,
    },
    letter: {
      ...brochure.letter,
      decorAsset: '/assets/brands/indochine_icon/ruong_bac_thang.svg',
      signatureName: letterSignatureName,
      signatureRole: letterSignatureRole,
      signatureContactLine: letterSignatureContactLine,
    },
    routeMap: {
      ...brochure.routeMap,
      title: labels.routeMapTitle,
      description: labels.routeMapLead,
      segments: routeSegments,
      mapModes: [labels.classic, labels.image],
      mapModeOptions: [
        {
          id: 'classic',
          label: labels.classic,
          tileUrl: 'https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}&hl=vi',
          attribution: '&copy; Bản đồ chủ quyền Việt Nam | Dữ liệu bản đồ &copy; Google',
        },
        {
          id: 'image',
          label: labels.image,
        },
      ],
      defaultMode: 'classic',
      initialActiveSegment: routeSegments[0]?.sequence ?? '01',
      mapViewport: buildMapViewport(routeSegments),
      interactiveMarkers: routeSegments.map((segment) => ({
        sequence: segment.sequence,
        coordinates: segment.coordinates,
        title: segment.title,
        city: segment.city,
      })),
    },
    itineraryDivider: {
      ...brochure.itineraryDivider,
      exploreLabel: labels.explore,
      journeyMeta: [
        {
          label: labels.duration,
          value: `${durationDays} days / ${Math.max(durationDays - 1, 0)} nights`,
        },
        {
          label: labels.route,
          value: routeSummary,
        },
      ],
      exploreHref: '#itinerary',
    },
    itinerary: {
      ...brochure.itinerary,
      days: brochure.itinerary.days.map((day) => {
        const layout = itineraryLayouts[day.dayLabel] ?? {
          layoutType: 'single' as const,
          isAlternate: false,
        };
        const detailRows = [
          day.highlights ? { label: labels.highlights, value: day.highlights } : null,
          day.overnight ? { label: labels.overnight, value: day.overnight } : null,
          day.meals?.length ? { label: labels.meals, value: day.meals.join(' · ') } : null,
        ].filter(Boolean) as Array<{ label: string; value: string }>;

        return {
          ...day,
          layoutType: layout.layoutType,
          isAlternate: layout.isAlternate,
          detailRows,
          carouselImages: [day.heroImage, ...day.secondaryImages].slice(0, 3),
          supportingImages: day.secondaryImages,
        };
      }),
    },
    hotels: {
      ...brochure.hotels,
      cards: brochure.hotels.cards.map((card, index) => ({
        ...card,
        layoutParity: index % 2 === 0 ? 'odd' : 'even',
        introVisibility: 'full' as const,
      })),
    },
    staysDivider: brochure.staysDivider,
    pricing: {
      ...brochure.pricing,
      importantNoteLabel: labels.importantNote,
      options: brochure.pricing.options.map((option, index) => {
        return {
          index: index + 1,
          displayIndex: `${index + 1}`.padStart(2, '0'),
          label: option.optionName || option.category,
          groupTotalPrice: option.totalPrice || '',
          perTravelerPrice: option.perPersonPrice,
        };
      }),
    },
    inclusionsExclusions: {
      ...brochure.inclusionsExclusions,
      inclusionsTitle: labels.inclusionsTitle,
      exclusionsTitle: labels.exclusionsTitle,
      inclusions: brochure.inclusionsExclusions.inclusions,
    },
    paymentTerms: {
      ...brochure.paymentTerms,
      cta: {
        label: brochure.paymentTerms.cta,
        href: '#designer',
        emphasis: 'secondary',
      },
    },
    finalization: {
      kicker: 'NEXT STEPS',
      title: 'Finalization Checklist',
      description: 'The remaining details we will confirm together.',
      required: { title: 'Final Details Required', items: [] },
      afterConfirmation: { title: 'After Confirmation', items: [] },
    },
    designer: {
      ...brochure.designer,
      contactActions: [
        {
          label: labels.chatWhatsapp,
          href: brand.contact.whatsapp,
          emphasis: 'primary',
          caption: `No. ${brand.contact.phone}`,
        },
        {
          label: labels.sendEmail,
          href: `mailto:${brand.contact.email}`,
          emphasis: 'secondary',
          caption: `Email: ${brand.contact.email}`,
        },
      ],
      supportBlocks: [],
    },
    footer: {
      text: brochure.footer.text,
      secondaryMeta: undefined,
    },
    states: {
      loading: {
        title: brochure.states.loadingTitle,
        body: brochure.states.loadingBody,
      },
      error: {
        title: brochure.states.errorTitle,
        body: brochure.states.errorBody,
        actionLabel: labels.tryAgain,
      },
      notFound: {
        title: brochure.states.notFoundTitle,
        body: brochure.states.notFoundBody,
        actionLabel: labels.returnHome,
      },
    },
  } as unknown as PageViewModel);
}

export function buildDisplayDocument({
  brandKey,
  themeId,
  lang,
  viewMode,
}: {
  brandKey: BrandKey;
  themeId: ThemeId;
  lang: LanguageCode;
  viewMode: ViewMode;
}): DisplayDocument {
  const theme = getThemeDefinition(themeId);
  return {
    theme,
    tokens: getBrandThemeTokens(brandKey),
    colors: resolveColorSlots({ brandKey, theme, viewMode }),
    appChrome: {
      brandOptions: (Object.keys(BRANDS_DATA) as BrandKey[]).map((key) => ({
        key,
        label: BRANDS_DATA[key].name,
        logoSrc: buildBrandLogoSrc(key),
      })),
    },
    viewMode,
    lang,
    page: buildPageViewModel({ brandKey, lang }),
  };
}

export function getSectionDisplayConfig(
  theme: ThemeDefinition,
  sectionId: PublicSectionId,
  viewMode: ViewMode
) {
  return theme.sectionConfigs[sectionId][viewMode];
}
