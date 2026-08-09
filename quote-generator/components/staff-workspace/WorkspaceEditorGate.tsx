"use client";

import useSWR from "swr";
import QuotationWorkspaceClient from "../quotation-workspace/QuotationWorkspaceClient";
import { getTypographyClassName } from "../../config/typography";
import { quotationFetch } from "../../lib/apiError";
import { cn } from "../../utils/cn";

const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? "";
type Overview = { quotation: { locale: string } };
export default function WorkspaceEditorGate({ quotationId }: { quotationId: string }) {
  const { data, error } = useSWR<Overview>(`${API_BASE}/api/v2/workspace/quotations/${encodeURIComponent(quotationId)}/overview`, (url: string) => quotationFetch<Overview>(url, undefined, "Quotation could not be opened."));
  if (error) return <p className={cn(getTypographyClassName("bodyMd"), "rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-5 text-[var(--color-on-surface)] shadow-[var(--elevation-card)]")}>This quotation is unavailable in your workspace.</p>;
  if (!data) return <p className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-muted)]")}>Verifying quotation access…</p>;
  return <QuotationWorkspaceClient quotationId={quotationId} lang={data.quotation.locale} />;
}
