"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import useSWR from "swr";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";
import { apiErrorMessage, quotationFetch } from "../../lib/apiError";
import QuotationIntakeForm from "./QuotationIntakeForm";
import {
  createBrochureFacts,
  formatApiError,
  serializeDraftMediaSelections,
  serializeFactsForApi,
  type DraftMediaSelections,
  type QuotationFacts,
  type QuotationOptions,
} from "./factsTypes";

const API_BASE =
  process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? "";
const fetchJson = async <T,>(url: string): Promise<T> =>
  quotationFetch<T>(url, undefined, "Brand options could not be loaded.");
export default function NewQuotationClient({ personalWorkspace = false }: { personalWorkspace?: boolean }) {
  const router = useRouter();
  const [facts, setFacts] = useState<QuotationFacts>(createBrochureFacts);
  const [draftMediaSelections, setDraftMediaSelections] = useState<DraftMediaSelections>({});
  const [message, setMessage] = useState("Complete the short intake, then continue with the full Facts workspace.");
  const [pending, startTransition] = useTransition();
  const { data: optionsResponse, error: optionsError } = useSWR<QuotationOptions>(
    `${API_BASE}/api/v2/quotation-options`,
    fetchJson,
  );
  const options = optionsResponse;
  function createQuotation() {
    startTransition(async () => {
      const response = await fetch(`${API_BASE}/api/v2/quotations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(
          serializeFactsForApi(
            facts,
            serializeDraftMediaSelections(draftMediaSelections),
          ),
        ),
      });
      const payload = await response.json();
      if (!response.ok) {
        setMessage(formatApiError(payload.detail, "Quotation could not be created."));
        return;
      }
      router.push(`${personalWorkspace ? "/workspace/quotations" : "/quotations"}/${payload.quotationId}${personalWorkspace ? "/edit" : "/workspace"}?stage=facts&lang=${encodeURIComponent(payload.baselineLang)}`);
    });
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-[100rem] flex-col gap-7 px-5 py-8 sm:px-8 lg:px-12">
      <header className="flex flex-col gap-3">
        <p
          className={cn(
            getTypographyClassName("overline"),
            "text-[var(--color-accent)]",
          )}
        >
          Quotation workspace
        </p>
        <h1
          className={cn(
            getTypographyClassName("pageTitle"),
            "text-[var(--color-on-surface)]",
          )}
        >
          Create quotation
        </h1>
        <p
          aria-live="polite"
          className={cn(
            getTypographyClassName("bodyLg"),
            "text-[var(--color-muted)]",
          )}
        >
          {message}
        </p>
      </header>
      {options ? <QuotationIntakeForm facts={facts} options={options} draftMediaSelections={draftMediaSelections} onDraftMediaSelectionChange={(fieldId, value) => setDraftMediaSelections((current) => ({ ...current, [fieldId]: value }))} onChange={setFacts} onSubmit={createQuotation} pending={pending} /> : <p className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-muted)]")}>{optionsError ? apiErrorMessage(optionsError) : "Loading active brand options…"}</p>}
      {optionsError ? (
        <p
          className={cn(
            getTypographyClassName("bodySm"),
            "text-[var(--color-accent)]",
          )}
        >
          {apiErrorMessage(optionsError)}
        </p>
      ) : null}
    </main>
  );
}
