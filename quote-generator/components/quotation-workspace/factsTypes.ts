import { DESIGNER_PRESENTATION_DEFAULTS } from "../../config/designerPresentationDefaults";

export type SourceKind = "manual" | "dmc_handoff";
export type DestinationRef = {
  id: string;
  name: string;
  slug: string;
  matchedFrom?: string;
};

/**
 * The route shown at Trip level is a projection of the daily programme, not a
 * second editable route. Keep stable catalog identities and preserve first
 * appearance order while collapsing repeat overnight destinations.
 */
export function routeDestinationRefsFromItinerary(
  itinerary: Array<Pick<ItineraryDayFact, "destination_ref">>,
): DestinationRef[] {
  const seen = new Set<string>();
  const refs: DestinationRef[] = [];
  for (const day of itinerary) {
    const ref = day.destination_ref;
    if (!ref || seen.has(ref.id)) continue;
    seen.add(ref.id);
    refs.push(ref);
  }
  return refs;
}

export type ItineraryDayFact = {
  day_number: number | null;
  destination: string | null;
  destination_ref?: DestinationRef | null;
  summary: string | null;
  overnight: string | null;
  meals: string[];
  highlights: string[];
  notes: string[];
  sense_of_pace: string | null;
  display_date: string | null;
};

export type HotelFact = {
  accommodation_id: string | null;
  destination: string | null;
  destination_ref?: DestinationRef | null;
  name: string | null;
  room_type: string | null;
  check_in: string | null;
  check_out: string | null;
  intro: string | null;
  phone: string | null;
  display_city: string | null;
  display_date: string | null;
  hotel_asset: string | null;
  room_asset: string | null;
};

export type PricingOptionFact = {
  id: string;
  label: string;
  currency: string | null;
  per_traveler_amount_minor: number | null;
  group_total_amount_minor: number | null;
};

export type BookingItemFact = {
  key: string | null;
  label: string | null;
  body: string | null;
};

export type QuotationCreationPayload = QuotationFacts & {
  factMediaSlots: Array<{
    fieldId: string;
    value: { r2Key: string; status: "ready"; altText?: string; source?: "manual" | "auto" } | Array<{ r2Key: string; status: "ready"; altText?: string; source?: "manual" | "auto" }>;
  }>;
};

/**
 * Pre-create media state. It uses the same atom shape as the canonical media
 * API, but deliberately remains local until the quotation POST succeeds.
 */
export type DraftMediaRef = {
  r2Key: string;
  altText?: string;
  status?: "ready";
  source?: "manual" | "auto";
};
export type DraftMediaSlotValue = DraftMediaRef | DraftMediaRef[] | null;
export type DraftMediaSelections = Record<string, DraftMediaSlotValue>;

export type QuotationFacts = {
  source: {
    kind: SourceKind;
    opportunityId?: string;
    handoffId?: string;
    sourceVersion?: string;
  };
  opportunity_id?: string | null;
  brand_id: string | null;
  lang: "en" | "vi" | "ar" | null;
  presentation_options: {
    template_id: string | null;
    travel_designer_id: string | null;
  };
  trip_facts: {
    destinations: string[];
    destination_refs?: DestinationRef[];
    start_date: string | null;
    end_date: string | null;
    duration_days: number | null;
    duration_nights: number | null;
    itinerary: ItineraryDayFact[];
    special_requirements: string[];
    display_route_text: string | null;
    display_travel_dates: string | null;
  };
  customer_facts: {
    customer_name: string | null;
    adults: number | null;
    children: number | null;
    nationality: string | null;
    guest_profile: string | null;
    travel_style?: string | null;
    market: string | null;
    party_label: string | null;
    greeting_name: string | null;
  };
  service_facts: {
    hotels: HotelFact[];
    inclusions: string[];
    exclusions: string[];
    room_notes: string | null;
  };
  pricing_facts: {
    conditions: string[];
    options: PricingOptionFact[];
  };
  booking_facts: {
    title: string | null;
    description: string | null;
    items: BookingItemFact[];
  };
  finalization_facts: {
    required_title: string | null;
    after_confirmation_title: string | null;
    required_items: string[];
    after_confirmation_items: string[];
  };
  designer_facts: {
    seller_subtitle: string | null;
    designer_signature: string | null;
    designer_kicker: string | null;
    designer_quote: string | null;
    designer_experience: string | null;
    designer_title: string | null;
    cta_body: string | null;
  };
};

