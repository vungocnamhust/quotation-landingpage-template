import type { TypographyVariant } from '../config/typography';
import type { ThemeId, ViewMode } from './contracts';

export type PublicSectionId =
  | 'nav'
  | 'hero'
  | 'letter'
  | 'routeMap'
  | 'itineraryDivider'
  | 'itinerary'
  | 'staysDivider'
  | 'hotels'
  | 'journeyTogetherDivider'
  | 'pricing'
  | 'inclusionsExclusions'
  | 'paymentTerms'
  | 'designer'
  | 'footer';

export type StateSectionId = 'loading' | 'error' | 'notFound';

/**
 * The display-side text contract. `path` is a canonical JSON pointer for
 * fact/content values, or an allowlisted presentation override key.
 */
export type EditableTextOwner = 'fact' | 'fact-derived' | 'content' | 'design' | 'system';
export type EditableTextMode = 'plainText' | 'richText' | 'altText' | 'ariaLabel' | 'actionLabel';

export interface EditableText {
  value: string;
  path: string;
  owner: EditableTextOwner;
  mode: EditableTextMode;
}

/** Transitional fixture compatibility; runtime V2 builders must emit EditableText. */
export type TextValue = EditableText | string;

export function textValue(value: TextValue | undefined): string {
  return typeof value === 'string' ? value : value?.value ?? '';
}

export type LayoutVariantId =
  | 'hero-cover'
  | 'centered-stack'
  | 'editorial-split-55-45'
  | 'editorial-split-50-50'
  | 'timeline-with-sidebar'
  | 'day-story-grid'
  | 'hotel-editorial-odd-even'
  | 'full-bleed-divider'
  | 'pricing-ledger'
  | 'two-column-panel'
  | 'term-rows'
  | 'profile-split'
  | 'footer-minimal'
  | 'nav-overlay-fixed'
  | 'letter-sidebar-220'
  | 'route-map-interactive'
  | 'itinerary-day-single'
  | 'itinerary-day-multi'
  | 'stays-editorial-split'
  | 'pricing-investment-ledger'
  | 'pricing-hero-investment'
  | 'pricing-editorial-comparison'
  | 'pricing-editorial-rows'
  | 'inclusions-panels'
  | 'designer-editorial-profile';

export type ShellVariantId =
  | 'shell-none'
  | 'shell-indochine-soft'
  | 'shell-indochine-frame'
  | 'shell-editorial-strip'
  | 'shell-full-bleed'
  | 'shell-pdf-page'
  | 'shell-pdf-page-framed';

export type BackgroundVariant =
  | 'canvas'
  | 'paper'
  | 'glass'
  | 'contrast'
  | 'accent-wash'
  | 'image-overlay'
  | 'transparent'
  | 'honeyCream'
  | 'paperAlt'
  | 'card'
  | 'surfaceWhite'
  | 'investment';

export type SpacingVariant = 'tight' | 'comfortable' | 'airy' | 'immersive' | 'page';

export type Alignment = 'start' | 'center' | 'split';

export type PaletteColorKey =
  | 'canvas'
  | 'paper'
  | 'ink'
  | 'mutedInk'
  | 'accent'
  | 'accentAlt'
  | 'contrast'
  | 'onContrast'
  | 'focus'
  | 'storyContrast'
  | 'investmentSurface'
  | 'investmentText';

export type ColorReference = PaletteColorKey | 'transparent';

export type ComponentColorRole =
  | 'primary'
  | 'secondary'
  | 'inverse'
  | 'muted'
  | 'outline'
  | 'timelineMarker'
  | 'timelineRoute'
  | 'timelineActive';

export type ColorScopeId =
  | 'page'
  | 'appChrome'
  | 'heroOverlay'
  | 'editorialPaper'
  | 'routeMap'
  | 'chapterContrast'
  | 'pricing'
  | 'details'
  | 'brandJourney'
  | 'designer'
  | 'footer';

