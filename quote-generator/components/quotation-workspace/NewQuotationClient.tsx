"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";
import useSWR from "swr";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";
import { apiErrorFieldErrors, apiErrorMessage, quotationFetch } from "../../lib/apiError";
import { useToast } from "../staff-workspace/ToastProvider";
import QuotationIntakeForm from "./QuotationIntakeForm";
import {
  createBrochureFacts,
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
  const [fieldErrors, setFieldErrors] = useState<Array<{ path: string; message: string }>>([]);
  const [pending, startTransition] = useTransition();
  const { notify, clearScope } = useToast();
  const { data: optionsResponse, error: optionsError } = useSWR<QuotationOptions>(
    `${API_BASE}/api/v2/quotation-options`,
    fetchJson,
  );
  const options = optionsResponse;
  useEffect(() => {
    if (fieldErrors.length) document.getElementById("quotation-intake-errors")?.focus();
  }, [fieldErrors]);
  function createQuotation() {
    startTransition(async () => {
      try {
        const response = await quotationFetch<{ quotationId: string; baselineLang: string }>(`${API_BASE}/api/v2/quotations`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(
            serializeFactsForApi(
              facts,
              serializeDraftMediaSelections(draftMediaSelections),
            ),
          ),
        }, "Quotation could not be created.");
        clearScope("create-quotation");
        router.push(`${personalWorkspace ? "/workspace/quotations" : "/quotations"}/${response.quotationId}${personalWorkspace ? "/edit" : "/workspace"}?stage=facts&lang=${encodeURIComponent(response.baselineLang)}`);
      } catch (error) {
        const message = apiErrorMessage(error);
        setFieldErrors(apiErrorFieldErrors(error));
        setMessage(message);
        notify({ message, type: "error", persistent: true, scope: "create-quotation", action: { label: "Retry", onClick: createQuotation } });
      }
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
      {fieldErrors.length ? <div id="quotation-intake-errors" tabIndex={-1} role="alert" className={cn(getTypographyClassName("bodySm"), "rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] p-4 text-[var(--color-on-surface)]")}><p>Please correct the following fields:</p><ul className="mt-2 list-disc pl-5">{fieldErrors.map((item, index) => <li key={`${item.path}-${index}`}>{item.path ? `${item.path}: ` : ""}{item.message}</li>)}</ul></div> : null}
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
