"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, useTransition } from "react";
import useSWR from "swr";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";
import { apiErrorFieldErrors, apiErrorMessage, quotationFetch } from "../../lib/apiError";
import { useToast } from "../staff-workspace/ToastProvider";
import MinimalQuotationIntakeForm from "./MinimalQuotationIntakeForm";
import RequestRecapPanel from "./RequestRecapPanel";
import {
  createBrochureFacts,
  type HotelFact,
  type PricingOptionFact,
  type QuotationFacts,
  type QuotationOptions,
  type QuoteRequestItem,
} from "./factsTypes";

import { buildInitialFactsFromRequest } from "../../lib/requestToFactsHandoff";

const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? "";

const fetchJson = async <T,>(url: string): Promise<T> =>
  quotationFetch<T>(url, undefined, "Data could not be loaded.");

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
  const [pending, startTransition] = useTransition();
  const { notify, clearScope } = useToast();

  useEffect(() => {
    if (fieldErrors.length) document.getElementById("quotation-intake-errors")?.focus();
  }, [fieldErrors]);

  const createQuotation = () => {
    startTransition(async () => {
      try {
        if (requestId) {
          // Generate Quotation from Request with minimal overrides
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
            customer_name: facts.customer_facts.customer_name,
            adults: facts.customer_facts.adults,
            children: facts.customer_facts.children,
            kid_ages: facts.customer_facts.kid_ages,
            start_date: facts.trip_facts.start_date,
            end_date: facts.trip_facts.end_date,
            itinerary_with_stays: facts.trip_facts.itinerary.map((day) => {
              const stay: HotelFact | undefined = facts.service_facts.hotels.find(
                (h) => h.destination === day.destination
              );
              return {
                day_number: day.day_number,
                destination: day.destination,
                accommodation_id: stay?.accommodation_id ?? null,
                accommodation_name: stay?.name ?? null,
                room_type: stay?.room_type ?? null,
                summary: day.summary ?? null,
              };
            }),
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
          if (res?.redirect_url) {
            router.push(res.redirect_url);
          } else {
            router.push(`/workspace/quotations/${res.quotation_id}/edit?stage=facts`);
          }
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
          action: { label: "Retry", onClick: createQuotation },
        });
      }
    });
  };

  return (
    <>
      {/* Field Errors Alert */}
      {fieldErrors.length ? (
        <div
          id="quotation-intake-errors"
          tabIndex={-1}
          role="alert"
          className={cn(
            getTypographyClassName("bodySm"),
            "rounded-[var(--radius-card)] border border-rose-300 bg-rose-50 p-4 text-rose-900"
          )}
        >
          <p className={cn(getTypographyClassName("label"), "text-rose-900")}>Please correct the following fields:</p>
          <ul className="mt-1 list-disc pl-5">
            {fieldErrors.map((item, index) => (
              <li key={`${item.path}-${index}`}>
                {item.path ? `${item.path}: ` : ""}
                {item.message}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {/* Main Content Layout */}
      <div className={cn("grid gap-8 items-start", quoteRequest ? "lg:grid-cols-12" : "max-w-4xl mx-auto w-full")}>
        {/* Left Column: Request Context Recap (Sticky) */}
        {quoteRequest ? (
          <div className="lg:col-span-4 lg:sticky lg:top-6 lg:self-start lg:max-h-[calc(100vh-4rem)] lg:overflow-y-auto pr-1">
            <RequestRecapPanel request={quoteRequest} />
          </div>
        ) : null}

        {/* Right Column: Minimal Facts Intake Form */}
        <div className={cn(quoteRequest ? "lg:col-span-8" : "w-full")}>
          <MinimalQuotationIntakeForm
            facts={facts}
            options={options}
            pending={pending}
            onChange={setFacts}
            onSubmit={createQuotation}
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
  const { data: options, error: optionsError } = useSWR<QuotationOptions>(
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
        <p className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-muted)]")}>
          {optionsError ? apiErrorMessage(optionsError) : "Loading active options…"}
        </p>
      )}
    </main>
  );
}
