"use client";

import { useMemo } from "react";
import useSWR from "swr";
import { listTravelStyles } from "../../../lib/quotationApi.ts";
import type { FlatTravelStyleTag } from "../tourComponentsCatalog.ts";

export function useTravelStyleCatalog(
  enabled: boolean,
  groupFilter: string,
  deferredSearch: string
) {
  const {
    data: travelStyleResponse,
    error,
    isLoading,
    mutate,
  } = useSWR(enabled ? ["travel-styles"] : null, listTravelStyles);

  const items = useMemo(() => {
    if (!enabled || !travelStyleResponse?.categories) {
      return [];
    }

    const searchTrimmed = deferredSearch.trim().toLowerCase();
    const result: FlatTravelStyleTag[] = [];

    for (const catGroup of travelStyleResponse.categories) {
      for (const tag of catGroup.tags) {
        // Group filter check
        if (groupFilter !== "all" && tag.category !== groupFilter) {
          continue;
        }

        // Search query check
        if (searchTrimmed) {
          const match =
            tag.name_en.toLowerCase().includes(searchTrimmed) ||
            tag.name_vi.toLowerCase().includes(searchTrimmed) ||
            tag.slug.toLowerCase().includes(searchTrimmed) ||
            catGroup.title_en.toLowerCase().includes(searchTrimmed);
          if (!match) continue;
        }

        result.push({
          ...tag,
          categoryTitleEn: catGroup.title_en,
          categoryTitleVi: catGroup.title_vi,
        });
      }
    }

    return result;
  }, [enabled, travelStyleResponse, groupFilter, deferredSearch]);

  return {
    items,
    isLoading,
    error,
    mutate,
  };
}