export type ResolvedFacts = {
  durationDays: number | null;
  durationNights: number | null;
  routeLabel: string;
  travelDatesLabel: string;
  partyLabel: string;
  pricing: {
    currency: string;
    total: number | null;
    perAdult: number | null;
    priceBasis: string;
  };
  defaults: { legalCopy: boolean };
  routeDestinationRefs?: DestinationRef[];
  itinerary?: Array<{
    dayNumber: number | null;
    destinationRef: DestinationRef | null;
    overnightRef: DestinationRef | null;
  }>;
  hotels?: Array<{ index: number; destinationRef: DestinationRef | null }>;
};

const BOOKING_FACT_DISALLOWED_TEXT = /[<>]/;

/**
 * Creation Facts are plain text. Keep this guard at the client serialization
 * boundary so a pasted legacy HTML fragment is reported before a request is
 * sent; the API enforces the same canonical contract for all other clients.
 */
export function assertBookingFactsArePlainText(items: BookingItemFact[]): void {
  const invalidIndex = items.findIndex((item) => {
    const body = item.body?.trim();
    return body !== undefined && body !== "" && BOOKING_FACT_DISALLOWED_TEXT.test(body);
  });
  if (invalidIndex !== -1) {
    throw new Error(
      `Booking term ${invalidIndex + 1} must be plain text. Remove HTML and write “more than” or “less than” instead of angle brackets.`,
    );
  }
}

/** Serialize only transport fields. Null, empty string and empty array remain distinct. */
export function serializeFactsForApi(
  rawFacts: QuotationFacts,
  factMediaSlots: QuotationCreationPayload["factMediaSlots"] = [],
): QuotationCreationPayload {
  const facts = ensureFactsDefaults(rawFacts);
  assertBookingFactsArePlainText(facts.booking_facts.items);
  const normalizedLines = (items: string[]) => items.map((item) => item.trim()).filter(Boolean);
  const tripFacts = { ...facts.trip_facts };
  delete tripFacts.destination_refs;
  return {
    ...facts,
    trip_facts: {
      ...tripFacts,
      destinations:
        facts.trip_facts.destination_refs?.map((ref) => ref.name) ??
        facts.trip_facts.destinations,
      special_requirements: normalizedLines(facts.trip_facts.special_requirements),
      itinerary: facts.trip_facts.itinerary.map((day) => {
        const serializedDay = { ...day, highlights: normalizedLines(day.highlights), meals: normalizedLines(day.meals), notes: normalizedLines(day.notes) };
        delete serializedDay.destination_ref;
        return serializedDay;
      }),
    },
    customer_facts: facts.customer_facts,
    service_facts: {
      ...facts.service_facts,
      inclusions: normalizedLines(facts.service_facts.inclusions),
      exclusions: normalizedLines(facts.service_facts.exclusions),
      hotels: facts.service_facts.hotels.map((hotel) => {
        const serializedHotel = { ...hotel };
        delete serializedHotel.destination_ref;
        return serializedHotel;
      }),
    },
    pricing_facts: {
      ...facts.pricing_facts,
      conditions: normalizedLines(facts.pricing_facts.conditions),
      // A blank row is an editor affordance, never quotation data.
      options: serializeCommercialOptions(facts.pricing_facts.options),
    },
    booking_facts: facts.booking_facts,
    finalization_facts: {
      ...facts.finalization_facts,
      required_items: normalizedLines(facts.finalization_facts.required_items),
      after_confirmation_items: normalizedLines(facts.finalization_facts.after_confirmation_items),
    },
    designer_facts: facts.designer_facts,
    factMediaSlots,
  };
}

