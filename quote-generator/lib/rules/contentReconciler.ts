/**
 * Pure domain rules for Content Studio reconciliation, default candidate derivation,
 * and PDF printable A4 text budget validation (Layer 1).
 *
 * Guarantees invariant synchronization between Facts, Content Candidates,
 * and Document Models with zero React dependencies.
 */

import type { LanguageCode } from '../../display/contracts.ts';
import { getLanguageLabels } from '../../display/labels.ts';
import type { QuotationFacts } from '../../components/quotation-workspace/factsTypes.ts';
import { formatRouteString, deriveRouteFromItinerary } from './routeRules.ts';
import type { CanonicalDay, CanonicalTrip } from './tripReconciler.ts';
import contentBudgetsData from '../../config/contentBudgets.json' with { type: 'json' };

export type PdfTextBudgetResult = {
  isValid: boolean;
  current: number;
  max: number;
  overflow: number;
};

const pdfCeilings = (contentBudgetsData?.pdfCeilings || {}) as Record<string, number>;

export const PDF_TEXT_BUDGETS: Record<string, number> = {
  ...pdfCeilings,
  day_title: pdfCeilings.day_title ?? 170,
  'itinerary:day:title': pdfCeilings['day-title'] ?? 170,
  dayTitle: pdfCeilings.day_title ?? 170,
  day_description: pdfCeilings.day_description ?? 1150,
  'itinerary:day:description': pdfCeilings['day-description'] ?? 1150,
  dayDescription: pdfCeilings.day_description ?? 1150,
  daySummary: pdfCeilings.day_description ?? 1150,
  hotel_intro: pdfCeilings.hotel_intro ?? 300,
  hotelIntro: pdfCeilings.hotel_intro ?? 300,
  hotel_total_copy: pdfCeilings.hotel_total_copy ?? 2100,
  hotelCopy: pdfCeilings.hotel_total_copy ?? 2100,
  hero_title: pdfCeilings.hero_title ?? 160,
  trip_title: pdfCeilings.trip_title ?? 160,
  heroTitle: pdfCeilings.hero_title ?? 160,
  hero_lede: pdfCeilings.hero_lede ?? 500,
  heroLede: pdfCeilings.hero_lede ?? 500,
  route_stop_description: pdfCeilings.route_stop_description ?? 500,
  mapSegmentDesc: pdfCeilings.route_stop_description ?? 500,
  overview_highlight: pdfCeilings.overview_highlight ?? 500,
  overview_letter_total: pdfCeilings.overview_letter_total ?? 4000,
  payment_terms_max_count: pdfCeilings.payment_terms_max_count ?? 4,
  payment_term_body: pdfCeilings.payment_term_body ?? 1600,
};

export const DEFAULT_BUDGET_LIMIT = 1600;

/**
 * Helper to derive the budget metric key for a given scope, fieldId, and path.
 */
export function deriveBudgetType(
  scope?: string | null,
  fieldId?: string | null,
  path?: Array<string | number> | null
): string {
  const pathStr = (path || []).join('.').toLowerCase();
  const idStr = (fieldId || '').toLowerCase();

  if (idStr === 'route-stop-descriptions' || pathStr.includes('mapsegmentdescriptions')) {
    return 'route_stop_description';
  }

  if (scope?.startsWith('itinerary:day:')) {
    if (idStr.includes('title') || pathStr.includes('title')) {
      return 'itinerary:day:title';
    }
    return 'itinerary:day:description';
  }

  if (scope === 'hero') {
    if (idStr.includes('title') || pathStr.includes('title')) {
      return 'hero_title';
    }
    return 'hero_lede';
  }

  if (scope === 'hotel_plan') {
    if (idStr.includes('intro') || pathStr.includes('intro')) {
      return 'hotel_intro';
    }
    return 'hotel_total_copy';
  }

  if (scope === 'route') {
    if (idStr.includes('title') || pathStr.includes('title')) {
      return 'hero_title';
    }
    return 'hero_lede';
  }

  if (scope === 'overview_letter' || scope === 'overview') {
    if (idStr.includes('highlight') || pathStr.includes('highlight')) {
      return 'overview_highlight';
    }
    if (idStr.includes('title') || pathStr.includes('title')) {
      return 'hero_title';
    }
    return 'hero_lede';
  }

  if (fieldId && PDF_TEXT_BUDGETS[fieldId]) {
    return fieldId;
  }

  return 'default';
}

