"use client";

import { useDeferredValue, useMemo } from "react";
import useSWR from "swr";
import { listTravelDesigners, type TravelDesignerProfile } from "../../lib/quotationApi";

export type UseTravelDesignerSearchOptions = {
  active?: "true" | "false" | "all";
  initialSelectedId?: string | null;
  enabled?: boolean;
};

export function useTravelDesignerSearch(
  query: string = "",
  { active = "true", initialSelectedId, enabled = true }: UseTravelDesignerSearchOptions = {}
) {
  const deferredQuery = useDeferredValue(query.trim());

  const queryKey = enabled ? ["travel-designers", active, deferredQuery] : null;

  const { data, error, isLoading, mutate } = useSWR(
    queryKey,
    ([, activeStatus, searchQuery]) =>
      listTravelDesigners({
        active: activeStatus as "true" | "false" | "all",
        search: searchQuery,
      }),
    {
      revalidateOnFocus: false,
      dedupingInterval: 30000,
      keepPreviousData: true,
    }
  );

  const items: TravelDesignerProfile[] = useMemo(() => data?.items ?? [], [data?.items]);

  const selectedProfile = useMemo(() => {
    if (!initialSelectedId) return null;
    return items.find((p) => p.id === initialSelectedId) ?? null;
  }, [initialSelectedId, items]);

  return {
    items,
    selectedProfile,
    isLoading,
    error: error ? (error instanceof Error ? error.message : "Travel Designers could not be loaded.") : null,
    mutate,
  };
}
