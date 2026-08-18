"use client";

import { useDeferredValue, useMemo } from "react";
import useSWR from "swr";
import { listPartners, type PartnerProfile } from "../../lib/quotationApi";

export type UsePartnerSearchOptions = {
  active?: "true" | "false" | "all";
  initialSelectedId?: string | null;
  enabled?: boolean;
};

export function usePartnerSearch(
  query: string = "",
  { active = "true", initialSelectedId, enabled = true }: UsePartnerSearchOptions = {}
) {
  const deferredQuery = useDeferredValue(query.trim());

  const queryKey = enabled ? ["partners", active, deferredQuery] : null;

  const { data, error, isLoading, mutate } = useSWR(
    queryKey,
    ([, activeStatus, searchQuery]) =>
      listPartners({
        active: activeStatus as "true" | "false" | "all",
        search: searchQuery,
      }),
    {
      revalidateOnFocus: false,
      dedupingInterval: 30000,
      keepPreviousData: true,
    }
  );

  const items: PartnerProfile[] = useMemo(() => data?.items ?? [], [data?.items]);

  const selectedPartner = useMemo(() => {
    if (!initialSelectedId) return null;
    return items.find((p) => p.id === initialSelectedId) ?? null;
  }, [initialSelectedId, items]);

  return {
    items,
    selectedPartner,
    isLoading,
    error: error ? (error instanceof Error ? error.message : "Partners could not be loaded.") : null,
    mutate,
  };
}
