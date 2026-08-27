import { QuotationApiError, quotationFetch } from "./apiError.ts";
import type { PricingOptionFact, QuotationFacts } from "../components/quotation-workspace/factsTypes.ts";
import { staysAdapter } from "./rules/staysAdapter.ts";
import { staysReconciler } from "./rules/staysReconciler.ts";

const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? "";

export type FastTrackStage =
  | "create"
  | "facts_media"
  | "content_generation"
  | "complete";

export type FastTrackProgress = {
  stage: FastTrackStage;
  message: string;
  current?: number;
  total?: number;
};

export type RunFastTrackOptions = {
  requestId: string | null;
  facts: QuotationFacts;
  existingQuotation?: { quotationId: string; baseRevision: number } | null;
  idempotencyKey?: string;
  onProgress?: (progress: FastTrackProgress) => void;
};

export type FastTrackResult = {
  quotationId: string;
  lang: string;
  redirectUrl: string;
};

export class FastTrackFailure extends Error {
  readonly quotationId: string;
  readonly currentRevision?: number;
  readonly review?: unknown;
  readonly retryable: boolean;

  constructor(message: string, quotationId: string, error: unknown) {
    super(message);
    this.name = "FastTrackFailure";
    this.quotationId = quotationId;
    this.currentRevision = error instanceof QuotationApiError ? error.metadata.currentRevision : undefined;
    this.review = error instanceof QuotationApiError ? error.metadata.review : undefined;
    this.retryable = error instanceof QuotationApiError ? error.metadata.retryable !== false && error.status !== 409 : true;
  }
}

/**
 * Executes the full automated workflow pipeline:
 * Step 1: Create quotation from request or standalone facts
 * Step 2: Auto-finalize facts and auto-resolve missing hero/destination/hotel media from library
 * Step 3: Batch generate and auto-apply AI storytelling copy for all sections
 * Step 4: Prepare direct navigation to Design Canvas
 */