/** Convert intake-only selections into the canonical create payload. */
export function serializeDraftMediaSelections(
  selections: DraftMediaSelections,
): QuotationCreationPayload["factMediaSlots"] {
  return Object.entries(selections).flatMap(([fieldId, value]) => {
    const values = Array.isArray(value) ? value : value ? [value] : [];
    const ready = values
      .filter((item) => typeof item?.r2Key === "string" && item.r2Key.trim())
      .map((item) => ({
        r2Key: item.r2Key.trim(),
        status: "ready" as const,
        ...(item.altText?.trim() ? { altText: item.altText.trim() } : {}),
        ...(item.source ? { source: item.source } : {}),
      }));
    if (!ready.length) return [];
    return [{ fieldId, value: Array.isArray(value) ? ready : ready[0] }];
  });
}

type ApiValidationIssue = {
  loc?: unknown;
  msg?: unknown;
};

/** Render an API error as text; never place response objects into JSX. */
export function formatApiError(detail: unknown, fallback: string): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (detail && typeof detail === "object") {
    const record = detail as { message?: unknown; errors?: unknown };
    if (typeof record.message === "string" && record.message.trim()) {
      return record.message;
    }
    const issues = Array.isArray(detail)
      ? detail
      : Array.isArray(record.errors)
        ? record.errors
        : [];
    const summaries = issues
      .filter((issue): issue is ApiValidationIssue =>
        Boolean(issue) && typeof issue === "object",
      )
      .slice(0, 3)
      .map((issue) => {
        const path = Array.isArray(issue.loc)
          ? issue.loc.filter((part) => part !== "body").join(".")
          : "";
        const message = typeof issue.msg === "string" ? issue.msg : "Invalid value";
        return path ? `${path}: ${message}` : message;
      });
    if (summaries.length) return summaries.join(" · ");
  }
  return fallback;
}

/** Rebuild editor identities from API-resolved catalog metadata after every reload. */
export function hydrateDestinationRefs(
  rawFacts: QuotationFacts,
  resolved?: ResolvedFacts,
): QuotationFacts {
  const facts = ensureFactsDefaults(rawFacts);
  if (!resolved) return facts;
  const resolvedDayRefs = (resolved.itinerary ?? [])
    .map((item) => item.destinationRef)
    .filter((ref): ref is DestinationRef => Boolean(ref));
  const routeRefs =
    resolved.routeDestinationRefs?.length
      ? resolved.routeDestinationRefs
      : resolvedDayRefs.length
        ? routeDestinationRefsFromItinerary(
            resolvedDayRefs.map((destination_ref) => ({ destination_ref })),
          )
        : facts.trip_facts.destination_refs;
  return {
    ...facts,
    trip_facts: {
      ...facts.trip_facts,
      destinations:
        routeRefs?.map((ref) => ref.name) ?? facts.trip_facts.destinations,
      destination_refs: routeRefs,
      itinerary: facts.trip_facts.itinerary.map((day, index) => ({
        ...day,
        destination_ref:
          resolved.itinerary?.[index]?.destinationRef ??
          day.destination_ref ??
          null,
      })),
    },
    service_facts: {
      ...facts.service_facts,
      hotels: facts.service_facts.hotels.map((hotel, index) => ({
        ...hotel,
        destination_ref:
          resolved.hotels?.[index]?.destinationRef ??
          hotel.destination_ref ??
          null,
      })),
    },
  };
}

export type QuotationOptions = {
  brands: Array<{ id: string; label: string }>;
  templates: Array<{ id: string; label: string; brandIds: string[] }>;
  languages: Array<{ id: "en" | "vi" | "ar"; label: string }>;
  travelDesigners?: Array<{
    id: string;
    name: string;
    email: string;
    phone: string;
    imageUrl?: string | null;
  }>;
  editableContract?: import("./useQuotationWorkspace").EditableBrochureContract;
};

