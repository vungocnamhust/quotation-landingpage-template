"use client";

import { useDeferredValue, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { CATEGORIES, type ComponentCategoryKey, type CategoryMeta } from "./tourComponentsCatalog.ts";

export function useTourComponentsState() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Active Category selection
  const activeCategoryParam = searchParams.get("category");
  const initialCategory = CATEGORIES.some((category) => category.key === activeCategoryParam)
    ? (activeCategoryParam as ComponentCategoryKey)
    : "hotels";
  const [activeCategory, setActiveCategory] = useState<ComponentCategoryKey>(initialCategory);

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
    setActiveFilter("all");
    setTravelStyleGroupFilter("all");
    router.replace(`/workspace/catalog?category=${key}`, { scroll: false });
  };

  return {
    activeCategory,
    currentCategoryMeta,
    search,
    deferredSearch,
    activeFilter,
    travelStyleGroupFilter,
    setSearch,
    setActiveFilter,
    setTravelStyleGroupFilter,
    handleCategoryChange,
  };
}