export interface BrandColorPalette {
  canvas: `#${string}`;
  paper: `#${string}`;
  ink: `#${string}`;
  mutedInk: `#${string}`;
  accent: `#${string}`;
  accentAlt: `#${string}`;
  contrast: `#${string}`;
  onContrast: `#${string}`;
  focus: `#${string}`;
  storyContrast: `#${string}`;
  investmentSurface: `#${string}`;
  investmentText: `#${string}`;
}

export interface ColorScopeRecipe {
  surface: ColorReference;
  onSurface: ColorReference;
  muted: ColorReference;
  accent: ColorReference;
  accentAlt: ColorReference;
  border: { color: PaletteColorKey; opacity: number };
  strongBorder: { color: PaletteColorKey; opacity: number };
  action: Record<'primary' | 'secondary', {
    surface: ColorReference;
    text: ColorReference;
    border: { color: PaletteColorKey; opacity: number };
  }>;
  timeline: {
    route: PaletteColorKey;
    /** A quieter, theme-resolved companion for short marker leaders. */
    leader: { color: PaletteColorKey; opacity: number };
    marker: PaletteColorKey;
    active: PaletteColorKey;
  };
  overlay?: {
    start: { color: PaletteColorKey; opacity: number };
    end: { color: PaletteColorKey; opacity: number };
  };
  /** Map-only reading surfaces; declared by the theme rather than CSS. */
  mapOverlay?: {
    header: { surface: PaletteColorKey; opacity: number };
    footer: { surface: PaletteColorKey; opacity: number };
    marker: { surface: PaletteColorKey; opacity: number };
  };
  /** Map raster treatment belongs to the theme so provider changes cannot inherit a mismatched CSS filter. */
  mapTileTreatment?: 'none' | 'google-prototype-v1';
  /** Full-canvas map vignette, kept separate from the reading and marker veils. */
  mapCanvasVeil?: { surface: PaletteColorKey; opacity: number };
  shadow: { color: PaletteColorKey; opacity: number };
  ornamentOpacity: number;
  viewModeAdjustments?: Partial<Record<ViewMode, Partial<ColorScopeRecipe>>>;
}

export interface ThemeColorRecipe {
  scopes: Record<ColorScopeId, ColorScopeRecipe>;
}

export interface ResolvedColorScope {
  id: ColorScopeId;
  style: Record<`--${string}`, string>;
}

export interface ResolvedColorSlots {
  page: ResolvedColorScope;
  appChrome: ResolvedColorScope;
  sections: Record<PublicSectionId, ResolvedColorScope>;
}

export type PdfPageTemplate =
  | 'cover'
  | 'chapter'
  | 'editorial'
  | 'timeline'
  | 'pricing'
  | 'details'
  | 'designer';

export interface TypographySlotMap {
  kicker?: TypographyVariant;
  title?: TypographyVariant;
  body?: TypographyVariant;
  metaPrimary?: TypographyVariant;
  metaSecondary?: TypographyVariant;
  quote?: TypographyVariant;
  price?: TypographyVariant;
  action?: TypographyVariant;
  signature?: TypographyVariant;
  /** Handwriting calligraphy glyph variant (Buongiorno Rastellino font). */
  signatureGlyph?: TypographyVariant;
  footer?: TypographyVariant;
  label?: TypographyVariant;
  link?: TypographyVariant;
  index?: TypographyVariant;
  badge?: TypographyVariant;
}

export interface PdfBehavior {
  pageTemplate: PdfPageTemplate;
  pageBreakBefore?: boolean;
  pageBreakAfter?: boolean;
  avoidBreakInside?: boolean;
  pageGroupWithNext?: boolean;
  allowCondensedVariant?: boolean;
}