export const FALLBACK_QUOTATION_OPTIONS: QuotationOptions = {
  brands: [
    { id: "vietnam_safar", label: "Vietnam Safar" },
    { id: "capella_travel", label: "Capella Travel" },
    { id: "selvara", label: "Selvara Journeys" },
  ],
  templates: [{ id: "vietnam_luxury_brosure.html", label: "Vietnam luxury brochure", brandIds: ["vietnam_safar", "capella_travel", "selvara"] }],
  languages: [{ id: "en", label: "EN" }, { id: "vi", label: "VI" }, { id: "ar", label: "AR" }],
  travelDesigners: [],
};

export const CURRENCY_OPTIONS = [
  { id: "USD", label: "USD — US Dollar" }, { id: "VND", label: "VND — Vietnamese Dong" }, { id: "EUR", label: "EUR — Euro" }, { id: "GBP", label: "GBP — British Pound" }, { id: "AUD", label: "AUD — Australian Dollar" },
];

/** Editable brochure policy defaults. They belong to the Fact form, never to labels.ts. */
export const BROCHURE_DEFAULT_INCLUSIONS = [
  "Airport transfer, international arrival fast-track assistance",
  "All private transfers with English-speaking guides mentioned in the itinerary",
  "Accommodations, experiences, admission fees, and exclusive arrangements mentioned in the detailed itinerary",
  "All meals mentioned in the itinerary",
  "Domestic flights",
] as const;

export const BROCHURE_DEFAULT_EXCLUSIONS = [
  "International flights",
  "Travel insurance",
  "Personal expenses",
  "Optional experiences not specified in the itinerary",
  "Tips and gratuities",
  "Any services not expressly listed as included",
] as const;

export const BROCHURE_DEFAULT_BOOKING_TERMS: readonly BookingItemFact[] = [
  {
    key: "deposit",
    label: "Deposit",
    body: "- A deposit of 30% of the total tour cost is required upon confirmation of the booking. This deposit is non-refundable.\n- For bookings confirmed within 60 days of arrival, full payment of 100% of the total tour cost is required at the time of confirmation.",
  },
  {
    key: "balance",
    label: "Balance",
    body: "- The remaining 70% balance must be paid no later than 60 days prior to the scheduled arrival date.",
  },
  {
    key: "cancellation",
    label: "Cancellation",
    body: "Written notice required. Cancellation fees apply based on arrival date:\n- More than 45 days prior: Deposit forfeited (30%)\n- 45 – 31 days prior: 50% of total tour cost\n- 30 – 20 days prior: 75% of total tour cost\n- Less than 20 days prior: 100% of total tour cost\n\nAny non-refundable payments, cancellation charges or penalties imposed by hotels, airlines, cruise operators and other service providers may also apply in addition to the cancellation fees stated above.",
  },
];

export const BROCHURE_DEFAULT_FINALIZATION = {
  required_title: null as string | null,
  after_confirmation_title: null as string | null,
  required_items: [] as string[],
  after_confirmation_items: [] as string[],
} as const;

export const MAX_COMMERCIAL_OPTIONS = 4;

const CURRENCY_FRACTION_DIGITS: Record<string, number> = { USD: 2, VND: 0, EUR: 2, GBP: 2, AUD: 2 };

export function currencyFractionDigits(currency: string | null): number {
  return CURRENCY_FRACTION_DIGITS[currency ?? ""] ?? 2;
}

export function minorAmountFromInput(value: string, currency: string | null): number | null {
  const amount = Number(value);
  if (!Number.isFinite(amount) || amount <= 0) return null;
  return Math.round(amount * 10 ** currencyFractionDigits(currency));
}

export function minorAmountToInput(value: number | null, currency: string | null): string {
  if (value === null || value <= 0) return "";
  return String(value / 10 ** currencyFractionDigits(currency));
}

export function formatMinorAmount(value: number | null, currency: string | null, locale: string): string {
  if (value === null || value <= 0 || !currency) return "";
  const divisor = 10 ** currencyFractionDigits(currency);
  const amount = value / divisor;
  const minDigits = amount % 1 === 0 ? 0 : currencyFractionDigits(currency);
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    minimumFractionDigits: minDigits,
    maximumFractionDigits: currencyFractionDigits(currency),
  }).format(amount);
}

