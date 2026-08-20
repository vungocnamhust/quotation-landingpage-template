import { quotationFetch, apiErrorMessage } from "./apiError.ts";
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
          destination: day.destination,
          destination_ref: day.destination_ref ?? null,
          overnight: day.overnight ?? day.destination ?? null,
          accommodation_id: day.accommodation_id ?? null,
          accommodation_name: day.accommodation_name ?? null,
          room_type: day.room_type ?? null,
          summary: day.summary ?? null,
        }));
      })(),
      pricing: {
        label: pricingOpt.label || "Standard Luxury Option",
        currency: pricingOpt.currency || "USD",
        per_adult_amount_minor: pricingOpt.per_traveler_amount_minor ?? null,
        per_child_amount_minor: pricingOpt.per_child_amount_minor ?? null,
        group_total_amount_minor: pricingOpt.group_total_amount_minor ?? null,
      },
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
  // Step 3: Auto-generate and apply AI content sections
  // ---------------------------------------------------------------------------
  onProgress?.({
    stage: "content_generation",
    message: "Preparing content sections for batch storytelling generation...",
    current: 0,
    total: 1,
  });

  try {
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

    const docItinerary = docRes.document?.itinerary as
      | { days?: Array<{ dayNumber?: number }> }
      | undefined;
    const dayCount = docItinerary?.days?.length ?? facts.trip_facts.itinerary.length ?? 0;

    const scopesToGenerate: string[] = [
      "hero",
      "overview",
      "route_map",
      ...Array.from({ length: dayCount }, (_, idx) => `itinerary:day:${idx + 1}`),
      "inclusions_exclusions",
    ];

    const totalScopes = scopesToGenerate.length;

    for (let i = 0; i < scopesToGenerate.length; i++) {
      const scope = scopesToGenerate[i];
      const scopeLabel = scope.startsWith("itinerary:day:")
        ? `Day ${scope.replace("itinerary:day:", "")}`
        : scope.replace("_", " ");

      onProgress?.({
        stage: "content_generation",
        message: `Generating AI narrative copy for ${scopeLabel} (${i + 1}/${totalScopes})...`,
        current: i + 1,
        total: totalScopes,
      });

      try {
        // 1. Generate content draft
        const draftRes = await quotationFetch<{
          draft: { id: string; candidate_json?: Record<string, unknown> };
        }>(
          `${API_BASE}/api/v2/quotations/${quotationId}/content-drafts?lang=${encodeURIComponent(lang)}`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              scope,
              generationMode: "storytelling",
              instruction: "",
            }),
          },
          `Failed to generate draft for ${scope}.`
        );

        // 2. Apply content draft to canonical document
        if (draftRes.draft?.id) {
          const applyRes = await quotationFetch<{
            ok: boolean;
            currentRevision: number;
          }>(
            `${API_BASE}/api/v2/quotations/${quotationId}/content-drafts/${draftRes.draft.id}/apply`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ baseRevision }),
            },
            `Failed to apply draft for ${scope}.`
          );

          if (applyRes.currentRevision) {
            baseRevision = applyRes.currentRevision;
          }
        }
      } catch (scopeErr) {
        console.warn(`Content generation skipped for scope '${scope}':`, apiErrorMessage(scopeErr));
      }
    }
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
