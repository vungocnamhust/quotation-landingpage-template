"use client";

import { useMemo, useCallback } from "react";
import useSWR from "swr";
import { listRoomingHeuristics, type RoomingHeuristicRuleItem } from "../quotationApi.ts";
import {
  DEFAULT_FALLBACK_ROOMING_RULES,
  generateRoomSuggestions,
  type RoomingRule,
} from "../rules/partyReconciler.ts";

export function useRoomingHeuristics() {
  const { data, error, isLoading, mutate } = useSWR(
    "rooming-heuristics",
    listRoomingHeuristics,
    {
      revalidateOnFocus: false,
      dedupingInterval: 60000,
      fallbackData: {
        items: DEFAULT_FALLBACK_ROOMING_RULES as unknown as RoomingHeuristicRuleItem[],
        total: DEFAULT_FALLBACK_ROOMING_RULES.length,
      },
    }
  );

  const rules: RoomingRule[] = useMemo(() => {
    if (data?.items && data.items.length > 0) {
      return data.items as RoomingRule[];
    }
    return DEFAULT_FALLBACK_ROOMING_RULES;
  }, [data]);

  const evaluateSuggestions = useCallback(
    (
      adults: number = 2,
      children: number = 0,
      kidAges: number[] = [],
      lang: string = "en"
    ) => {
      return generateRoomSuggestions(adults, children, kidAges, lang, rules);
    },
    [rules]
  );

  return {
    rules,
    isLoading,
    error,
    mutate,
    evaluateSuggestions,
  };
}
