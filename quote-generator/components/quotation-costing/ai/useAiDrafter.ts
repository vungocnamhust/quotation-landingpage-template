"use client";

import { useCallback, useState } from "react";
import useSWR from "swr";
import {
  analyzeTripProfile,
  draftServices,
  listAiRuns,
  type AnalyzeTripResponse,
  type DraftDaySpec,
  type DraftServicesResponse,
  type TripProfile,
} from "../../../lib/quotationApi.ts";
import { apiErrorMessage, QuotationApiError } from "../../../lib/apiError.ts";

/**
 * Headless hook for the AI Service Drafter (15.7) human-in-the-loop flow — Analyze
 * (0-tool prose -> TripProfile) then Draft (per-day catalog agent, zero-money output).
 * Same shape as useCostingWorkspace/useIngestionBatches: SWR owns the run-list cache,
 * plain useState owns in-flight action state, and every mutation's response replaces
 * state directly instead of triggering a revalidating refetch.
 */
export function useAiDrafter(sheetId: string | null) {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isDrafting, setIsDrafting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const { data: runsData, mutate: mutateRuns } = useSWR(
    sheetId ? ["ai-runs", sheetId] : null,
    ([, id]) => listAiRuns(id),
    { revalidateOnFocus: false },
  );

  const runAction = useCallback(
    async <T,>(action: () => Promise<T>, onConflict?: () => void): Promise<T | null> => {
      try {
        return await action();
      } catch (error) {
        setActionError(apiErrorMessage(error));
        if (error instanceof QuotationApiError && error.kind === "conflict") {
          // The sheet's costing_revision moved under us (CAS) — the host must reload
          // the workbench before a retry can succeed (16.3-style 409 handling).
          onConflict?.();
        }
        return null;
      }
    },
    [],
  );

  const analyze = useCallback(
    async (rawText: string): Promise<AnalyzeTripResponse | null> => {
      if (!sheetId) return null;
      setIsAnalyzing(true);
      setActionError(null);
      try {
        const result = await runAction(() => analyzeTripProfile(sheetId, rawText));
        if (result) void mutateRuns();
        return result;
      } finally {
        setIsAnalyzing(false);
      }
    },
    [mutateRuns, runAction, sheetId],
  );

  const draft = useCallback(
    async (
      input: {
        runId: string;
        tripProfile: TripProfile;
        days: DraftDaySpec[];
        dayNumbers?: number[] | null;
        baseCostingRevision: number;
      },
      onConflict?: () => void,
    ): Promise<DraftServicesResponse | null> => {
      if (!sheetId) return null;
      setIsDrafting(true);
      setActionError(null);
      try {
        const result = await runAction(() => draftServices(sheetId, input), onConflict);
        if (result) void mutateRuns();
        return result;
      } finally {
        setIsDrafting(false);
      }
    },
    [mutateRuns, runAction, sheetId],
  );

  return {
    runs: runsData?.runs ?? [],
    isAnalyzing,
    isDrafting,
    actionError,
    analyze,
    draft,
  };
}

export default useAiDrafter;
