import { quotationFetch } from "./apiError.ts";
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
  onProgress?: (progress: FastTrackProgress) => void;
};

export type FastTrackResult = {
  quotationId: string;
  lang: string;
  redirectUrl: string;
};

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

  let quotationId = "";
  let baseRevision = 1;

  if (requestId) {
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
  } else {
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

  // ---------------------------------------------------------------------------
  // Step 2: Auto-resolve media defaults from catalog/library
  // ---------------------------------------------------------------------------
  onProgress?.({
    stage: "facts_media",
    message: "Auto-resolving destination and accommodation photography from library...",
  });

  try {
    const mediaRes = await quotationFetch<{
      ok: boolean;
      currentRevision?: number;
    }>(
      `${API_BASE}/api/v2/quotations/${quotationId}/facts/media-defaults?lang=${encodeURIComponent(lang)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          baseRevision,
          dryRun: false,
        }),
      },
      "Failed to apply media defaults."
    );
    if (mediaRes.currentRevision) {
      baseRevision = mediaRes.currentRevision;
    }
  } catch (mediaErr) {
    // Non-fatal: if media default resolution fails, proceed with content generation
    console.warn("Media defaults auto-assignment skipped or encountered error:", mediaErr);
  }

  // ---------------------------------------------------------------------------
  // Step 3: Auto-generate and apply AI content sections via Fast Batching
  // ---------------------------------------------------------------------------
  onProgress?.({
    stage: "content_generation",
    message: "Generating luxury storytelling narratives and daily itinerary in parallel...",
    current: 1,
    total: 2,
  });

  try {
    // 1. Batch generate all drafts in parallel on backend
    const batchRes = await quotationFetch<{
      ok: boolean;
      drafts: Array<{ id: string; scope: string }>;
      count: number;
    }>(
      `${API_BASE}/api/v2/quotations/${quotationId}/content-drafts/batch-generate?lang=${encodeURIComponent(lang)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          generationMode: "storytelling",
          instruction: "",
        }),
      },
      "Failed to batch generate content drafts."
    );

    onProgress?.({
      stage: "content_generation",
      message: `Applying all generated narratives (${batchRes.count ?? batchRes.drafts?.length ?? "all"}) to brochure...`,
      current: 2,
      total: 2,
    });

    // 2. Fetch current revision
    const docRes = await quotationFetch<{
      document: Record<string, unknown>;
      currentRevision: number;
    }>(
      `${API_BASE}/api/v2/quotations/${quotationId}/document?lang=${encodeURIComponent(lang)}`,
      undefined,
      "Failed to load canonical document."
    );

    if (docRes.currentRevision) {
      baseRevision = docRes.currentRevision;
    }

    // 3. Apply all drafts in 1 atomic database transaction
    await quotationFetch<{
      ok: boolean;
      currentRevision: number;
      appliedCount: number;
    }>(
      `${API_BASE}/api/v2/quotations/${quotationId}/content-drafts/apply-all?lang=${encodeURIComponent(lang)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ baseRevision }),
      },
      "Failed to apply content drafts to brochure."
    );
  } catch (contentErr) {
    console.warn("Content batch generation encountered warning:", contentErr);
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
