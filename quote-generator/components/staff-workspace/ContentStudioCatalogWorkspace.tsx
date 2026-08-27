"use client";

import { useMemo, useState } from "react";
import { Building2, Palette, Plus } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import { DataViewContainer } from "../ui/data-view/DataViewContainer.tsx";
import type { AccommodationProfile } from "../../lib/quotationApi.ts";
import type { FlatTravelStyleTag } from "./tourComponentsCatalog.ts";
import { useAccommodationManager } from "./accommodations/useAccommodationManager.ts";
import { AccommodationCard } from "./accommodations/AccommodationCard.tsx";
import { createAccommodationColumns } from "./accommodations/AccommodationColumns.tsx";
import { AccommodationDrawerModal } from "./accommodations/AccommodationDrawerModal.tsx";
import { useTravelStyleCatalog } from "./travel-styles/useTravelStyleCatalog.ts";
import { TravelStyleCard } from "./travel-styles/TravelStyleCard.tsx";
import { createTravelStyleColumns } from "./travel-styles/TravelStyleColumns.tsx";

type ContentCatalogTab = "accommodations" | "travel_styles";
const STATUS_FILTERS = [
  { label: "All", value: "all" },
  { label: "Active", value: "true" },
  { label: "Inactive", value: "false" },
];
const TRAVEL_STYLE_FILTERS = [
  { label: "All Groups", value: "all" },
  { label: "Group Composition", value: "group_composition" },
  { label: "Tour Type", value: "tour_type" },
  { label: "Purpose & Theme", value: "purpose" },
  { label: "Interest & Experience", value: "interest_experience" },
];

