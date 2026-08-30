"use client";

import { useCallback, useState } from "react";
import useSWR from "swr";
import {
  applyCostingPricing,
  attachCostingSheetToQuotation,
  createCostingSheet,
  createServiceLine,
  deleteServiceLine,
  findCostingSheetByQuotation,
  findCostingSheetByRequest,
  getCostingWorkbench,
  updateCostingSettings,
  updateServiceLine,
} from "../../lib/quotationApi.ts";
import { apiErrorMessage, QuotationApiError } from "../../lib/apiError.ts";
import type {
  ApplyPricingResponse,
  CostingWorkbenchAnchor,
  CostingWorkbenchResponse,
  ServiceLineWriteInput,
} from "./types.ts";

function newIdempotencyKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `idem_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

/**
 * Headless hook for the Costing Workbench (15.4 / 15.5) — resolves-or-creates the
 * sheet for the given anchor, then owns the workbench SWR cache and every
 * mutation. Every write's response IS the new cache value (the server always
 * returns the fresh `{sheet, items, summary, applications, drift}`), so mutations never trigger a
 * revalidating refetch — they just replace the cache with the response.
 */
export function useCostingWorkspace(anchor: CostingWorkbenchAnchor) {
  const [sheetId, setSheetId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [isCreatingSheet, setIsCreatingSheet] = useState(false);
  const [isApplyingPricing, setIsApplyingPricing] = useState(false);

  const anchorKind: "request" | "quotation" = anchor.requestId ? "request" : "quotation";
  const anchorId = anchor.requestId ?? anchor.quotationId ?? "";
  const findKey = sheetId ? null : (["costing-sheet-find", anchorKind, anchorId] as const);

  const { data: foundSheet, isLoading: isFinding } = useSWR(
    findKey,
    async ([, kind, idValue]) =>
      kind === "request" ? findCostingSheetByRequest(idValue) : findCostingSheetByQuotation(idValue),
    { revalidateOnFocus: false },
  );

  const resolvedSheetId = sheetId ?? foundSheet?.id ?? null;

  const {
    data: workbench,
    isLoading: isLoadingWorkbench,
    mutate: mutateWorkbench,
  } = useSWR(resolvedSheetId ? ["costing-workbench", resolvedSheetId] : null, ([, id]) => getCostingWorkbench(id), {
    revalidateOnFocus: false,
  });

  const applyResult = useCallback(
    (result: CostingWorkbenchResponse) => {
      setSheetId(result.sheet.id);
      mutateWorkbench(result, { revalidate: false });
      setActionError(null);
      return result;
    },
    [mutateWorkbench],
  );

  const runAction = useCallback(
    async <T,>(action: () => Promise<T>, onConflict?: () => void): Promise<T | null> => {
      try {
        return await action();
      } catch (error) {
        setActionError(apiErrorMessage(error));
        if (error instanceof QuotationApiError && error.kind === "conflict") {
          // Someone else moved the sheet on — reload the authoritative state.
          if (resolvedSheetId) await mutateWorkbench();
          // Callers whose CAS also spans a resource this module doesn't own
          // (e.g. applyPricing's facts/document baseRevision) get a chance to
          // refresh that resource too, so a retry doesn't repeat the same 409
          // forever (16.3 P0 fix).
          onConflict?.();
        }
        return null;
      }
    },
    [mutateWorkbench, resolvedSheetId],
  );

  const createSheet = useCallback(
    async (currency?: string) => {
      setIsCreatingSheet(true);
      try {
        return await runAction(async () => {
          const sheet = await createCostingSheet(
            anchor.requestId ? { request_id: anchor.requestId, currency } : { quotation_id: anchor.quotationId, currency },
          );
          setSheetId(sheet.id);
          const fresh = await getCostingWorkbench(sheet.id);
          return applyResult(fresh);
        });
      } finally {
        setIsCreatingSheet(false);
      }
    },
    [anchor.requestId, anchor.quotationId, applyResult, runAction],
  );

  const baseCostingRevision = workbench?.sheet.costing_revision ?? 0;

  const updateSettings = useCallback(
    (input: { currency?: string; markup_rate_bps?: number; rounding_increment_minor?: number }) => {
      if (!resolvedSheetId) return Promise.resolve(null);
      return runAction(async () => {
        const result = await updateCostingSettings(resolvedSheetId, { base_costing_revision: baseCostingRevision, ...input });
        return applyResult(result);
      });
    },
    [applyResult, baseCostingRevision, resolvedSheetId, runAction],
  );

  const addLine = useCallback(
    (input: Omit<ServiceLineWriteInput, "base_costing_revision">) => {
      if (!resolvedSheetId) return Promise.resolve(null);
      return runAction(async () => {
        const result = await createServiceLine(
          resolvedSheetId,
          { base_costing_revision: baseCostingRevision, ...input },
          newIdempotencyKey(),
        );
        return applyResult(result);
      });
    },
    [applyResult, baseCostingRevision, resolvedSheetId, runAction],
  );

  const editLine = useCallback(
    (lineId: string, input: Omit<ServiceLineWriteInput, "base_costing_revision">) => {
      if (!resolvedSheetId) return Promise.resolve(null);
      return runAction(async () => {
        const result = await updateServiceLine(resolvedSheetId, lineId, { base_costing_revision: baseCostingRevision, ...input });
        return applyResult(result);
      });
    },
    [applyResult, baseCostingRevision, resolvedSheetId, runAction],
  );

  const removeLine = useCallback(
    (lineId: string) => {
      if (!resolvedSheetId) return Promise.resolve(null);
      return runAction(async () => {
        const result = await deleteServiceLine(resolvedSheetId, lineId, baseCostingRevision);
        return applyResult(result);
      });
    },
    [applyResult, baseCostingRevision, resolvedSheetId, runAction],
  );

  const attachToQuotation = useCallback(
    (quotationId: string) => {
      if (!resolvedSheetId) return Promise.resolve(null);
      return runAction(async () => {
        const result = await attachCostingSheetToQuotation(resolvedSheetId, quotationId, newIdempotencyKey());
        return applyResult(result);
      });
    },
    [applyResult, resolvedSheetId, runAction],
  );

  const applyPricing = useCallback(
    async (
      input: {
        base_revision: number;
        target_option_id?: string | null;
        option_label?: string | null;
        lang?: string | null;
      },
      idempotencyKey?: string,
      onConflict?: () => void,
    ): Promise<ApplyPricingResponse | null> => {
      if (!resolvedSheetId) return null;
      setIsApplyingPricing(true);
      try {
        return await runAction(async () => {
          const response = await applyCostingPricing(
            resolvedSheetId,
            {
              base_revision: input.base_revision,
              base_costing_revision: baseCostingRevision,
              target_option_id: input.target_option_id,
              option_label: input.option_label,
              lang: input.lang,
            },
            idempotencyKey || newIdempotencyKey(),
          );
          const fresh = await getCostingWorkbench(resolvedSheetId);
          applyResult(fresh);
          return response;
        }, onConflict);
      } finally {
        setIsApplyingPricing(false);
      }
    },
    [applyResult, baseCostingRevision, resolvedSheetId, runAction],
  );

  return {
    sheetId: resolvedSheetId,
    workbench,
    isLoading: isFinding || isLoadingWorkbench,
    isCreatingSheet,
    isApplyingPricing,
    actionError,
    createSheet,
    updateSettings,
    addLine,
    editLine,
    removeLine,
    attachToQuotation,
    applyPricing,
    refresh: () => (resolvedSheetId ? mutateWorkbench() : undefined),
  };
}