/**
 * Validate text length against fixed A4 PDF compositor printable budgets.
 */
export function validatePdfTextBudget(
  scopeOrType: string,
  text: string | string[] | null | undefined
): PdfTextBudgetResult {
  const max = PDF_TEXT_BUDGETS[scopeOrType] ?? DEFAULT_BUDGET_LIMIT;

  let textString = '';
  if (Array.isArray(text)) {
    textString = text
      .map((item) => (typeof item === 'string' ? item : String(item ?? '')))
      .filter((s) => s.length > 0)
      .join(' ');
  } else if (text !== null && text !== undefined) {
    textString = String(text);
  }

  const current = textString.trim().length;
  const isValid = current <= max;
  const overflow = Math.max(0, current - max);

  return {
    isValid,
    current,
    max,
    overflow,
  };
}

/**
 * Convert facts or trip into a canonical trip object helper.
 */
function toTripHelper(factsOrTrip?: QuotationFacts | CanonicalTrip | null): CanonicalTrip {
  if (!factsOrTrip) {
    return {
      startDate: null,
      endDate: null,
      durationDays: null,
      durationNights: null,
      destinations: [],
      displayRouteText: null,
      itinerary: [],
      lang: 'en',
    };
  }
  if ('itinerary' in factsOrTrip && Array.isArray(factsOrTrip.itinerary)) {
    return factsOrTrip as CanonicalTrip;
  }
  const facts = factsOrTrip as QuotationFacts;
  const trip = facts.trip_facts ?? { itinerary: [] };
  return {
    startDate: trip.start_date ?? null,
    endDate: trip.end_date ?? null,
    durationDays: trip.duration_days ?? null,
    durationNights: trip.duration_nights ?? null,
    destinations: trip.destinations ?? [],
    displayRouteText: trip.display_route_text ?? null,
    itinerary: (trip.itinerary ?? []).map((d, index) => ({
      day_number: d.day_number ?? index + 1,
      destination: d.destination ?? null,
      overnight: d.overnight ?? d.destination ?? null,
      display_date: d.display_date ?? null,
      summary: d.summary ?? null,
      meals: d.meals ?? [],
      highlights: d.highlights ?? [],
      notes: d.notes ?? [],
    })),
    lang: facts.lang || 'en',
  };
}

/**
 * Localized day title generator helper.
 */
function formatDayLabel(dayNumber: number, destination: string | null | undefined, lang: LanguageCode): string {
  const prefix = lang === 'vi' ? 'Ngày' : lang === 'ar' ? 'اليوم' : 'Day';
  if (destination && destination.trim()) {
    return `${prefix} ${dayNumber} · ${destination.trim()}`;
  }
  return `${prefix} ${dayNumber}`;
}

/**
 * Pure function: Generate standardized default candidate fallback data for a given scope.
 */
