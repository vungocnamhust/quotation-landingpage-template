"use client";

import { useCallback, useState } from "react";
import useSWR from "swr";
import { apiErrorMessage, quotationFetch } from "../../lib/apiError.ts";
import type {
  QuoteRequestItem,
  QuoteRequestRevisionMeta,
} from "../quotation-workspace/factsTypes.ts";

const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? "";

type RevisionsResponse = {
  request_id: string;
  current_revision: number;
  items: QuoteRequestRevisionMeta[];
};

export type UseRequestRevisionHistoryOptions = {
  enabled?: boolean;
};

export function useRequestRevisionHistory(
  requestId: string | null | undefined,
  { enabled = true }: UseRequestRevisionHistoryOptions = {}
) {
  const [loadingRev, setLoadingRev] = useState<number | null>(null);
  const [inspectError, setInspectError] = useState<string | null>(null);

  const url = enabled && requestId
    ? `${API_BASE}/api/v2/workspace/requests/${encodeURIComponent(requestId)}/revisions`
    : null;

  const { data, error, isLoading, mutate } = useSWR<RevisionsResponse>(
    url,
    (fetchUrl: string) =>
      quotationFetch<RevisionsResponse>(
        fetchUrl,
        undefined,
        "Could not load revision history."
      ),
    {
      revalidateOnFocus: false,
      dedupingInterval: 30000,
    }
  );

  const fetchRevisionSnapshot = useCallback(
    async (revNumber: number): Promise<QuoteRequestItem | null> => {
      if (!requestId) return null;
      setLoadingRev(revNumber);
      setInspectError(null);
      try {
        const snapshot = await quotationFetch<QuoteRequestItem>(
          `${API_BASE}/api/v2/workspace/requests/${encodeURIComponent(requestId)}/revisions/${revNumber}`,
          undefined,
          `Could not load snapshot for Revision #${revNumber}`
        );
        return snapshot ?? null;
      } catch (err: unknown) {
        setInspectError(apiErrorMessage(err));
        return null;
      } finally {
        setLoadingRev(null);
      }
    },
    [requestId]
  );

  return {
    revisions: data?.items ?? [],
    currentRevision: data?.current_revision ?? 1,
    isLoading,
    loadingRev,
    error: error ? (error instanceof Error ? error.message : "Revisions could not be loaded.") : null,
    inspectError,
    fetchRevisionSnapshot,
    mutate,
  };
}
