"use client";

import { useDeferredValue, useMemo } from "react";
import useSWR from "swr";
import { listSuppliers, type SupplierProfile } from "../../lib/quotationApi.ts";

export type UseSupplierSearchOptions = {
  active?: "true" | "false" | "all";
  supplierType?: string;
  destinationId?: string;
  initialSelectedId?: string | null;
  enabled?: boolean;
};

export function useSupplierSearch(
  query: string = "",
  { active = "true", supplierType, destinationId, initialSelectedId, enabled = true }: UseSupplierSearchOptions = {}
) {
  const deferredQuery = useDeferredValue(query.trim());

  const queryKey = enabled ? ["suppliers", active, deferredQuery, supplierType ?? "", destinationId ?? ""] : null;

  const { data, error, isLoading, mutate } = useSWR(
    queryKey,
    ([, activeStatus, searchQuery, type, destination]) =>
      listSuppliers({
        active: activeStatus as "true" | "false" | "all",
        search: searchQuery,
        supplierType: type || undefined,
        destinationId: destination || undefined,
      }),
    {
      revalidateOnFocus: false,
      dedupingInterval: 30000,
      keepPreviousData: true,
    }
  );

  const items: SupplierProfile[] = useMemo(() => data?.items ?? [], [data?.items]);

  const selectedSupplier = useMemo(() => {
    if (!initialSelectedId) return null;
    return items.find((s) => s.id === initialSelectedId) ?? null;
  }, [initialSelectedId, items]);

  return {
    items,
    selectedSupplier,
    isLoading,
    error: error ? (error instanceof Error ? error.message : "Suppliers could not be loaded.") : null,
    mutate,
  };
}