export function deriveDefaultCandidate(
  scope: string,
  factsOrTrip?: QuotationFacts | CanonicalTrip | null,
  langCode?: string | null
): Record<string, unknown> {
  const lang: LanguageCode = langCode === 'vi' || langCode === 'ar' ? langCode : 'en';
  const labels = getLanguageLabels(lang);
  const trip = toTripHelper(factsOrTrip);
  const routeMeta = deriveRouteFromItinerary(trip.itinerary);
  const destinations =
    trip.destinations && trip.destinations.length > 0
      ? trip.destinations
      : routeMeta.destinations;
  const routeText = trip.displayRouteText || formatRouteString(destinations);

  if (scope === 'hero') {
    const title =
      destinations.length > 0
        ? `${destinations[0]} & Beyond`
        : lang === 'vi'
        ? 'Hành Trình Khám Phá'
        : lang === 'ar'
        ? 'رحلة استكشافية'
        : 'Journey of Discovery';
    const durationText =
      trip.durationDays && trip.durationDays > 0
        ? `${trip.durationDays} ${trip.durationDays > 1 ? labels.dayPlural : labels.daySingular}`
        : '';

    return {
      trip: {
        title,
        lede: labels.routeMapLead,
      },
      narrative: {
        coverKicker: labels.journeyOverviewKicker,
        heroMeta1: durationText,
        heroMeta2: routeText,
        footerText: labels.footerText,
      },
    };
  }

  if (scope === 'overview_letter' || scope === 'overview') {
    return {
      narrative: {
        journeyOverviewTitle: labels.journeyOverviewTitle,
        letterHighlight: labels.routeMapLead,
        letterGreeting: lang === 'vi' ? 'Kính gửi Quý khách' : lang === 'ar' ? 'عزيزي الضيف' : 'Dear Guest',
        letterIntro: labels.staysDividerTagline,
        letterBody2: labels.itineraryDescription,
        letterOutro: labels.staysDividerClosing,
        letterSignOff: lang === 'vi' ? 'Trân trọng' : lang === 'ar' ? 'مع خالص التحيات' : 'Warm regards',
        letterSender: 'Travel Designer',
      },
    };
  }

  if (scope === 'route') {
    const segmentCount = Math.max(1, destinations.length);
    const mapSegmentDescriptions: string[] = [];
    for (let i = 0; i < segmentCount; i++) {
      const dest = destinations[i];
      if (dest) {
        mapSegmentDescriptions.push(
          lang === 'vi'
            ? `Khám phá và trải nghiệm vẻ đẹp tại ${dest}.`
            : lang === 'ar'
            ? `استكشف وتجربة سحر ${dest}.`
            : `Explore and experience the highlights of ${dest}.`
        );
      } else {
        mapSegmentDescriptions.push('');
      }
    }

    return {
      route: {
        title: labels.routeMapTitle,
        description: labels.routeMapDescription,
        mapSegmentDescriptions,
      },
    };
  }

  if (scope === 'itinerary') {
    return {
      itinerary: {
        title: labels.itineraryTitle,
        description: labels.itineraryDescription,
      },
    };
  }

  if (scope.startsWith('itinerary:day:')) {
    const dayNumber = parseInt(scope.split(':').pop() || '1', 10);
    const day: CanonicalDay | undefined =
      trip.itinerary.find((d) => d.day_number === dayNumber) ?? trip.itinerary[dayNumber - 1];

    const title = formatDayLabel(dayNumber, day?.destination, lang);
    const descriptionParagraphs: string[] = [];
    if (day?.summary && day.summary.trim()) {
      descriptionParagraphs.push(day.summary.trim());
    } else {
      descriptionParagraphs.push(
        lang === 'vi'
          ? `Chương trình tham quan và trải nghiệm tại ${day?.destination || 'điểm đến'}.`
          : lang === 'ar'
          ? `برنامج الجولة والتجارب في ${day?.destination || 'الوجهة'}.`
          : `Curated experiences and highlights in ${day?.destination || 'the destination'}.`
      );
    }

    const activities = day?.highlights && day.highlights.length > 0 ? [...day.highlights] : [];

    return {
      dayNumber,
      title,
      description: descriptionParagraphs,
      activities,
    };
  }

  if (scope === 'hotel_plan') {
    return {
      stays: {
        hotels: [],
        roomNotes: '',
      },
    };
  }

  if (scope === 'finalization') {
    return {
      content: {
        sections: {
          finalization: {
            blocks: [],
          },
        },
      },
    };
  }

  return {};
}

/**
 * Pure function: Reconcile an existing content candidate with Facts to maintain 100% invariant alignment.
 * Resizes map segment descriptions to match route segments, ensures day-level candidate alignment,
 * and fills missing narrative keys while preserving user modifications.
 */
