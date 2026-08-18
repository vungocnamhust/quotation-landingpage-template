import { getBrandThemeTokensFromProfile, resolveColorSlotsFromProfile } from '../config/runtimeThemeTokens';
import { DESIGNER_PRESENTATION_DEFAULTS } from '../config/designerPresentationDefaults';
import type { AppChromeViewModel, BrandColorPalette, BrandRenderProfile, BrandThemeTokens, EditableText, EditableTextMode, EditableTextOwner, PageViewModel, PublicSectionId, ResolvedColorSlots, ThemeDefinition } from './types';
import type { LanguageCode, ViewMode } from './contracts';
import { getLanguageLabels, PRICING_AMOUNT_LABELS } from './labels';
import { getThemeDefinition } from './themeRegistry';

export interface DisplayDocument {
  theme: ThemeDefinition;
  tokens: BrandThemeTokens;
  colors: ResolvedColorSlots;
  appChrome: AppChromeViewModel;
  viewMode: ViewMode;
  lang: LanguageCode;
  quotationNumber: string;
  pdfWhitespaceSlogan: EditableText;
  page: PageViewModel;
}

export function getSectionDisplayConfig(theme: ThemeDefinition, sectionId: PublicSectionId, viewMode: ViewMode) {
  return theme.sectionConfigs[sectionId][viewMode];
}

type QuoteDocumentPayload = Record<string, unknown>;
type QuoteRecord = Record<string, unknown>;

const REQUIRED_PALETTE_KEYS = ['canvas', 'paper', 'ink', 'mutedInk', 'accent', 'accentAlt', 'contrast', 'onContrast', 'focus', 'storyContrast', 'investmentSurface', 'investmentText'] as const;
const REQUIRED_RADII_KEYS = ['card', 'button', 'frame', 'pill'] as const;

function normalizeBrandRenderProfile(profile: BrandRenderProfile): BrandRenderProfile {
  // Published releases predate the two background-only tokens. Normalize at
  // the render boundary so their immutable snapshots retain their old visual
  // contract while new mutable profiles supply the explicit values.
  const palette = profile.palette as Partial<BrandColorPalette>;
  return {
    ...profile,
    palette: {
      ...palette,
      storyContrast: palette.storyContrast ?? palette.contrast!,
      investmentSurface: palette.investmentSurface ?? palette.contrast!,
      investmentText: palette.investmentText ?? palette.onContrast!,
    } as BrandColorPalette,
  };
}

