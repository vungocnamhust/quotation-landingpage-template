"use client";

import useSWR from "swr";
import { quotationFetch } from "../../lib/apiError.ts";
import type { QuoteRequestItem } from "../quotation-workspace/factsTypes.ts";

const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? "";

const fetcher = (url: string) =>
  quotationFetch<QuoteRequestItem>(url, undefined, "Could not load request detail.");

export function useRequestDetail(requestId: string | null | undefined) {
  const url = requestId
    ? `${API_BASE}/api/v2/workspace/requests/${encodeURIComponent(requestId)}`
    : null;

  const { data, error, isLoading, mutate } = useSWR<QuoteRequestItem>(url, fetcher, {
    revalidateOnFocus: false,
    dedupingInterval: 15000,
  });

  return {
    request: data ?? null,
    isLoading,
    error: error ? (error instanceof Error ? error.message : "Request could not be loaded.") : null,
    mutate,
  };
}