export function reconcileCandidateWithFacts(
  scope: string,
  candidate: Record<string, unknown> | undefined | null,
  canonicalTripOrFacts?: CanonicalTrip | QuotationFacts | null,
  langCode?: string | null
): Record<string, unknown> {
  const lang: LanguageCode = langCode === 'vi' || langCode === 'ar' ? langCode : 'en';
  const trip = toTripHelper(canonicalTripOrFacts);
  const defaultCandidate = deriveDefaultCandidate(scope, trip, lang);

  if (!candidate || Object.keys(candidate).length === 0) {
    return defaultCandidate;
  }

  if (scope === 'route') {
    const routeObj = (candidate.route && typeof candidate.route === 'object'
      ? (candidate.route as Record<string, unknown>)
      : candidate) as Record<string, unknown>;

    const defaultRoute = (defaultCandidate.route as Record<string, unknown>) || {};
    const defaultDescriptions = (defaultRoute.mapSegmentDescriptions as string[]) || [];

    const existingDescriptions = Array.isArray(routeObj.mapSegmentDescriptions)
      ? (routeObj.mapSegmentDescriptions as string[])
      : [];

    const targetLength = defaultDescriptions.length;
    const reconciledDescriptions: string[] = [];

    for (let i = 0; i < targetLength; i++) {
      if (i < existingDescriptions.length && typeof existingDescriptions[i] === 'string' && existingDescriptions[i].trim()) {
        reconciledDescriptions.push(existingDescriptions[i]);
      } else if (i < defaultDescriptions.length) {
        reconciledDescriptions.push(defaultDescriptions[i]);
      } else {
        reconciledDescriptions.push('');
      }
    }

    const title =
      typeof routeObj.title === 'string' && routeObj.title.trim()
        ? routeObj.title.trim()
        : (defaultRoute.title as string);

    const description =
      typeof routeObj.description === 'string' && routeObj.description.trim()
        ? routeObj.description.trim()
        : (defaultRoute.description as string);

    return {
      ...candidate,
      route: {
        ...routeObj,
        title,
        description,
        mapSegmentDescriptions: reconciledDescriptions,
      },
    };
  }

  if (scope.startsWith('itinerary:day:')) {
    const dayNumber = parseInt(scope.split(':').pop() || '1', 10);
    const day: CanonicalDay | undefined =
      trip.itinerary.find((d) => d.day_number === dayNumber) ?? trip.itinerary[dayNumber - 1];

    const defaultTitle = formatDayLabel(dayNumber, day?.destination, lang);
    const title =
      typeof candidate.title === 'string' && candidate.title.trim()
        ? candidate.title.trim()
        : defaultTitle;

    let description: string[] = [];
    if (Array.isArray(candidate.description) && candidate.description.length > 0) {
      description = candidate.description.map((item) => String(item ?? ''));
    } else if (typeof candidate.description === 'string' && candidate.description.trim()) {
      description = [candidate.description.trim()];
    } else if (defaultCandidate.description && Array.isArray(defaultCandidate.description)) {
      description = defaultCandidate.description as string[];
    }

    let activities: string[] = [];
    if (Array.isArray(candidate.activities)) {
      activities = candidate.activities.map((item) => String(item ?? ''));
    } else if (day?.highlights && day.highlights.length > 0) {
      activities = [...day.highlights];
    }

    return {
      ...candidate,
      dayNumber,
      title,
      description,
      activities,
    };
  }

  if (scope === 'hero') {
    const tripObj = (candidate.trip as Record<string, unknown>) || {};
    const narrativeObj = (candidate.narrative as Record<string, unknown>) || {};
    const defTrip = (defaultCandidate.trip as Record<string, unknown>) || {};
    const defNarrative = (defaultCandidate.narrative as Record<string, unknown>) || {};

    return {
      ...candidate,
      trip: {
        ...defTrip,
        ...tripObj,
        title: (tripObj.title as string) || (defTrip.title as string),
        lede: (tripObj.lede as string) || (defTrip.lede as string),
      },
      narrative: {
        ...defNarrative,
        ...narrativeObj,
        coverKicker: (narrativeObj.coverKicker as string) || (defNarrative.coverKicker as string),
        heroMeta1: (narrativeObj.heroMeta1 as string) || (defNarrative.heroMeta1 as string),
        heroMeta2: (narrativeObj.heroMeta2 as string) || (defNarrative.heroMeta2 as string),
        footerText: (narrativeObj.footerText as string) || (defNarrative.footerText as string),
      },
    };
  }

  if (scope === 'overview_letter' || scope === 'overview') {
    const narrativeObj = (candidate.narrative as Record<string, unknown>) || {};
    const defNarrative = (defaultCandidate.narrative as Record<string, unknown>) || {};

    return {
      ...candidate,
      narrative: {
        ...defNarrative,
        ...narrativeObj,
        journeyOverviewTitle:
          (narrativeObj.journeyOverviewTitle as string) || (defNarrative.journeyOverviewTitle as string),
        letterHighlight:
          (narrativeObj.letterHighlight as string) || (defNarrative.letterHighlight as string),
        letterGreeting:
          (narrativeObj.letterGreeting as string) || (defNarrative.letterGreeting as string),
        letterIntro:
          (narrativeObj.letterIntro as string) || (defNarrative.letterIntro as string),
        letterBody2:
          (narrativeObj.letterBody2 as string) || (defNarrative.letterBody2 as string),
        letterOutro:
          (narrativeObj.letterOutro as string) || (defNarrative.letterOutro as string),
        letterSignOff:
          (narrativeObj.letterSignOff as string) || (defNarrative.letterSignOff as string),
        letterSender:
          (narrativeObj.letterSender as string) || (defNarrative.letterSender as string),
      },
    };
  }

  if (scope === 'itinerary') {
    const itineraryObj = (candidate.itinerary as Record<string, unknown>) || {};
    const defItinerary = (defaultCandidate.itinerary as Record<string, unknown>) || {};

    return {
      ...candidate,
      itinerary: {
        ...defItinerary,
        ...itineraryObj,
        title: (itineraryObj.title as string) || (defItinerary.title as string),
        description: (itineraryObj.description as string) || (defItinerary.description as string),
      },
    };
  }

  return {
    ...defaultCandidate,
    ...candidate,
  };
}

