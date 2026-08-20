"use client";

import { useDeferredValue, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  CATEGORIES,
  type ComponentCategoryKey,
  type CategoryMeta,
  type GenericComponentItem,
} from "./tourComponentsCatalog.ts";

export function useTourComponentsState() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Active Category selection
  const activeCategoryParam =
    (searchParams.get("category") as ComponentCategoryKey) || "accommodations";
  const [activeCategory, setActiveCategory] = useState<ComponentCategoryKey>(activeCategoryParam);

  const currentCategoryMeta: CategoryMeta = useMemo(
    () => CATEGORIES.find((c) => c.key === activeCategory) ?? CATEGORIES[0],
    [activeCategory]
  );

  // Search & Filter state
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState<"all" | "true" | "false">("all");
  const [travelStyleGroupFilter, setTravelStyleGroupFilter] = useState<string>("all");

  const deferredSearch = useDeferredValue(search);

  const handleCategoryChange = (key: ComponentCategoryKey) => {
    setActiveCategory(key);
    setSearch("");
    setTravelStyleGroupFilter("all");
    router.replace(`/workspace/components?category=${key}`, { scroll: false });
  };

  // Real empty storage for generic categories (Cars, Experiences, Tickets, Destinations)
  // Ready to connect to backend endpoint when available
  const [genericCatalogStore] = useState<
    Record<Exclude<ComponentCategoryKey, "accommodations" | "travel_styles">, GenericComponentItem[]>
  >({
    cars: [],
    experiences: [],
    tickets: [],
    destinations: [],
  });

  const genericItems = useMemo(() => {
    if (activeCategory === "accommodations" || activeCategory === "travel_styles") {
      return [];
    }
    const list = genericCatalogStore[activeCategory] ?? [];
    if (!deferredSearch.trim()) return list;
    const lower = deferredSearch.toLowerCase();
    return list.filter(
      (item) =>
        item.name.toLowerCase().includes(lower) ||
        item.subtitle.toLowerCase().includes(lower) ||
        item.tags.some((t) => t.toLowerCase().includes(lower))
    );
  }, [activeCategory, genericCatalogStore, deferredSearch]);

  return {
    activeCategory,
    currentCategoryMeta,
    search,
    deferredSearch,
    activeFilter,
    travelStyleGroupFilter,
    genericItems,
    setSearch,
    setActiveFilter,
    setTravelStyleGroupFilter,
    handleCategoryChange,
  };
}