export async function runQuotationFastTrackPipeline({
  requestId,
  facts,
  existingQuotation = null,
  idempotencyKey,
  onProgress,
}: RunFastTrackOptions): Promise<FastTrackResult> {
  const lang = facts.lang || "en";

  // ---------------------------------------------------------------------------
  // Step 1: Create Quotation
  // ---------------------------------------------------------------------------
  onProgress?.({
    stage: "create",
    message: "Initializing quotation record and blueprint facts...",
  });

  let quotationId = existingQuotation?.quotationId ?? "";
  let baseRevision = existingQuotation?.baseRevision ?? 1;

  if (!existingQuotation && requestId) {
    const pricingOpt: PricingOptionFact = facts.pricing_facts.options[0] || {
      id: "opt-standard",
      label: "Standard Luxury Option",
      currency: "USD",
      per_traveler_amount_minor: 350000,
      group_total_amount_minor: 700000,
    };

    const overridesPayload = {
      brand_id: facts.brand_id,
      lang: facts.lang,
      template_id: facts.presentation_options.template_id,
      travel_designer_id: facts.presentation_options.travel_designer_id,
      partner_id: facts.presentation_options.partner_id,
      customer_name: facts.customer_facts.customer_name,
      adults: facts.customer_facts.adults,
      children: facts.customer_facts.children,
      kid_ages: facts.customer_facts.kid_ages,
      start_date: facts.trip_facts.start_date,
      end_date: facts.trip_facts.end_date,
      itinerary_with_stays: (() => {
        const canonical = staysAdapter.fromQuotationFacts(facts);
        const hydrated = staysReconciler.syncItineraryFromStays(
          canonical.itinerary,
          facts.service_facts.hotels,
          facts.trip_facts.start_date
        );
        return hydrated.map((day) => ({
          day_number: day.day_number,
          title: day.title ?? null,
          destination: day.destination,
          destination_ref: day.destination_ref ?? null,
          overnight: day.overnight ?? day.destination ?? null,
          accommodation_id: day.accommodation_id ?? null,
          accommodation_name: day.accommodation_name ?? null,
          room_type: day.room_type ?? null,
          summary: day.summary ?? null,
          meals: (day.meals ?? []).map((s) => s.trim()).filter(Boolean),
          highlights: (day.highlights ?? []).map((s) => s.trim()).filter(Boolean),
          notes: (day.notes ?? []).map((s) => s.trim()).filter(Boolean),
          sense_of_pace: day.sense_of_pace ?? "balanced",
          display_date: day.display_date ?? null,
        }));
      })(),
      pricing: {
        label: pricingOpt.label || "Standard Luxury Option",
        currency: pricingOpt.currency || "USD",
        per_adult_amount_minor: pricingOpt.per_traveler_amount_minor ?? null,
        per_child_amount_minor: pricingOpt.per_child_amount_minor ?? null,
        group_total_amount_minor: pricingOpt.group_total_amount_minor ?? null,
      },
      pricing_options: (facts.pricing_facts.options || []).map((opt, idx) => ({
        label: opt.label || `Option ${idx + 1}`,
        currency: opt.currency || "USD",
        per_adult_amount_minor: opt.per_adult_amount_minor ?? opt.per_traveler_amount_minor ?? null,
        per_child_amount_minor: opt.per_child_amount_minor ?? null,
        group_total_amount_minor: opt.group_total_amount_minor ?? null,
      })),
    };

    const res = await quotationFetch<{
      quotation_id: string;
      redirect_url?: string;
      current_revision?: number;
    }>(
      `${API_BASE}/api/v2/workspace/requests/${requestId}/generate-quotation`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(overridesPayload),
      },
      "Failed to generate quotation from request."
    );

    quotationId = res.quotation_id;
    baseRevision = res.current_revision || 1;
  } else if (!existingQuotation) {
    const res = await quotationFetch<{
      quotationId: string;
      baselineLang: string;
    }>(
      `${API_BASE}/api/v2/quotations`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(facts),
      },
      "Quotation could not be created."
    );

    quotationId = res.quotationId;
    baseRevision = 1;
  }

  // The server owns media mutation, bypass generation, atomic apply, and the
  // canonical readiness decision. The client never infers completion.
  onProgress?.({
    stage: "facts_media",
    message: "Auto-resolving destination and accommodation photography from library...",
  });

  onProgress?.({
    stage: "content_generation",
    message: "Generating luxury storytelling narratives and daily itinerary in parallel...",
    current: 1,
    total: 2,
  });

  try {
    const result = await quotationFetch<{
      status: "complete";
      quotationId: string;
      currentRevision: number;
      review: { ready: boolean };
    }>(
      `${API_BASE}/api/v2/quotations/${quotationId}/fast-track/assemble?lang=${encodeURIComponent(lang)}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": idempotencyKey ?? crypto.randomUUID(),
          "X-Correlation-ID": `fast-track-${crypto.randomUUID()}`,
        },
        body: JSON.stringify({ baseRevision, writingStyle: "storytelling" }),
      },
      "Fast Track assembly could not complete."
    );
    if (!result.review.ready) {
      throw new Error("Server returned an incomplete Fast Track assembly.");
    }
  } catch (error) {
    // A network failure can occur after a durable server commit. Confirm the
    // canonical state before claiming failure, but never redirect on unknown state.
    if (error instanceof QuotationApiError && error.kind === "network") {
      try {
        const review = await quotationFetch<{ ready: boolean; currentRevision: number }>(
          `${API_BASE}/api/v2/quotations/${quotationId}/review-status?lang=${encodeURIComponent(lang)}`,
          undefined,
          "Failed to verify Fast Track readiness."
        );
        if (review.ready) baseRevision = review.currentRevision;
        else throw error;
      } catch {
        throw new FastTrackFailure("Fast Track state could not be verified. The quotation was kept as incomplete.", quotationId, error);
      }
    } else {
      throw new FastTrackFailure(error instanceof Error ? error.message : "Fast Track assembly could not complete.", quotationId, error);
    }
  }

  // ---------------------------------------------------------------------------
  // Step 4: Ready - Direct landing on Design Canvas
  // ---------------------------------------------------------------------------
  onProgress?.({
    stage: "complete",
    message: "Brochure assembled! Opening Design Studio...",
  });

  const redirectUrl = `/workspace/quotations/${quotationId}/edit?stage=design&lang=${encodeURIComponent(lang)}`;

  return {
    quotationId,
    lang,
    redirectUrl,
  };
}
