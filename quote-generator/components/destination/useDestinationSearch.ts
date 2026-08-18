"use client";

import { useDeferredValue, useMemo } from "react";
import useSWR from "swr";
import { quotationFetch } from "../../lib/apiError";
import type { DestinationCatalogItem, DestinationRef } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? "";

type SearchResponse = { items: DestinationCatalogItem[] };

const fetchJson = async (url: string): Promise<SearchResponse> => {
  return quotationFetch<SearchResponse>(url, undefined, "Destination search failed.");
};

export const POPULAR_DESTINATIONS: DestinationRef[] = [
  { id: "dst_vietnam", name: "Vietnam", slug: "vietnam" },
  { id: "dst_cambodia", name: "Cambodia", slug: "cambodia" },
  { id: "dst_laos", name: "Laos", slug: "laos" },
  { id: "dst_thailand", name: "Thailand", slug: "thailand" },
  { id: "dst_hanoi", name: "Hanoi", slug: "hanoi" },
  { id: "dst_danang", name: "Da Nang", slug: "da-nang" },
  { id: "dst_hoian", name: "Hoi An", slug: "hoi-an" },
  { id: "dst_saigon", name: "Ho Chi Minh City", slug: "ho-chi-minh-city" },
  { id: "dst_halong", name: "Ha Long Bay", slug: "ha-long-bay" },
  { id: "dst_hue", name: "Hue", slug: "hue" },
  { id: "dst_ninhbinh", name: "Ninh Binh", slug: "ninh-binh" },
  { id: "dst_siemreap", name: "Siem Reap", slug: "siem-reap" },
  { id: "dst_luangprabang", name: "Luang Prabang", slug: "luang-prabang" },
];

export function useDestinationSearch(query: string) {
  const deferredQuery = useDeferredValue(query.trim());
  const hasQuery = deferredQuery.length >= 2;

  const url = hasQuery
    ? `${API_BASE}/api/v2/destinations?query=${encodeURIComponent(deferredQuery)}&limit=12`
    : null;

  const { data, error, isLoading } = useSWR<SearchResponse>(
    url,
    fetchJson,
    {
      revalidateOnFocus: false,
      dedupingInterval: 30000,
      keepPreviousData: true,
    }
  );

  const results: DestinationRef[] = useMemo(() => {
    if (!hasQuery) {
      return POPULAR_DESTINATIONS;
    }
    if (!data?.items) {
      return [];
    }
    return data.items.map((item) => ({
      id: item.id,
      name: item.name,
      slug: item.slug,
      matchedFrom: item.matchedFrom,
    }));
  }, [hasQuery, data]);

  return {
    results,
    isLoading: hasQuery && isLoading,
    error: error ? "Destination catalog is temporarily unavailable." : null,
    hasQuery,
  };
}