export interface SectionDisplayConfig {
  layoutVariant: LayoutVariantId;
  shellVariant: ShellVariantId;
  backgroundVariant: BackgroundVariant;
  spacingVariant: SpacingVariant;
  alignment: Alignment;
  stickyBehavior?: 'fixed-overlay' | 'sticky-canvas' | 'static';
  ornamentVariant?: string;
  surfaceStyle?: 'borderless' | 'framed' | 'glass' | 'paper' | 'full-bleed';
  sectionIntroStyle?: 'hero' | 'chapter' | 'editorial' | 'ledger';
  mobileOrderStrategy?: string;
  interactionPreset?: 'route-map' | 'carousel' | 'none';
  visibilityByViewMode: Record<ViewMode, boolean>;
  ornaments: string[];
  colorScope: ColorScopeId;
  brandColorScopes?: Partial<Record<string, ColorScopeId>>;
  colorSlots: Partial<Record<'action' | 'badge' | 'link' | 'marker' | 'timeline', ComponentColorRole>>;
  typographySlots: TypographySlotMap;
  printBehavior: PdfBehavior;
}

export interface LayoutVariantDefinition {
  id: LayoutVariantId;
  slots: {
    section?: string;
    container: string;
    header?: string;
    intro?: string;
    content?: string;
    aside?: string;
    media?: string;
    items?: string;
    footer?: string;
    overlay?: string;
  };
  responsive: {
    mobile?: Partial<LayoutVariantDefinition['slots']>;
    pdf?: Partial<LayoutVariantDefinition['slots']>;
  };
}

export interface ShellVariantDefinition {
  id: ShellVariantId;
  className: string;
}

export interface ThemeDefinition {
  id: ThemeId;
  label: string;
  supportedViewModes: ViewMode[];
  pageShell: ShellVariantId;
  sectionOrder: PublicSectionId[];
  sectionConfigs: Record<PublicSectionId, Record<ViewMode, SectionDisplayConfig>>;
  layoutVariants: LayoutVariantId[];
  ornamentRegistry: Record<string, string>;
  assetRegistry: Record<string, string>;
  sectionBehaviorPresets: Partial<{
    nav: {
      scrollMode: 'hero-overlay';
    };
    routeMap: {
      interaction: 'interactive';
    };
    itinerary: {
      alternatingLayouts: boolean;
    };
  }>;
  typographyMap: Record<PublicSectionId, TypographySlotMap>;
  colorRecipe: ThemeColorRecipe;
  pdfRules: {
    fixedPageSize: 'A4';
    pageClassName: string;
    preserveColor: boolean;
  };
}

export interface BrandThemeTokens {
  brandKey: string;
  themeId: ThemeId;
  palette: BrandColorPalette;
  radii: {
    card: string;
    button: string;
    frame: string;
    pill: string;
  };
}

export interface NavActionViewModel {
  label: TextValue;
  href: string;
  emphasis?: 'primary' | 'secondary';
  caption?: TextValue;
}

export interface NavSecondaryActionViewModel {
  type: 'language' | 'notification' | 'pdf';
  label: TextValue;
  href?: string;
}

export interface NavViewModel {
  brandName: TextValue;
  brandLogo: TextValue;
  brandLogoSrc?: string;
  brandLogoAlt?: TextValue;
  sectionAriaLabel?: TextValue;
  themeLabel?: TextValue;
  languageOptions?: Array<{ code: string; label: TextValue }>;
  links: Array<{ label: TextValue; href: string }>;
  actions: NavActionViewModel[];
  secondaryActions?: NavSecondaryActionViewModel[];
  scrollStateBehavior?: 'hero-overlay';
}

export interface AppChromeViewModel {
  brandOptions: Array<{
    key: string;
    label: string;
    logoSrc: string;
  }>;
}

/** Server-provided V2 brand contract. Public sections never consume it directly. */
export interface BrandRenderProfile {
  id: string;
  displayName: string;
  hostname: string;
  logoUrl: string;
  palette: BrandColorPalette;
  radii: BrandThemeTokens['radii'];
  themeId?: ThemeId;
  layoutVersion?: number;
}