/**
 * Pure function: Scan entire document for PDF layout budget violations.
 * Matches backend `_pdf_layout_preflight` rules.
 */
export function checkDocumentPdfTextBudgets(document: Record<string, unknown>): Array<{
  path: string;
  scope: string;
  field: string;
  result: PdfTextBudgetResult;
}> {
  const violations: Array<{
    path: string;
    scope: string;
    field: string;
    result: PdfTextBudgetResult;
  }> = [];

  const itinerary = ((document.itinerary as Record<string, unknown>)?.days as Array<Record<string, unknown>>) || [];
  itinerary.forEach((day, index) => {
    if (!day || typeof day !== 'object') return;
    const title = String(day.title || '');
    const titleCheck = validatePdfTextBudget('day_title', title);
    if (!titleCheck.isValid) {
      violations.push({
        path: `/itinerary/days/${index}/title`,
        scope: `itinerary:day:${day.dayNumber ?? index + 1}`,
        field: 'title',
        result: titleCheck,
      });
    }

    const description = day.description;
    const descCheck = validatePdfTextBudget('day_description', description as string | string[]);
    if (!descCheck.isValid) {
      violations.push({
        path: `/itinerary/days/${index}/description`,
        scope: `itinerary:day:${day.dayNumber ?? index + 1}`,
        field: 'description',
        result: descCheck,
      });
    }
  });

  const hotels = ((document.stays as Record<string, unknown>)?.hotels as Array<Record<string, unknown>>) || [];
  hotels.forEach((hotel, index) => {
    if (!hotel || typeof hotel !== 'object') return;
    const copyKeys = ['name', 'city', 'hotelDate', 'tel', 'roomType', 'intro'];
    const totalCopy = copyKeys.map((k) => String(hotel[k] || '')).join(' ');
    const copyCheck = validatePdfTextBudget('hotel_total_copy', totalCopy);
    if (!copyCheck.isValid) {
      violations.push({
        path: `/stays/hotels/${index}`,
        scope: 'hotel_plan',
        field: 'hotel_total_copy',
        result: copyCheck,
      });
    }
  });

  const narrative = (document.narrative as Record<string, unknown>) || {};
  if (typeof narrative === 'object' && narrative !== null) {
    const highlight = String(narrative.letterHighlight || '');
    const highlightCheck = validatePdfTextBudget('overview_highlight', highlight);
    if (!highlightCheck.isValid) {
      violations.push({
        path: '/narrative/letterHighlight',
        scope: 'overview_letter',
        field: 'letterHighlight',
        result: highlightCheck,
      });
    }

    const letterKeys = ['journeyOverviewTitle', 'letterGreeting', 'letterIntro', 'letterBody2', 'letterOutro', 'letterSignOff', 'letterSender', 'letterHighlight'];
    const totalLetterCopy = letterKeys.map((k) => String(narrative[k] || '')).join(' ');
    const totalLetterCheck = validatePdfTextBudget('overview_letter_total', totalLetterCopy);
    if (!totalLetterCheck.isValid) {
      violations.push({
        path: '/narrative',
        scope: 'overview_letter',
        field: 'overview_letter_total',
        result: totalLetterCheck,
      });
    }
  }

  const route = (document.route as Record<string, unknown>) || {};
  if (typeof route === 'object' && route !== null) {
    const segmentDescs = Array.isArray(route.mapSegmentDescriptions)
      ? (route.mapSegmentDescriptions as unknown[]).map(String)
      : [];
    segmentDescs.forEach((desc, index) => {
      const segCheck = validatePdfTextBudget('route_stop_description', desc);
      if (!segCheck.isValid) {
        violations.push({
          path: `/route/mapSegmentDescriptions/${index}`,
          scope: 'route',
          field: `mapSegmentDescriptions.${index}`,
          result: segCheck,
        });
      }
    });
  }

  const booking = (document.booking as Record<string, unknown>) || {};
  const bookingItems = (Array.isArray(booking.items) ? booking.items : Array.isArray(booking.terms) ? booking.terms : Array.isArray(document.booking_terms) ? (document.booking_terms as unknown[]) : []) as Array<Record<string, unknown>>;
  if (bookingItems.length > 4) {
    violations.push({
      path: '/booking/items',
      scope: 'booking_terms',
      field: 'items_count',
      result: {
        isValid: false,
        current: bookingItems.length,
        max: 4,
        overflow: bookingItems.length - 4,
      },
    });
  }
  bookingItems.forEach((term, index) => {
    if (!term || typeof term !== 'object') return;
    const body = String(term.body || term.bodyRichText || '');
    const bodyCheck = validatePdfTextBudget('payment_term_body', body);
    if (!bodyCheck.isValid) {
      violations.push({
        path: `/booking/items/${index}/body`,
        scope: 'booking_terms',
        field: `items.${index}.body`,
        result: bodyCheck,
      });
    }
  });

  return violations;
}

