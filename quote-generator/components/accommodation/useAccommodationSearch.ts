"use client";

import { useDeferredValue, useMemo } from "react";
import useSWR from "swr";
import { listAccommodations, type AccommodationProfile } from "../../lib/quotationApi.ts";

export type UseAccommodationSearchOptions = {
  active?: "true" | "false" | "all";
  destinationId?: string | null;
  destination?: string | null;
  initialSelectedId?: string | null;
  enabled?: boolean;
};

export function useAccommodationSearch(
  query: string = "",
  {
    active = "true",
    destinationId,
    destination,
    initialSelectedId,
    enabled = true,
  }: UseAccommodationSearchOptions = {}
) {
  const deferredQuery = useDeferredValue(query.trim());

  const queryKey = enabled
    ? ["accommodations", active, destinationId || "", destination || "", deferredQuery]
    : null;

  const { data, error, isLoading, mutate } = useSWR(
    queryKey,
    ([, activeStatus, destId, destName, searchQuery]) =>
      listAccommodations({
        active: activeStatus as "true" | "false" | "all",
        destinationId: destId || undefined,
        destination: destName || undefined,
        query: searchQuery,
      }),
    {
      revalidateOnFocus: false,
      dedupingInterval: 30000,
      keepPreviousData: true,
    }
  );

  const items: AccommodationProfile[] = useMemo(() => data?.items ?? [], [data?.items]);

  const selectedProfile = useMemo(() => {
    if (!initialSelectedId) return null;
    return items.find((p) => p.id === initialSelectedId) ?? null;
  }, [initialSelectedId, items]);

  return {
    items,
    selectedProfile,
    isLoading,
    error: error ? (error instanceof Error ? error.message : "Accommodations could not be loaded.") : null,
    mutate,
  };
}