export interface HeroViewModel {
  kicker: TextValue;
  title: TextValue;
  lede: TextValue;
  metaPrimary: TextValue;
  metaSecondary: TextValue;
  primaryCta: NavActionViewModel;
  footerMeta: TextValue;
  backgroundImage: string;
  backgroundImageAlt: TextValue;
}

export interface LetterViewModel {
  chapterKicker: TextValue;
  title: TextValue;
  highlight: TextValue;
  greeting: TextValue;
  intro: TextValue;
  body: TextValue[];
  outro: TextValue;
  signatureName: TextValue;
  signatureRole: TextValue;
  contactLine?: string;
  decorAsset?: string;
  signatureContactLine?: TextValue;
  /** Calligraphy glyph characters rendered in the handwriting font above signatureName. Optional — absent when designer has no signature_initial set. */
  signatureGlyph?: TextValue;
}

export interface RouteSegmentViewModel {
  sequence: string;
  title: TextValue;
  description: TextValue;
  sidebarLabel?: TextValue;
  duration?: TextValue;
  hotelName?: TextValue;
  coordinates: [number, number];
  dayLabel: TextValue;
  city: TextValue;
  image?: string;
  dayStart?: number;
  dayEnd?: number;
  badgeLabel?: string;
}

export interface RouteMapViewModel {
  kicker?: TextValue;
  title: TextValue;
  description: TextValue;
  segments: RouteSegmentViewModel[];
  mapModes: TextValue[];
  mapModeOptions: Array<{
    id: string;
    label: TextValue;
    tileUrl?: string;
    attribution?: string;
    backgroundImage?: string;
  }>;
  defaultMode: string;
  initialActiveSegment: string;
  isInteractiveAvailable: boolean;
  unavailableMessage: TextValue;
  overviewAriaLabel: TextValue;
  mapViewport: {
    center: [number, number] | null;
    latSpan: number;
    lngSpan: number;
  };
  interactiveMarkers: Array<{
    sequence: string;
    coordinates: [number, number];
    dayLabel: TextValue;
    title: TextValue;
    city: TextValue;
  }>;
}

export interface ChapterDividerViewModel {
  kicker: TextValue;
  title: TextValue;
  tagline: TextValue;
  image?: string;
  imageAlt?: TextValue;
  closing?: TextValue;
  exploreLabel?: TextValue;
  showDivider?: boolean;
  journeyMeta?: Array<{
    label: TextValue;
    value: TextValue;
  }>;
  exploreHref?: string;
}

export interface ItineraryDetailRow {
  label: TextValue;
  value: TextValue;
}

export interface ItineraryDayViewModel {
  dayLabel: TextValue;
  title: TextValue;
  description: TextValue[];
  layoutType: 'single' | 'multi';
  isAlternate: boolean;
  highlights?: TextValue;
  notes?: TextValue[];
  overnight?: TextValue;
  meals?: TextValue[];
  detailRows: ItineraryDetailRow[];
  heroImage: string;
  secondaryImages: string[];
  carouselImages: string[];
  carouselImageAlts: TextValue[];
  supportingImages: string[];
  supportingImageAlts: TextValue[];
  city: TextValue;
  carouselLabels: {
    previous: TextValue;
    next: TextValue;
    list: TextValue;
    show: TextValue;
  };
}

export interface ItinerarySectionViewModel {
  kicker: TextValue;
  title: TextValue;
  description: TextValue;
  days: ItineraryDayViewModel[];
}

export interface HotelCardViewModel {
  city: TextValue;
  name: TextValue;
  intro?: TextValue;
  dateRanges: TextValue[];
  telephone?: TextValue;
  telephonePrefix?: TextValue;
  hotelImage: string;
  hotelImageAlt: TextValue;
  roomImage: string;
  roomImageAlt: TextValue;
  roomType: TextValue;
  layoutParity: 'odd' | 'even';
  introVisibility?: 'full' | 'compact';
}