export default function ContentStudioCatalogWorkspace() {
  const [activeTab, setActiveTab] =
    useState<ContentCatalogTab>("accommodations");
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState<"all" | "true" | "false">(
    "all",
  );
  const [travelStyleGroupFilter, setTravelStyleGroupFilter] = useState("all");
  const isAccommodationActive = activeTab === "accommodations";
  const isTravelStyleActive = activeTab === "travel_styles";

  const {
    items: accommodationItems,
    isLoading: isAccommodationLoading,
    error: accommodationError,
    isDrawerOpen,
    editing,
    draft,
    destinationRef,
    pending,
    message,
    setDraft,
    setDestinationRef,
    openCreate,
    openEdit,
    closeDrawer,
    saveAccommodation,
    uploadAsset,
    toggleAccommodationStatus,
  } = useAccommodationManager(isAccommodationActive, activeFilter, search);
  const {
    items: travelStyleItems,
    isLoading: isTravelStyleLoading,
    error: travelStyleError,
  } = useTravelStyleCatalog(
    isTravelStyleActive,
    travelStyleGroupFilter,
    search,
  );
  const accommodationColumns = useMemo(
    () => createAccommodationColumns(openEdit, toggleAccommodationStatus),
    [openEdit, toggleAccommodationStatus],
  );
  const travelStyleColumns = useMemo(() => createTravelStyleColumns(), []);

  const selectTab = (tab: ContentCatalogTab) => {
    setActiveTab(tab);
    setSearch("");
    setActiveFilter("all");
    setTravelStyleGroupFilter("all");
  };

  return (
    <main className="flex flex-col gap-6">
      <header>
        <p
          className={cn(
            getTypographyClassName("overline"),
            "text-[var(--color-accent)]",
          )}
        >
          Editorial and taxonomy
        </p>
        <h1
          className={cn(
            getTypographyClassName("pageTitle"),
            "mt-1 text-[var(--color-on-surface)]",
          )}
        >
          Content Studio
        </h1>
        <p
          className={cn(
            getTypographyClassName("bodyLg"),
            "mt-1 text-[var(--color-muted)]",
          )}
        >
          Manage reusable property imagery, editorial accommodation profiles,
          and travel-style taxonomy.
        </p>
      </header>

      <div
        className="flex gap-2 overflow-x-auto pb-1"
        role="tablist"
        aria-label="Content studio catalogs"
      >
        <button
          type="button"
          role="tab"
          aria-selected={isAccommodationActive}
          onClick={() => selectTab("accommodations")}
          className={cn(
            getTypographyClassName("buttonSecondary"),
            "flex shrink-0 items-center gap-2 rounded-[var(--radius-button)] px-4 py-2.5 transition-all cursor-pointer",
            isAccommodationActive
              ? "border border-[var(--color-border-strong)] bg-[var(--color-accent)] text-white shadow-xs"
              : "border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:border-[var(--color-border-strong)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)]",
          )}
        >
          <Building2 size={16} aria-hidden="true" />
          <span>Accommodation Profiles</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={isTravelStyleActive}
          onClick={() => selectTab("travel_styles")}
          className={cn(
            getTypographyClassName("buttonSecondary"),
            "flex shrink-0 items-center gap-2 rounded-[var(--radius-button)] px-4 py-2.5 transition-all cursor-pointer",
            isTravelStyleActive
              ? "border border-[var(--color-border-strong)] bg-[var(--color-accent)] text-white shadow-xs"
              : "border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:border-[var(--color-border-strong)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)]",
          )}
        >
          <Palette size={16} aria-hidden="true" />
          <span>Travel Styles</span>
        </button>
      </div>

      {isAccommodationActive ? (
        <DataViewContainer<AccommodationProfile>
          items={accommodationItems}
          keyExtractor={(item) => item.id}
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Search accommodation profiles…"
          filters={STATUS_FILTERS}
          activeFilter={activeFilter}
          onFilterChange={(value) =>
            setActiveFilter(value as "all" | "true" | "false")
          }
          isLoading={isAccommodationLoading}
          error={accommodationError}
          emptyTitle="No accommodation profiles found"
          emptyDescription={
            search
              ? "No accommodation profiles match your search query."
              : "Add a property profile with its editorial details and brochure media."
          }
          emptyIcon={
            <Building2 size={40} className="mb-3 text-[var(--color-muted)]" />
          }
          actionButton={
            <button
              type="button"
              onClick={openCreate}
              className={cn(
                getTypographyClassName("buttonPrimary"),
                "flex items-center justify-center gap-2 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-4 py-2.5 text-white shadow-xs transition-all hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] cursor-pointer",
              )}
            >
              <Plus size={18} aria-hidden="true" />
              <span>Add accommodation profile</span>
            </button>
          }
          gridItemRenderer={(profile) => (
            <AccommodationCard
              key={profile.id}
              profile={profile}
              onEdit={openEdit}
              onToggleStatus={toggleAccommodationStatus}
            />
          )}
          tableColumns={accommodationColumns}
        />
      ) : (
        <DataViewContainer<FlatTravelStyleTag>
          items={travelStyleItems}
          keyExtractor={(item) => item.id}
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Search travel styles by name, slug, or group…"
          filters={TRAVEL_STYLE_FILTERS}
          activeFilter={travelStyleGroupFilter}
          onFilterChange={setTravelStyleGroupFilter}
          isLoading={isTravelStyleLoading}
          error={travelStyleError}
          emptyTitle="No travel styles found"
          emptyDescription={
            search
              ? "No travel styles match your search query."
              : "No travel styles found in the selected group."
          }
          emptyIcon={
            <Palette size={40} className="mb-3 text-[var(--color-muted)]" />
          }
          gridItemRenderer={(tag) => <TravelStyleCard key={tag.id} tag={tag} />}
          tableColumns={travelStyleColumns}
        />
      )}

      <AccommodationDrawerModal
        isOpen={isDrawerOpen}
        editing={editing}
        draft={draft}
        destinationRef={destinationRef}
        pending={pending}
        message={message}
        onClose={closeDrawer}
        onDraftChange={setDraft}
        onDestinationChange={setDestinationRef}
        onUploadAsset={(target, file) => void uploadAsset(target, file)}
        onSave={() => void saveAccommodation()}
      />
    </main>
  );
}