export function assertBrandRenderProfile(profile: BrandRenderProfile): void {
  if (!profile.id || !profile.displayName || !profile.hostname || !profile.logoUrl) throw new Error('Brand render profile is missing identity fields.');
  if (profile.themeId && profile.themeId !== 'brochure') throw new Error(`Unsupported V2 brand theme: ${profile.themeId}`);
  if (profile.layoutVersion && profile.layoutVersion !== 1) throw new Error(`Unsupported V2 layout version: ${profile.layoutVersion}`);
  for (const key of REQUIRED_PALETTE_KEYS) if (!/^#[0-9a-fA-F]{6}$/.test(profile.palette[key])) throw new Error(`Brand palette ${key} must be an opaque #RRGGBB color.`);
  for (const key of REQUIRED_RADII_KEYS) if (!profile.radii[key]) throw new Error(`Brand radius ${key} is required.`);
}

function record(value: unknown): QuoteRecord { return value && typeof value === 'object' && !Array.isArray(value) ? value as QuoteRecord : {}; }
function recordList(value: unknown): QuoteRecord[] { return Array.isArray(value) ? value.map(record) : []; }
function stringValue(value: unknown): string { return typeof value === 'string' ? value : ''; }
function positiveInteger(value: unknown): number | null { return typeof value === 'number' && Number.isInteger(value) && value > 0 ? value : null; }
function assetUrl(asset: unknown): string {
  if (typeof asset === 'string') return asset.trim();
  const url = record(asset).url;
  return typeof url === 'string' ? url.trim() : '';
}
function assetAlt(asset: unknown, path: string, fallback = ''): EditableText {
  return editable(stringValue(record(asset).altText).trim() || fallback, path, 'fact', 'altText');
}
function listText(items: unknown): string[] { return Array.isArray(items) ? items.map((item) => typeof item === 'string' ? item : stringValue(record(item).text)).filter(Boolean) : []; }
function contentBlocks(sections: QuoteRecord, sectionId: string): QuoteRecord[] { return recordList(record(sections[sectionId]).blocks); }
function contentBlock(blocks: QuoteRecord[], type: string): QuoteRecord { return blocks.find((block) => stringValue(block.type) === type) ?? {}; }
function blockItems(block: QuoteRecord): QuoteRecord[] { return recordList(block.items); }
function formatDisplayDate(value: string, lang: LanguageCode): string {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return '';
  const date = new Date(`${value}T00:00:00.000Z`);
  return Number.isNaN(date.getTime()) ? '' : new Intl.DateTimeFormat(lang, { day: 'numeric', month: 'short' }).format(date);
}
function formatPriceMinor(value: number | null, currency: string, lang: LanguageCode, suffix: string): string {
  if (value === null || !currency) return '';
  const locale = lang === 'vi' ? 'vi-VN' : lang === 'ar' ? 'ar' : 'en-US';
  const divisor = currency === 'VND' ? 1 : 100;
  const amount = value / divisor;
  const minimumFractionDigits = amount % 1 === 0 ? 0 : (currency === 'VND' ? 0 : 2);
  const maximumFractionDigits = currency === 'VND' ? 0 : 2;
  return `${new Intl.NumberFormat(locale, { style: 'currency', currency, minimumFractionDigits, maximumFractionDigits }).format(amount)} ${suffix}`;
}

function editable(value: string, path: string, owner: EditableTextOwner, mode: EditableTextMode = 'plainText'): EditableText {
  return { value, path, owner, mode };
}

function factCopy(value: string, path: string, fallback = ''): EditableText {
  return editable(value || fallback, path, 'fact');
}

function designCopy(overrides: QuoteRecord, key: string, fallback: string, mode: EditableTextMode = 'plainText'): EditableText {
  const value = stringValue(overrides[key]).trim() || fallback;
  return editable(value, `/presentation/copyOverrides/${key}`, 'design', mode);
}

function presentationAsset(overrides: QuoteRecord, key: string, fallback: unknown): QuoteRecord {
  const override = record(overrides[key]);
  return assetUrl(override) ? override : record(fallback);
}

function uniqueUrls(items: unknown[]): string[] {
  return [...new Set(items.map(assetUrl).filter(Boolean))];
}

function contentCopy(value: string, path: string, fallback: string): EditableText {
  return editable(value || fallback, path, 'content');
}

function derivedCopy(value: string, path: string, fallback = ''): EditableText {
  return editable(value || fallback, path, 'fact-derived');
}

function bookingTermItems(blocks: QuoteRecord[]): Array<{ item: QuoteRecord; path: string }> {
  return blocks.flatMap((block, blockIndex) => {
    const type = stringValue(block.type);
    if (type !== 'termList' && type !== 'paymentSchedule') return [];
    return blockItems(block).map((item, itemIndex) => ({
      item,
      path: `/content/sections/booking_terms/blocks/${blockIndex}/items/${itemIndex}`,
    }));
  });
}

/** The only V2 boundary from canonical API data to the five-layer display system. */
export function buildDisplayDocumentFromQuoteDocument({ document, brandProfile, lang, viewMode }: {
  document: QuoteDocumentPayload;
  brandProfile: BrandRenderProfile;
  lang: LanguageCode;
  viewMode: ViewMode;
}): DisplayDocument {
  const profile = normalizeBrandRenderProfile(brandProfile);
  assertBrandRenderProfile(profile);
  const labels = getLanguageLabels(lang);
  const theme = getThemeDefinition(profile.themeId ?? 'brochure');
  const trip = record(document.trip);
  const customer = record(document.customer);
  const customer_facts = record(document.customer_facts);
  const customerFacts = record(document.customerFacts);
  const booking = record(document.booking);
  const booking_facts = record(document.booking_facts);
  const bookingFacts = record(document.bookingFacts);
  const narrative = record(document.narrative);
  const route = record(document.route);
  const itinerary = record(document.itinerary);
  const stays = record(document.stays);
  const pricing = record(document.pricing);
  const customerGreeting = stringValue(customer.greetingName) || stringValue(customer.greeting_name) || stringValue(customer_facts.greeting_name) || stringValue(customer_facts.greetingName) || stringValue(customerFacts.greeting_name) || stringValue(customerFacts.greetingName);
  const customerParty = stringValue(customer.partyLabel) || stringValue(customer.party_label) || stringValue(customer_facts.party_label) || stringValue(customer_facts.partyLabel) || stringValue(customerFacts.party_label) || stringValue(customerFacts.partyLabel);
  const bookingTitleText = stringValue(booking.title) || stringValue(booking_facts.title) || stringValue(bookingFacts.title);
  const contentSections = record(record(document.content).sections);
  const inclusionsBlock = contentBlock(contentBlocks(contentSections, 'inclusions_exclusions'), 'twoColumnList');
  const bookingBlocks = contentBlocks(contentSections, 'booking_terms');
  const bookingParagraphIndex = bookingBlocks.findIndex((block) => stringValue(block.type) === 'paragraph');
  const bookingParagraph = bookingParagraphIndex >= 0 ? bookingBlocks[bookingParagraphIndex] : {};
  const bookingParagraphPath = `/content/sections/booking_terms/blocks/${bookingParagraphIndex >= 0 ? bookingParagraphIndex : 0}/text`;
  const bookingItems = bookingTermItems(bookingBlocks);
  const designer = record(document.designer);
  const assets = record(document.assets);
  const presentation = record(document.presentation);
  const overrides = record(presentation.copyOverrides);
  const mediaOverrides = record(presentation.mediaOverrides);
  const identityOverrides = record(presentation.identityOverrides);
  const brandName = stringValue(identityOverrides.brandName).trim() || profile.displayName;
  // Canonical quotation media is Fact-owned. Legacy presentation overrides are
  // read-only compatibility for frozen documents created before this contract.
  const quoteLogo = record(record(document.brand).logo);
  const logoAsset = assetUrl(quoteLogo) ? quoteLogo : presentationAsset(identityOverrides, 'logo', { url: profile.logoUrl });
  const logoUrl = assetUrl(logoAsset) || profile.logoUrl;
  const logoAlt = editable(stringValue(identityOverrides.logoAlt).trim() || brandName, '/presentation/identityOverrides/logoAlt', 'design', 'altText');
  const email = stringValue(designer.email);
  const phone = stringValue(designer.phone);
  const whatsappHref = phone ? `https://wa.me/${phone.replace(/[^\d]/g, '').replace(/^00/, '')}` : '';

  const routeSegments = recordList(route.staySegments).flatMap((segment, index) => {
    const rawCoordinates = Array.isArray(segment.coords) && segment.coords.length === 2 ? [Number(segment.coords[0]), Number(segment.coords[1])] as [number, number] : null;
    const coords = rawCoordinates && Number.isFinite(rawCoordinates[0]) && Number.isFinite(rawCoordinates[1]) && rawCoordinates[0] >= -90 && rawCoordinates[0] <= 90 && rawCoordinates[1] >= -180 && rawCoordinates[1] <= 180 ? rawCoordinates : null;
    if (!coords) return [];
    const base = `/route/staySegments/${index}`;
    const dayStart = Number(segment.dayStart);
    const dayEnd = Number(segment.dayEnd);
    const hasDayRange = Number.isSafeInteger(dayStart) && dayStart > 0 && Number.isSafeInteger(dayEnd) && dayEnd >= dayStart;
    const dayLabel = hasDayRange ? `${dayEnd === dayStart ? labels.daySingular : labels.dayPlural} ${dayStart}${dayEnd === dayStart ? '' : `–${dayEnd}`}` : stringValue(segment.daysLabel);
    const activityPreviews = recordList(segment.activityPreviews);
    const activityFallback = activityPreviews
      .map((item) => {
        const lbl = stringValue(item.label);
        const sum = stringValue(item.summary);
        return lbl && sum ? `${lbl}: ${sum}` : sum || lbl;
      })
      .filter(Boolean)
      .join(' ');
    const rawDesc = stringValue(segment.mapSegmentDesc) || activityFallback;
    return {
      sequence: String(index + 1).padStart(2, '0'),
      title: derivedCopy(stringValue(segment.displayName), `${base}/displayName`),
      description: contentCopy(rawDesc, `${base}/mapSegmentDesc`, ''),
      sidebarLabel: derivedCopy(stringValue(segment.daysLabel) || stringValue(segment.mapSegmentDuration), `${base}/daysLabel`),
      duration: derivedCopy(stringValue(segment.nightsLabel) || stringValue(segment.mapSegmentDuration), `${base}/nightsLabel`),
      hotelName: derivedCopy(stringValue(segment.hotelName), `${base}/hotelName`),
      coordinates: coords,
      dayLabel: derivedCopy(dayLabel, `${base}/dayStart`),
      city: derivedCopy(stringValue(segment.displayName), `${base}/displayName`),
      image: assetUrl(segment.hotelImage),
    };
  });
  const days = recordList(itinerary.days).map((day, index) => {
    const base = `/itinerary/days/${index}`;
    const images = record(day.images);
    const secondaryImages = [assetUrl(images.small1), assetUrl(images.small2)].filter(Boolean);
    const heroImage = assetUrl(images.hero);
    const galleryOverride = recordList(mediaOverrides[`itinerary.days.${index}.gallery`]);
    const canonicalGallery = recordList(images.carousel);
    const galleryAssets = canonicalGallery.length ? canonicalGallery : galleryOverride.length ? galleryOverride : [images.hero, images.small1, images.small2];
    const carouselImages = uniqueUrls(galleryAssets);
    const carouselImageAlts = galleryAssets
      .map((asset, itemIndex) => assetAlt(asset, `${base}/images/carousel/${itemIndex}/altText`, stringValue(day.title)))
      .filter((_, itemIndex) => Boolean(carouselImages[itemIndex]));
    const activities = listText(day.activities);
    const meals = listText(day.meals);
    const notes = listText(day.notes);
    const detailRows = [
      activities.length ? { label: editable(stringValue(day.labelHighlights) || labels.highlights, `${base}/labelHighlights`, 'fact'), value: contentCopy(activities.join(' · '), `${base}/activities`, '') } : null,
      day.overnight ? { label: designCopy(overrides, 'itinerary.overnightLabel', labels.overnight), value: editable(stringValue(day.overnight), `${base}/overnight`, 'fact') } : null,
      meals.length ? { label: designCopy(overrides, 'itinerary.mealsLabel', labels.meals), value: editable(meals.join(' · '), `${base}/meals`, 'fact') } : null,
    ].filter(Boolean) as Array<{ label: EditableText; value: EditableText }>;
    return {
      dayLabel: derivedCopy([`${labels.daySingular} ${String(day.dayNumber ?? index + 1).padStart(2, '0')}`, formatDisplayDate(stringValue(day.dayDate), lang)].filter(Boolean).join(' · '), `${base}/dayNumber`),
      title: contentCopy(stringValue(day.title), `${base}/title`, ''),
      description: listText(day.description).map((item, itemIndex) => contentCopy(item, `${base}/description/${itemIndex}`, '')),
      layoutType: day.layoutType === 'multi' ? 'multi' as const : 'single' as const,
      isAlternate: index % 2 === 1,
      highlights: contentCopy(activities.join(' · '), `${base}/activities`, ''),
      notes: notes.map((item, itemIndex) => editable(item, `${base}/notes/${itemIndex}`, 'fact')),
      overnight: editable(stringValue(day.overnight), `${base}/overnight`, 'fact'),
      meals: meals.map((item, itemIndex) => editable(item, `${base}/meals/${itemIndex}`, 'fact')),
      detailRows,
      heroImage,
      secondaryImages,
      carouselImages,
      carouselImageAlts,
      supportingImages: secondaryImages,
      supportingImageAlts: [images.small1, images.small2]
        .map((asset, itemIndex) => assetAlt(asset, `${base}/images/carousel/${itemIndex + 1}/altText`, stringValue(day.title)))
        .filter((_, itemIndex) => Boolean(secondaryImages[itemIndex])),
      city: derivedCopy(stringValue(day.segmentCity), `${base}/segmentCity`),
      carouselLabels: {
        previous: designCopy(overrides, 'carousel.previousImage', labels.previousImage, 'ariaLabel'),
        next: designCopy(overrides, 'carousel.nextImage', labels.nextImage, 'ariaLabel'),
        list: designCopy(overrides, 'carousel.itineraryImages', labels.itineraryImages, 'ariaLabel'),
        show: designCopy(overrides, 'carousel.showImage', labels.showImage, 'ariaLabel'),
      },
    };
  });
  const hotels = recordList(stays.hotels).map((hotel, index) => {
    const base = `/stays/hotels/${index}`;
    return {
      city: editable(stringValue(hotel.city), `${base}/city`, 'fact'),
      name: editable(stringValue(hotel.name), `${base}/name`, 'fact'),
      intro: factCopy(stringValue(hotel.introduction), `${base}/introduction`),
      dateRanges: [editable(stringValue(hotel.hotelDate), `${base}/hotelDate`, 'fact')].filter((item) => item.value),
      telephone: editable(stringValue(hotel.tel), `${base}/tel`, 'fact'),
      telephonePrefix: designCopy(overrides, 'hotels.telephonePrefix', labels.hotelTelephonePrefix),
      hotelImage: assetUrl(hotel.hotelImage) || assetUrl(record(mediaOverrides[`stays.hotels.${index}.hotelImage`])),
      hotelImageAlt: assetAlt(hotel.hotelImage, `${base}/hotelImage/altText`, stringValue(hotel.name)),
      roomImage: assetUrl(hotel.roomImage) || assetUrl(record(mediaOverrides[`stays.hotels.${index}.roomImage`])),
      roomImageAlt: assetAlt(hotel.roomImage, `${base}/roomImage/altText`, stringValue(hotel.roomType) || stringValue(hotel.name)),
      roomType: editable(stringValue(hotel.roomType), `${base}/roomType`, 'fact'),
      layoutParity: index % 2 === 0 ? 'odd' as const : 'even' as const,
      introVisibility: 'full' as const,
    };
  });
  const sourceSegments = recordList(route.staySegments);
  const mapCenter = routeSegments[0]?.coordinates;
  const isInteractiveAvailable = sourceSegments.length > 0 && routeSegments.length === sourceSegments.length && Boolean(mapCenter);

  return {
    theme,
    tokens: getBrandThemeTokensFromProfile(profile),
    colors: resolveColorSlotsFromProfile({ profile, theme, viewMode }),
    appChrome: { brandOptions: [{ key: profile.id, label: brandName, logoSrc: logoUrl }] },
    viewMode,
    lang,
    quotationNumber: stringValue(document.quotationNumber) || stringValue(document.quotation_number) || stringValue(document.id),
    pdfWhitespaceSlogan: designCopy(overrides, 'pdf.whitespaceSlogan', labels.pdfWhitespaceSlogan),
    page: {
      nav: {
        brandName: editable(brandName, '/presentation/identityOverrides/brandName', 'design'), brandLogo: editable(brandName, '/presentation/identityOverrides/brandName', 'design'), brandLogoSrc: logoUrl, brandLogoAlt: logoAlt,
        sectionAriaLabel: designCopy(overrides, 'a11y.brochureSections', labels.brochureSections, 'ariaLabel'),
        themeLabel: designCopy(overrides, 'nav.brochureTheme', labels.brochureTheme),
        languageOptions: [
          { code: 'en', label: designCopy(overrides, 'nav.language.en', 'English', 'actionLabel') },
          { code: 'vi', label: designCopy(overrides, 'nav.language.vi', 'Tiếng Việt', 'actionLabel') },
          { code: 'ar', label: designCopy(overrides, 'nav.language.ar', 'العربية', 'actionLabel') },
        ],
        links: [
          { label: designCopy(overrides, 'nav.routeMap', labels.routeMapNav), href: '#route-map' },
          { label: designCopy(overrides, 'nav.itinerary', labels.itineraryNav), href: '#itinerary' },
          { label: designCopy(overrides, 'nav.quotation', labels.quotationNav), href: '#pricing' },
          { label: designCopy(overrides, 'nav.terms', labels.termsNav), href: '#payment-terms' },
        ], actions: [], scrollStateBehavior: 'hero-overlay',
      },
      hero: {
        kicker: contentCopy(stringValue(narrative.coverKicker), '/narrative/coverKicker', labels.journeyOverviewKicker),
        title: contentCopy(stringValue(trip.title), '/trip/title', ''),
        lede: contentCopy(stringValue(trip.lede), '/trip/lede', ''),
        metaPrimary: contentCopy(stringValue(narrative.heroMeta1) || stringValue(trip.durationText), '/narrative/heroMeta1', stringValue(trip.durationText)),
        metaSecondary: contentCopy(stringValue(narrative.heroMeta2) || stringValue(trip.routeText), '/narrative/heroMeta2', stringValue(trip.routeText)),
        primaryCta: { label: designCopy(overrides, 'hero.primaryCta', labels.beginJourney, 'actionLabel'), href: '#route-map', emphasis: 'primary' },
        footerMeta: editable(brandName, '/presentation/identityOverrides/brandName', 'design'), backgroundImage: assetUrl(assets.hero) || assetUrl(record(mediaOverrides['assets.hero'])), backgroundImageAlt: assetAlt(assets.hero, '/assets/hero/altText', stringValue(trip.title) || brandName),
      },
      letter: {
        chapterKicker: designCopy(overrides, 'letter.kicker', labels.journeyOverviewKicker),
        title: contentCopy(stringValue(narrative.journeyOverviewTitle), '/narrative/journeyOverviewTitle', labels.journeyOverviewTitle),
        highlight: editable(customerParty || stringValue(narrative.letterHighlight), '/customer/partyLabel', 'fact'),
        decorAsset: assetUrl(assets.letterDecor) || assetUrl(record(mediaOverrides['assets.letterDecor'])) || '/assets/brands/indochine_icon/ruong_bac_thang.svg',
        greeting: editable(customerGreeting || stringValue(narrative.letterGreeting), '/customer/greetingName', 'fact'),
        intro: contentCopy(stringValue(narrative.letterIntro), '/narrative/letterIntro', ''),
        body: [stringValue(narrative.letterBody2)].filter(Boolean).map((item) => contentCopy(item, '/narrative/letterBody2', '')),
        outro: contentCopy(stringValue(narrative.letterOutro), '/narrative/letterOutro', ''),
        signatureName: contentCopy(stringValue(narrative.letterSignOff) || stringValue(designer.name), '/narrative/letterSignOff', ''),
        signatureRole: contentCopy((stringValue(narrative.letterSender) || stringValue(designer.subtitle)).toUpperCase(), '/narrative/letterSender', ''),
        signatureContactLine: derivedCopy([email, phone].filter(Boolean).join(' · '), '/designer/contact'),
      },
      routeMap: {
        title: contentCopy(stringValue(route.title), '/route/title', labels.routeMapTitle),
        description: contentCopy(stringValue(route.description), '/route/description', labels.routeMapDescription),
        segments: routeSegments, overviewAriaLabel: designCopy(overrides, 'a11y.routeMapOverview', labels.routeMapOverview, 'ariaLabel'), isInteractiveAvailable, unavailableMessage: designCopy(overrides, 'route.unavailableMessage', labels.routeMapUnavailable), mapModes: [editable(labels.classic, '/labels/classic', 'system')],
        mapModeOptions: [{ id: 'classic', label: editable(labels.classic, '/labels/classic', 'system') }], defaultMode: 'classic', initialActiveSegment: routeSegments[0]?.sequence ?? '01',
        mapViewport: { center: mapCenter, latSpan: 8, lngSpan: 8 },
        interactiveMarkers: routeSegments.map(({ sequence, coordinates, title, city, dayLabel }) => ({ sequence, coordinates, title, city, dayLabel })),
      },
      itineraryDivider: { kicker: designCopy(overrides, 'itinerary.kicker', labels.itineraryNav), title: contentCopy(stringValue(itinerary.title), '/itinerary/title', labels.itineraryTitle), tagline: contentCopy(stringValue(itinerary.description), '/itinerary/description', labels.itineraryDescription), image: assetUrl(assets.itineraryDivider) || assetUrl(record(mediaOverrides['assets.itineraryDivider'])), imageAlt: assetAlt(assets.itineraryDivider, '/assets/itineraryDivider/altText', stringValue(itinerary.title)), exploreLabel: designCopy(overrides, 'itinerary.explore', labels.explore, 'actionLabel'), exploreHref: '#itinerary' },
      itinerary: { kicker: designCopy(overrides, 'itinerary.kicker', labels.itineraryNav), title: contentCopy(stringValue(itinerary.title), '/itinerary/title', labels.itineraryTitle), description: contentCopy(stringValue(itinerary.description), '/itinerary/description', labels.itineraryDescription), days },
      hotels: { title: designCopy(overrides, 'stays.title', labels.stayPlanning), description: designCopy(overrides, 'stays.description', ''), cards: hotels, roomNotes: editable(stringValue(stays.roomNotes), '/stays/roomNotes', 'fact') },
      staysDivider: { image: assetUrl(assets.hotelDivider) || assetUrl(record(mediaOverrides['assets.hotelDivider'])), imageAlt: assetAlt(assets.hotelDivider, '/assets/hotelDivider/altText', labels.staysDividerTitle), kicker: designCopy(overrides, 'stays.kicker', labels.stayPlanning), title: designCopy(overrides, 'stays.title', labels.staysDividerTitle), tagline: designCopy(overrides, 'stays.tagline', labels.staysDividerTagline), closing: designCopy(overrides, 'stays.closing', labels.staysDividerClosing), pdfTitle: designCopy(overrides, 'stays.pdfTitle', labels.consideredInFull) },
      pricing: { kicker: designCopy(overrides, 'pricing.kicker', ''), title: designCopy(overrides, 'pricing.title', labels.pricingTitle), description: designCopy(overrides, 'pricing.description', labels.pricingDescription), importantNote: editable(listText(pricing.conditions).join(' · '), '/pricing/conditions', 'fact'), importantNoteLabel: designCopy(overrides, 'pricing.importantNoteLabel', labels.importantNote), confirmedMainOptionLabel: designCopy(overrides, 'pricing.confirmedMainOption', labels.confirmedMainOption), options: recordList(pricing.options).map((option, index) => { const currency = stringValue(option.currency).toUpperCase(); const perTravelerAmountMinor = positiveInteger(option.perTravelerAmountMinor); const groupTotalAmountMinor = positiveInteger(option.groupTotalAmountMinor); const legacyPerTraveler = stringValue(option.legacyPerPersonText) || stringValue(option.perPersonText); const legacyGroupTotal = stringValue(option.legacyTotalText) || stringValue(option.totalText); const typed = Boolean(stringValue(option.label).trim() && currency && perTravelerAmountMinor && groupTotalAmountMinor); const legacy = Boolean((stringValue(option.name) || stringValue(option.category)).trim() && legacyPerTraveler && legacyGroupTotal); if (!typed && !legacy) return null; return { index: index + 1, displayIndex: editable(String(index + 1).padStart(2, '0'), `/pricing/options/${index}`, 'fact'), label: editable(stringValue(option.label).trim() || stringValue(option.name).trim() || stringValue(option.category).trim() || `Option ${String(index + 1).padStart(2, '0')}`, `/pricing/options/${index}/label`, 'fact'), groupTotalPrice: editable(typed ? formatPriceMinor(groupTotalAmountMinor, currency, lang, PRICING_AMOUNT_LABELS[lang].total) : legacyGroupTotal, `/pricing/options/${index}/groupTotalAmountMinor`, 'fact'), perTravelerPrice: editable(typed ? formatPriceMinor(perTravelerAmountMinor, currency, lang, PRICING_AMOUNT_LABELS[lang].perTraveler) : legacyPerTraveler, `/pricing/options/${index}/perTravelerAmountMinor`, 'fact'), isConfirmedMainOption: option.isConfirmedMainOption === true || option.confirmedMainOption === true || (index === 0 && option.isMainOption !== false), isAlternativeOption: option.isAlternativeOption === true }; }).filter((option): option is NonNullable<typeof option> => option !== null) },
      inclusionsExclusions: { title: designCopy(overrides, 'inclusions.title', labels.inclusionsSectionTitle), inclusionsTitle: designCopy(overrides, 'inclusions.inclusionsTitle', stringValue(inclusionsBlock.leftTitle) || labels.inclusionsTitle), exclusionsTitle: designCopy(overrides, 'inclusions.exclusionsTitle', stringValue(inclusionsBlock.rightTitle) || labels.exclusionsTitle), inclusionsLead: designCopy(overrides, 'inclusions.lead', labels.inclusionsDescription), exclusionsLead: designCopy(overrides, 'exclusions.lead', ''), inclusions: listText(inclusionsBlock.leftItems).map((item, index) => editable(item, `/content/sections/inclusions_exclusions/blocks/0/leftItems/${index}`, 'fact')), exclusions: listText(inclusionsBlock.rightItems).map((item, index) => editable(item, `/content/sections/inclusions_exclusions/blocks/0/rightItems/${index}`, 'fact')) },
      paymentTerms: { kicker: '', title: editable(bookingTitleText || labels.bookingTermsTitle, '/content/sections/booking_terms/title', 'fact'), description: editable(stringValue(bookingParagraph.text) || labels.bookingTermsDescription, bookingParagraphPath, 'fact', 'richText'), cta: { label: designCopy(overrides, 'bookingTerms.cta', labels.sendEmail, 'actionLabel'), href: email ? `mailto:${email}` : '#designer', emphasis: 'secondary' }, terms: bookingItems.map(({ item, path }) => ({ label: editable(stringValue(item.label), `${path}/label`, 'fact'), bodyRichText: editable(stringValue(item.body), `${path}/body`, 'fact', 'richText') })) },
      designer: {
        kicker: factCopy(stringValue(designer.kicker), '/designer/kicker', DESIGNER_PRESENTATION_DEFAULTS.kicker),
        title: factCopy(stringValue(designer.title), '/designer/title', DESIGNER_PRESENTATION_DEFAULTS.title),
        quote: factCopy(stringValue(designer.quote), '/designer/quote', DESIGNER_PRESENTATION_DEFAULTS.quote),
        ctaBody: factCopy(stringValue(designer.ctaBody), '/designer/ctaBody', DESIGNER_PRESENTATION_DEFAULTS.ctaBody),
        name: derivedCopy(stringValue(designer.name) || 'Eddie', '/designer/name'),
        subtitle: editable(stringValue(designer.subtitle) || 'Trung Hieu Pham', '/designer/subtitle', 'fact'),
        signatureLabel: factCopy(stringValue(designer.signature), '/designer/signature', DESIGNER_PRESENTATION_DEFAULTS.signature),
        experienceNote: factCopy(stringValue(designer.experience), '/designer/experience', DESIGNER_PRESENTATION_DEFAULTS.experience),
        avatar: assetUrl(designer.image) || assetUrl(record(mediaOverrides['designer.avatar'])),
        avatarAlt: assetAlt(designer.image, '/designer/image/altText', stringValue(designer.name)),
        contactActions: [
          { label: editable(labels.chatWhatsapp, '/labels/chatWhatsapp', 'system', 'actionLabel'), href: whatsappHref, emphasis: 'primary' as const, caption: derivedCopy(phone, '/designer/phone') },
          { label: editable(labels.sendEmail, '/labels/sendEmail', 'system', 'actionLabel'), href: email ? `mailto:${email}` : '#', emphasis: 'secondary' as const, caption: derivedCopy(email, '/designer/email') },
        ].filter((action) => action.href && action.href !== '#'),
        supportBlocks: [],
      },
      footer: { text: contentCopy(stringValue(narrative.footerText), '/narrative/footerText', labels.footerText), secondaryMeta: derivedCopy(brandName, '/brand/displayName') },
      states: { loading: { title: editable(labels.loading, '/labels/loading', 'system'), body: editable(labels.loadingBody, '/labels/loadingBody', 'system') }, error: { title: editable(labels.errorTitle, '/labels/errorTitle', 'system'), body: editable(labels.errorBody, '/labels/errorBody', 'system'), actionLabel: editable(labels.tryAgain, '/labels/tryAgain', 'system', 'actionLabel') }, notFound: { title: editable(labels.notFoundTitle, '/labels/notFoundTitle', 'system'), body: editable(labels.notFoundBody, '/labels/notFoundBody', 'system'), actionLabel: editable(labels.returnHome, '/labels/returnHome', 'system', 'actionLabel') } },
    },
  };
}