/**
 * Pure function: Validate a candidate object for a specific scope.
 */
export function validateCandidatePdfBudget(
  scope: string,
  candidate: Record<string, unknown> | null | undefined
): {
  isValid: boolean;
  violations: Array<{ field: string; result: PdfTextBudgetResult }>;
} {
  if (!candidate || typeof candidate !== 'object') {
    return { isValid: true, violations: [] };
  }

  const violations: Array<{ field: string; result: PdfTextBudgetResult }> = [];

  if (scope.startsWith('itinerary:day:')) {
    const title = String(candidate.title || '');
    const titleCheck = validatePdfTextBudget('day_title', title);
    if (!titleCheck.isValid) {
      violations.push({ field: 'title', result: titleCheck });
    }
    const description = candidate.description;
    const descCheck = validatePdfTextBudget('day_description', description as string | string[]);
    if (!descCheck.isValid) {
      violations.push({ field: 'description', result: descCheck });
    }
  } else if (scope === 'overview_letter') {
    const narrative = (candidate.narrative as Record<string, unknown>) || candidate;
    const highlight = String(narrative.letterHighlight || '');
    const highlightCheck = validatePdfTextBudget('overview_highlight', highlight);
    if (!highlightCheck.isValid) {
      violations.push({ field: 'letterHighlight', result: highlightCheck });
    }
    const letterKeys = ['journeyOverviewTitle', 'letterGreeting', 'letterIntro', 'letterBody2', 'letterOutro', 'letterSignOff', 'letterSender', 'letterHighlight'];
    const totalLetterCopy = letterKeys.map((k) => String(narrative[k] || '')).join(' ');
    const totalLetterCheck = validatePdfTextBudget('overview_letter_total', totalLetterCopy);
    if (!totalLetterCheck.isValid) {
      violations.push({ field: 'overview_letter_total', result: totalLetterCheck });
    }
  } else if (scope === 'route') {
    const route = (candidate.route as Record<string, unknown>) || candidate;
    const segmentDescs = Array.isArray(route.mapSegmentDescriptions)
      ? (route.mapSegmentDescriptions as unknown[]).map(String)
      : [];
    segmentDescs.forEach((desc, index) => {
      const segCheck = validatePdfTextBudget('route_stop_description', desc);
      if (!segCheck.isValid) {
        violations.push({ field: `mapSegmentDescriptions.${index}`, result: segCheck });
      }
    });
  } else if (scope === 'hero') {
    const trip = (candidate.trip as Record<string, unknown>) || candidate;
    const title = String(trip.title || '');
    const titleCheck = validatePdfTextBudget('hero_title', title);
    if (!titleCheck.isValid) {
      violations.push({ field: 'title', result: titleCheck });
    }
    const lede = String(trip.lede || '');
    const ledeCheck = validatePdfTextBudget('hero_lede', lede);
    if (!ledeCheck.isValid) {
      violations.push({ field: 'lede', result: ledeCheck });
    }
  }

  return {
    isValid: violations.length === 0,
    violations,
  };
}

export const contentReconciler = {
  validatePdfTextBudget,
  deriveBudgetType,
  deriveDefaultCandidate,
  reconcileCandidateWithFacts,
  checkDocumentPdfTextBudgets,
  validateCandidatePdfBudget,
  PDF_TEXT_BUDGETS,
  DEFAULT_BUDGET_LIMIT,
};
