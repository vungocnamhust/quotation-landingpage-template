"use client";

import { useDeferredValue, useMemo } from "react";
import useSWR from "swr";
import { listProducts, type ProductCategory, type ProductProfile } from "../../lib/quotationApi.ts";

export type UseProductSearchOptions = {
  active?: "true" | "false" | "all";
  category?: ProductCategory | ProductCategory[];
  destinationId?: string;
  supplierId?: string;
  propertyId?: string;
  initialSelectedId?: string | null;
  enabled?: boolean;
};

export function useProductSearch(
  query: string = "",
  {
    active = "true",
    category,
    destinationId,
    supplierId,
    propertyId,
    initialSelectedId,
    enabled = true,
  }: UseProductSearchOptions = {}
) {
  const deferredQuery = useDeferredValue(query.trim());
  const categoryKey = Array.isArray(category) ? category.join(",") : category ?? "";

  const queryKey = enabled
    ? ["products", active, deferredQuery, categoryKey, destinationId ?? "", supplierId ?? "", propertyId ?? ""]
    : null;

  const { data, error, isLoading, mutate } = useSWR(
    queryKey,
    async ([, activeStatus, searchQuery, categories, destination, supplier, property]) => {
      const categoryList = categories ? categories.split(",") : [undefined];
      const responses = await Promise.all(
        categoryList.map((singleCategory) =>
          listProducts({
            active: activeStatus as "true" | "false" | "all",
            search: searchQuery,
            category: singleCategory || undefined,
            destinationId: destination || undefined,
            supplierId: supplier || undefined,
            propertyId: property || undefined,
          })
        )
      );
      const merged = new Map<string, ProductProfile>();
      for (const response of responses) {
        for (const item of response.items) merged.set(item.id, item);
      }
      const items = Array.from(merged.values());
      return { items, total: items.length };
    },
    {
      revalidateOnFocus: false,
      dedupingInterval: 30000,
      keepPreviousData: true,
    }
  );

  const items: ProductProfile[] = useMemo(() => data?.items ?? [], [data?.items]);

  const selectedProduct = useMemo(() => {
    if (!initialSelectedId) return null;
    return items.find((p) => p.id === initialSelectedId) ?? null;
  }, [initialSelectedId, items]);

  return {
    items,
    selectedProduct,
    isLoading,
    error: error ? (error instanceof Error ? error.message : "Products could not be loaded.") : null,
    mutate,
  };
}
