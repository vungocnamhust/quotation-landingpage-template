"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, useTransition } from "react";
import useSWR from "swr";
import { AlertCircle } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import { apiErrorFieldErrors, apiErrorMessage, quotationFetch } from "../../lib/apiError.ts";
import { useToast } from "../staff-workspace/ToastProvider.tsx";
import MinimalQuotationIntakeForm from "./MinimalQuotationIntakeForm.tsx";
import RequestRecapPanel from "./RequestRecapPanel.tsx";
import {
  createBrochureFacts,
  type PricingOptionFact,
  type QuotationFacts,
  type QuotationOptions,
  type QuoteRequestItem,
} from "./factsTypes.ts";

import { buildInitialFactsFromRequest } from "../../lib/requestToFactsHandoff.ts";
import { staysAdapter } from "../../lib/rules/staysAdapter.ts";
import { staysReconciler } from "../../lib/rules/staysReconciler.ts";

const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? "";

const fetchJson = async <T,>(url: string): Promise<T> =>
  quotationFetch<T>(url, undefined, "Data could not be loaded.");

import FastTrackProgressModal from "./FastTrackProgressModal.tsx";
import { runQuotationFastTrackPipeline, type FastTrackProgress } from "../../lib/quotationFastTrack.ts";

function QuotationIntakeInner({
  quoteRequest,
  requestId,
  options,
  personalWorkspace,
}: {
  quoteRequest: QuoteRequestItem | null;
  requestId: string | null;
  options: QuotationOptions;
  personalWorkspace: boolean;
}) {
  const router = useRouter();
  const [facts, setFacts] = useState<QuotationFacts>(() =>
    buildInitialFactsFromRequest(quoteRequest, createBrochureFacts())
  );
  const [fieldErrors, setFieldErrors] = useState<Array<{ path: string; message: string }>>([]);
  const [isPending, startTransition] = useTransition();
  const [fastTrackProgress, setFastTrackProgress] = useState<FastTrackProgress | null>(null);
  const [isFastTrackOpen, setIsFastTrackOpen] = useState(false);
  const { toast, notify, clearScope } = useToast();

  useEffect(() => {
    if (fieldErrors.length) document.getElementById("quotation-intake-errors")?.focus();
  }, [fieldErrors]);

  const handleCreateQuotation = (targetStage: "facts" | "design") => {
    if (targetStage === "design") {
      setIsFastTrackOpen(true);
      setFastTrackProgress({
        stage: "create",
        message: "Starting automated fast-track workflow...",
      });

      startTransition(async () => {
        try {
          const result = await runQuotationFastTrackPipeline({
            requestId,
            facts,
            onProgress: (prog) => setFastTrackProgress(prog),
          });

          clearScope("create-quotation");
          toast("Brochure assembled successfully! Opening Design Studio...", "success");
          router.push(result.redirectUrl);
        } catch (error) {
          setIsFastTrackOpen(false);
          const msg = apiErrorMessage(error);
          setFieldErrors(apiErrorFieldErrors(error));
          notify({
            message: msg,
            type: "error",
            persistent: true,
            scope: "create-quotation",
            action: { label: "Retry", onClick: () => handleCreateQuotation("design") },
          });
        }
      });
      return;
    }

    // Standard creation -> navigate to Facts stage
    startTransition(async () => {
      try {
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
            redirect_url: string;
          }>(
            `${API_BASE}/api/v2/workspace/requests/${requestId}/generate-quotation`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(overridesPayload),
            },
            "Failed to generate quotation from request."
          );

          clearScope("create-quotation");
          toast(
            `Quotation created successfully from request #${requestId}! Redirecting to workspace...`,
            "success"
          );
          router.push(
            `/workspace/quotations/${res.quotation_id}/edit?stage=facts&lang=${encodeURIComponent(
              facts.lang || "en"
            )}`
          );
        } else {
          // Direct quotation creation without request
          const res = await quotationFetch<{ quotationId: string; baselineLang: string }>(
            `${API_BASE}/api/v2/quotations`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(facts),
            },
            "Quotation could not be created."
          );
          clearScope("create-quotation");
          toast("Quotation created successfully! Redirecting to workspace...", "success");
          router.push(
            `${personalWorkspace ? "/workspace/quotations" : "/quotations"}/${res.quotationId}${
              personalWorkspace ? "/edit" : "/workspace"
            }?stage=facts&lang=${encodeURIComponent(res.baselineLang)}`
          );
        }
      } catch (error) {
        const msg = apiErrorMessage(error);
        setFieldErrors(apiErrorFieldErrors(error));
        notify({
          message: msg,
          type: "error",
          persistent: true,
          scope: "create-quotation",
          action: { label: "Retry", onClick: () => handleCreateQuotation("facts") },
        });
      }
    });
  };

  return (
    <>
      <FastTrackProgressModal isOpen={isFastTrackOpen} progress={fastTrackProgress} />
      {/* Field Errors Alert */}
      {fieldErrors.length ? (
        <div
          id="quotation-intake-errors"
          tabIndex={-1}
          role="alert"
          className="mx-auto w-full max-w-4xl rounded-[var(--radius-card)] border border-rose-300 bg-rose-50 p-4 text-rose-900 shadow-sm"
        >
          <div className="flex items-center gap-2">
            <AlertCircle size={16} className="text-rose-600" />
            <p className={cn(getTypographyClassName("label"), "text-rose-900")}>
              Please resolve the following intake requirements:
            </p>
          </div>
          <ul className="mt-2 list-disc pl-5 space-y-1">
            {fieldErrors.map((err, idx) => (
              <li key={idx} className={cn(getTypographyClassName("caption"), "text-rose-800")}>
                {err.message}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className={cn("grid gap-8 items-start", requestId ? "lg:grid-cols-[20rem_minmax(0,1fr)]" : "")}>
        {requestId && quoteRequest ? (
          <RequestRecapPanel request={quoteRequest} />
        ) : null}

        <div className="min-w-0">
          <MinimalQuotationIntakeForm
            facts={facts}
            options={options}
            onChange={setFacts}
            onSubmit={handleCreateQuotation}
            pending={isPending}
          />
        </div>
      </div>
    </>
  );
}

export default function NewQuotationClient({ personalWorkspace = false }: { personalWorkspace?: boolean }) {
  const searchParams = useSearchParams();
  const requestId = searchParams.get("requestId");

  // Load Brand / Language options
  const {
    data: options,
    error: optionsError,
    mutate: mutateOptions,
  } = useSWR<QuotationOptions>(
    `${API_BASE}/api/v2/quotation-options`,
    fetchJson
  );

  // Load Quote Request if requestId is present
  const {
    data: quoteRequest,
    isLoading: requestLoading,
  } = useSWR<QuoteRequestItem>(
    requestId ? `${API_BASE}/api/v2/workspace/requests/${requestId}` : null,
    fetchJson
  );

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-[100rem] flex-col gap-6 px-4 py-8 sm:px-6 lg:px-10">
      {/* Top Header */}
      <header className="flex flex-col gap-2 border-b border-[var(--color-border)] pb-4">
        <p className={cn(getTypographyClassName("overline"), "text-[var(--color-accent)]")}>
          Quotation Workspace
        </p>
        <h1 className={cn(getTypographyClassName("pageTitle"), "text-[var(--color-on-surface)]")}>
          {requestId ? "New Quotation from Request" : "Create New Quotation"}
        </h1>
        <p className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-muted)]")}>
          {requestId
            ? "Review the request summary on the left and set the minimal facts (route, stays, pricing) to draft this quotation."
            : "Complete the minimal facts to initialize a quotation proposal."}
        </p>
      </header>

      {options ? (
        requestId && requestLoading ? (
          <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-8 text-center">
            <p className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-muted)]")}>
              Loading request context…
            </p>
          </div>
        ) : (
          <QuotationIntakeInner
            key={quoteRequest?.id ?? "standalone"}
            quoteRequest={quoteRequest ?? null}
            requestId={requestId}
            options={options}
            personalWorkspace={personalWorkspace}
          />
        )
      ) : (
        <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 text-center shadow-[var(--elevation-card)]">
          {optionsError ? (
            <div className="flex flex-col items-center gap-3">
              <p className={cn(getTypographyClassName("bodyMd"), "text-rose-700")}>
                {apiErrorMessage(optionsError)}
              </p>
              <button
                type="button"
                onClick={() => mutateOptions()}
                className={cn(
                  getTypographyClassName("buttonSecondary"),
                  "rounded-[var(--radius-button)] border border-[var(--color-border)] px-4 py-2 text-[var(--color-on-surface)] hover:bg-[var(--color-surface-muted)] cursor-pointer"
                )}
              >
                Retry loading options
              </button>
            </div>
          ) : (
            <p className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-muted)]")}>
              Loading active options…
            </p>
          )}
        </div>
      )}
    </main>
  );
}
