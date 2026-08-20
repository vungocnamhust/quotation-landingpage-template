"use client";

import { useDeferredValue, useMemo } from "react";
import useSWR from "swr";
import { quotationFetch } from "../../lib/apiError.ts";
import type { DestinationCatalogItem, DestinationRef } from "./types.ts";

const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? "";

type SearchResponse = { items: DestinationCatalogItem[] };

const fetchJson = async (url: string): Promise<SearchResponse> => {
  return quotationFetch<SearchResponse>(url, undefined, "Destination search failed.");
};

export const POPULAR_DESTINATIONS: DestinationRef[] = [
  { id: "dst_ho-chi-minh", name: "Ho Chi Minh City", slug: "ho-chi-minh" },
  { id: "dst_ha-noi", name: "Hanoi", slug: "ha-noi" },
  { id: "dst_ninh-binh", name: "Ninh Binh", slug: "ninh-binh" },
  { id: "dst_quang-nam", name: "Hoi An", slug: "quang-nam" },
  { id: "dst_quang-ninh", name: "Ha Long Bay", slug: "quang-ninh" },
  { id: "dst_thua-thien-hue", name: "Hue", slug: "thua-thien-hue" },
  { id: "dst_da-nang", name: "Da Nang", slug: "da-nang" },
  { id: "dst_lao-cai", name: "Sapa", slug: "lao-cai" },
  { id: "dst_mekong", name: "Mekong Delta", slug: "mekong" },
  { id: "dst_khanh-hoa", name: "Nha Trang", slug: "khanh-hoa" },
  { id: "dst_siem-reap", name: "Siem Reap", slug: "siem-reap" },
  { id: "dst_phnom-penh", name: "Phnom Penh", slug: "phnom-penh" },
  { id: "dst_luang-prabang", name: "Luang Prabang", slug: "luang-prabang" },
  { id: "dst_vientiane", name: "Vientiane", slug: "vientiane" },
  { id: "dst_bangkok", name: "Bangkok", slug: "bangkok" },
  { id: "dst_chiang-mai", name: "Chiang Mai", slug: "chiang-mai" },
  { id: "dst_phuket", name: "Phuket", slug: "phuket" },
];

export function useDestinationSearch(query: string) {
  const deferredQuery = useDeferredValue(query.trim());
  const hasQuery = deferredQuery.length > 0;

  const url = `${API_BASE}/api/v2/destinations?query=${encodeURIComponent(deferredQuery)}&limit=25`;

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
      matchedFrom: item.matchedFrom,
    }));
  }, [hasQuery, data]);

  return {
    results,
    isLoading: isLoading && !data,
    error: error ? "Destination catalog is temporarily unavailable." : null,
    hasQuery,
  };
}
