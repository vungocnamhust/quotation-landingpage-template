"use client";

import useSWR from "swr";
import {
  activateRate,
  createRate,
  deleteDraftRate,
  listProductRates,
  supersedeRate,
  updateRate,
  type RateAggregateInput,
  type RateLifecycleStatus,
} from "../../../lib/quotationApi.ts";

export function useProductRates(productId: string | null, lifecycle: RateLifecycleStatus | "all" = "all") {
  const key = productId ? ["product-rates", productId, lifecycle] : null;
  const { data, error, isLoading, mutate } = useSWR(key, () =>
    listProductRates(productId as string, { lifecycle })
  );

  return {
    rates: data?.items ?? [],
    total: data?.total ?? 0,
    isLoading,
    error,
    mutate,
    createDraft: (input: RateAggregateInput) => createRate(productId as string, input),
    updateDraft: (rateId: string, input: RateAggregateInput) => updateRate(rateId, input),
    activate: (rateId: string) => activateRate(rateId),
    supersede: (rateId: string, input: RateAggregateInput) => supersedeRate(rateId, input),
    deleteDraft: (rateId: string) => deleteDraftRate(rateId),
  };
}