export interface HotelsViewModel {
  kicker?: TextValue;
  title: TextValue;
  description: TextValue;
  cards: HotelCardViewModel[];
  roomNotes?: TextValue;
}

export interface StaysDividerViewModel {
  image: string;
  imageAlt: TextValue;
  kicker: TextValue;
  title: TextValue;
  tagline: TextValue;
  closing?: TextValue;
  pdfTitle?: TextValue;
}

export interface JourneyTogetherDividerViewModel {
  image: string;
  imageAlt: TextValue;
  kicker: TextValue;
  title: TextValue;
  tagline: TextValue;
  closing: TextValue;
}

export interface PriceOptionViewModel {
  index: number;
  displayIndex: TextValue;
  label: TextValue;
  description?: TextValue;
  badge?: TextValue;
  groupTotalPrice: TextValue;
  perTravelerPrice: TextValue;
  perAdultPrice?: TextValue;
  perChildPrice?: TextValue;
  pricingBreakdown?: TextValue;
  groupTotalLabel?: TextValue;
  isSelection?: boolean;
}

export interface PricingViewModel {
  kicker: TextValue;
  title: TextValue;
  description: TextValue;
  options: PriceOptionViewModel[];
  importantNote?: TextValue;
  importantNoteLabel: TextValue;
}

export type InclusionItemViewModel =
  | TextValue
  | {
      title: TextValue;
      desc: TextValue;
    };

export interface InclusionsExclusionsViewModel {
  kicker?: TextValue;
  title: TextValue;
  inclusionsTitle?: TextValue;
  exclusionsTitle?: TextValue;
  inclusions: InclusionItemViewModel[];
  exclusions: TextValue[];
  inclusionsLead?: TextValue;
  exclusionsLead?: TextValue;
}

export interface PaymentTermItemViewModel {
  label: TextValue;
  bodyRichText: EditableText;
}

export interface PaymentTermsViewModel {
  kicker: TextValue;
  title: TextValue;
  description: TextValue;
  cta: NavActionViewModel;
  terms: PaymentTermItemViewModel[];
}

export interface FinalizationColumnViewModel {
  title: TextValue;
  items: TextValue[];
}

export interface FinalizationViewModel {
  kicker: TextValue;
  title: TextValue;
  description: TextValue;
  required: FinalizationColumnViewModel;
  afterConfirmation: FinalizationColumnViewModel;
}

export interface DesignerSupportBlockViewModel {
  title: TextValue;
  iconSrc: string;
  items: TextValue[];
}

export interface DesignerViewModel {
  kicker: TextValue;
  title: TextValue;
  quote: TextValue;
  ctaBody?: TextValue;
  name: TextValue;
  subtitle?: TextValue;
  signatureLabel: TextValue;
  experienceNote: TextValue;
  avatar: string;
  avatarAlt: TextValue;
  contactActions: NavActionViewModel[];
  supportBlocks: DesignerSupportBlockViewModel[];
}

export interface FooterViewModel {
  text: TextValue;
  secondaryMeta?: TextValue;
}

export interface StateViewModel {
  title: TextValue;
  body: TextValue;
  actionLabel?: TextValue;
}

export interface StateViewModels {
  loading: StateViewModel;
  error: StateViewModel;
  notFound: StateViewModel;
}

export interface PageViewModel {
  nav: NavViewModel;
  hero: HeroViewModel;
  letter: LetterViewModel;
  routeMap: RouteMapViewModel;
  itineraryDivider: ChapterDividerViewModel;
  itinerary: ItinerarySectionViewModel;
  staysDivider: StaysDividerViewModel;
  hotels: HotelsViewModel;
  journeyTogetherDivider: JourneyTogetherDividerViewModel;
  pricing: PricingViewModel;
  inclusionsExclusions: InclusionsExclusionsViewModel;
  paymentTerms: PaymentTermsViewModel;
  designer: DesignerViewModel;
  footer: FooterViewModel;
  states: StateViewModels;
}
