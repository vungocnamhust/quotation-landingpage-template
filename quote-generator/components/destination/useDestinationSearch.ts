"use client";

import { useDeferredValue, useMemo } from "react";
import useSWR from "swr";
import { quotationFetch } from "../../lib/apiError.ts";
import { POPULAR_DESTINATIONS } from "./popularDestinations.ts";
import type { DestinationCatalogItem, DestinationSearchResult } from "./types.ts";

const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? "";

type SearchResponse = { items: DestinationCatalogItem[] };

const fetchJson = async (url: string): Promise<SearchResponse> => {
  return quotationFetch<SearchResponse>(url, undefined, "Destination search failed.");
};

export { POPULAR_DESTINATIONS };

export interface UseDestinationSearchOptions {
  /** Restrict results to these destination_type values (csv), e.g. ["province", "city"]. */
  types?: string[];
  /** Restrict results to direct children of this destination id. */
  parentId?: string;
}

export function useDestinationSearch(query: string, options: UseDestinationSearchOptions = {}) {
  const deferredQuery = useDeferredValue(query.trim());
  const hasQuery = deferredQuery.length > 0;
  const typesParam = options.types?.join(",") ?? "";
  const parentIdParam = options.parentId ?? "";

  const params = new URLSearchParams({ query: deferredQuery, limit: "25" });
  if (typesParam) params.set("types", typesParam);
  if (parentIdParam) params.set("parentId", parentIdParam);
  const url = `${API_BASE}/api/v2/destinations?${params.toString()}`;

  const { data, error, isLoading } = useSWR<SearchResponse>(
    url,
    fetchJson,
    {
      revalidateOnFocus: false,
      dedupingInterval: 30000,
      keepPreviousData: true,
    }
  );

  const results: DestinationSearchResult[] = useMemo(() => {
    if (!data?.items || data.items.length === 0) {
      if (!hasQuery) {
        return POPULAR_DESTINATIONS;
      }
      return [];
    }
    return data.items.map((item) => ({
      id: item.id,
      name: item.name,
      slug: item.slug,
      mediaPrefix: item.mediaPrefix ?? null,
      defaultMediaPrefix: item.defaultMediaPrefix,
      matchedFrom: item.matchedFrom,
      destinationType: item.destinationType,
      iataCode: item.iataCode ?? null,
      mergedIntoId: item.mergedIntoId ?? null,
    }));
  }, [hasQuery, data]);

  return {
    results,
    isLoading: isLoading && !data,
    error: error ? "Destination catalog is temporarily unavailable." : null,
    hasQuery,
  };
}