export function createPricingOption(index = 1): PricingOptionFact {
  return {
    id: `pricing-option-${globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${index}`}`,
    label: `Option ${String(index).padStart(2, "0")}`,
    currency: null,
    per_traveler_amount_minor: null,
    group_total_amount_minor: null,
  };
}

export function dateForItineraryDay(startDate: string | null, dayNumber: number | null): string | null {
  if (!startDate || !dayNumber || dayNumber < 1 || !/^\d{4}-\d{2}-\d{2}$/.test(startDate)) return null;
  const date = new Date(`${startDate}T00:00:00.000Z`);
  if (Number.isNaN(date.getTime())) return null;
  date.setUTCDate(date.getUTCDate() + dayNumber - 1);
  return date.toISOString().slice(0, 10);
}

export function createItineraryDay({ index, startDate }: { index: number; startDate: string | null }): ItineraryDayFact {
  const dayNumber = index + 1;
  return {
    day_number: dayNumber, destination: null, destination_ref: null, summary: null, overnight: null,
    meals: [], highlights: [], notes: [], sense_of_pace: null,
    display_date: dateForItineraryDay(startDate, dayNumber),
  };
}

export function isRenderablePricingOption(option: PricingOptionFact): boolean {
  return Boolean(
    option.label.trim()
    && option.currency
    && (option.per_traveler_amount_minor ?? 0) > 0
    && (option.group_total_amount_minor ?? 0) > 0,
  );
}

export function serializeCommercialOptions(options: PricingOptionFact[]): PricingOptionFact[] {
  return options.filter((option) => Boolean(
    option.currency
    || option.per_traveler_amount_minor !== null
    || option.group_total_amount_minor !== null,
  ));
}

export const emptyFacts = (): QuotationFacts => ({
  source: { kind: "manual" },
  brand_id: null,
  lang: null,
  presentation_options: { template_id: null, travel_designer_id: null },
  trip_facts: {
    destinations: [],
    destination_refs: [],
    start_date: null,
    end_date: null,
    duration_days: null,
    duration_nights: null,
    itinerary: [],
    special_requirements: [],
    display_route_text: null, display_travel_dates: null,
  },
  customer_facts: {
    customer_name: null,
    adults: null,
    children: null,
    nationality: null,
    guest_profile: null,
    travel_style: null,
    market: null,
    party_label: null,
    greeting_name: null,
  },
  service_facts: {
    hotels: [],
    inclusions: [], exclusions: [],
    room_notes: null,
  },
  pricing_facts: {
    conditions: [],
    options: [],
  },
  booking_facts: { title: null, description: null, items: [] },
  finalization_facts: {
    required_title: null,
    after_confirmation_title: null,
    required_items: [],
    after_confirmation_items: [],
  },
  designer_facts: {
    seller_subtitle: null,
    designer_signature: DESIGNER_PRESENTATION_DEFAULTS.signature,
    designer_kicker: DESIGNER_PRESENTATION_DEFAULTS.kicker,
    designer_quote: DESIGNER_PRESENTATION_DEFAULTS.quote,
    designer_experience: DESIGNER_PRESENTATION_DEFAULTS.experience,
    designer_title: DESIGNER_PRESENTATION_DEFAULTS.title,
    cta_body: DESIGNER_PRESENTATION_DEFAULTS.ctaBody,
  },
});

/** Guarantees all nested fact sections exist even when loading legacy quotations or partial API payloads. */
export function ensureFactsDefaults(facts?: Partial<QuotationFacts> | null): QuotationFacts {
  const base = emptyFacts();
  if (!facts || typeof facts !== "object") return base;

  return {
    ...base,
    ...facts,
    source: {
      ...base.source,
      ...(facts.source ?? {}),
    },
    brand_id: facts.brand_id ?? base.brand_id,
    lang: facts.lang ?? base.lang,
    presentation_options: {
      ...base.presentation_options,
      ...(facts.presentation_options ?? {}),
    },
    trip_facts: {
      ...base.trip_facts,
      ...(facts.trip_facts ?? {}),
      destinations: facts.trip_facts?.destinations ?? base.trip_facts.destinations,
      destination_refs: facts.trip_facts?.destination_refs ?? base.trip_facts.destination_refs,
      itinerary: (facts.trip_facts?.itinerary ?? base.trip_facts.itinerary).map((day) => ({
        ...day,
        meals: day.meals ?? [],
        highlights: day.highlights ?? [],
        notes: day.notes ?? [],
      })),
      special_requirements: facts.trip_facts?.special_requirements ?? base.trip_facts.special_requirements,
    },
    customer_facts: {
      ...base.customer_facts,
      ...(facts.customer_facts ?? {}),
      travel_style: facts.customer_facts?.travel_style ?? facts.customer_facts?.guest_profile ?? base.customer_facts.travel_style,
      guest_profile: facts.customer_facts?.travel_style ?? facts.customer_facts?.guest_profile ?? base.customer_facts.guest_profile,
    },
    service_facts: {
      ...base.service_facts,
      ...(facts.service_facts ?? {}),
      hotels: (facts.service_facts?.hotels ?? base.service_facts.hotels).map((hotel) => ({
        ...hotel,
        accommodation_id: hotel.accommodation_id ?? null,
      })),
      inclusions: facts.service_facts?.inclusions ?? base.service_facts.inclusions,
      exclusions: facts.service_facts?.exclusions ?? base.service_facts.exclusions,
    },
    pricing_facts: {
      ...base.pricing_facts,
      ...(facts.pricing_facts ?? {}),
      conditions: facts.pricing_facts?.conditions ?? base.pricing_facts.conditions,
      options: (facts.pricing_facts?.options ?? base.pricing_facts.options).map((option, index) => ({
        id: option.id ?? `pricing-option-legacy-${index + 1}`,
        label: option.label ?? `Option ${String(index + 1).padStart(2, "0")}`,
        currency: option.currency ?? null,
        per_traveler_amount_minor: option.per_traveler_amount_minor ?? null,
        group_total_amount_minor: option.group_total_amount_minor ?? null,
      })),
    },
    booking_facts: {
      ...base.booking_facts,
      ...(facts.booking_facts ?? {}),
      items: (facts.booking_facts?.items ?? base.booking_facts.items).map((item) => ({
        ...item,
      })),
    },
    finalization_facts: {
      ...base.finalization_facts,
      ...(facts.finalization_facts ?? {}),
      required_items: facts.finalization_facts?.required_items ?? base.finalization_facts.required_items,
      after_confirmation_items: facts.finalization_facts?.after_confirmation_items ?? base.finalization_facts.after_confirmation_items,
    },
    designer_facts: {
      ...base.designer_facts,
      ...(facts.designer_facts ?? {}),
    },
  };
}

/** Fresh mutable Facts state for a new brochure. Existing quotations are never defaulted again. */
export const createBrochureFacts = (): QuotationFacts => {
  const facts = emptyFacts();
  return {
    ...facts,
    service_facts: { ...facts.service_facts, inclusions: [...BROCHURE_DEFAULT_INCLUSIONS], exclusions: [...BROCHURE_DEFAULT_EXCLUSIONS] },
    booking_facts: {
      title: "Booking & Payment Terms",
      description: "Commercial conditions, deposits, and cancellation policy for this booking.",
      items: BROCHURE_DEFAULT_BOOKING_TERMS.map((item) => ({ ...item })),
    },
    finalization_facts: {
      ...facts.finalization_facts,
      ...BROCHURE_DEFAULT_FINALIZATION,
      required_items: [...BROCHURE_DEFAULT_FINALIZATION.required_items],
      after_confirmation_items: [...BROCHURE_DEFAULT_FINALIZATION.after_confirmation_items],
    },
  };
};
