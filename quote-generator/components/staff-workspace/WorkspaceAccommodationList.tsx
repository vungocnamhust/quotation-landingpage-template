"use client";

import { useDeferredValue, useMemo, useState } from "react";
import { Plus, Building2 } from "lucide-react";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";
import { DataViewContainer } from "../ui/data-view/DataViewContainer";
import type { AccommodationProfile } from "../../lib/quotationApi";
import { useAccommodationManager } from "./accommodations/useAccommodationManager";
import { AccommodationCard } from "./accommodations/AccommodationCard";
import { createAccommodationColumns } from "./accommodations/AccommodationColumns";
import { AccommodationDrawerModal } from "./accommodations/AccommodationDrawerModal";

export default function WorkspaceAccommodationList() {
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState<"all" | "true" | "false">("all");
  const deferredSearch = useDeferredValue(search);

  const {
    items,
    isLoading,
    error,
    isDrawerOpen,
    editing,
    draft,
    destinationRef,
    message,
    pending,
    setDraft,
    setDestinationRef,
    openCreate,
    openEdit,
    closeDrawer,
    saveAccommodation,
    uploadAsset,
    toggleAccommodationStatus,
  } = useAccommodationManager(true, activeFilter, deferredSearch);

  const accommodationColumns = useMemo(
    () => createAccommodationColumns(openEdit, toggleAccommodationStatus),
    [openEdit, toggleAccommodationStatus]
  );

  return (
    <div className="flex flex-col gap-6">
      <DataViewContainer<AccommodationProfile>
        items={items}
        keyExtractor={(item) => item.id}
        search={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search accommodations…"
        filters={[
          { label: "All", value: "all" },
          { label: "Active", value: "true" },
          { label: "Inactive", value: "false" },
        ]}
        activeFilter={activeFilter}
        onFilterChange={(val) => setActiveFilter(val as "all" | "true" | "false")}
        isLoading={isLoading}
        error={error}
        emptyTitle="No accommodations found"
        emptyDescription={
          search
            ? "No accommodations match your search query."
            : "Start by adding your first accommodation profile to the catalog."
        }
        emptyIcon={<Building2 size={40} className="mb-3 text-[var(--color-muted)]" />}
        actionButton={
          <button
            type="button"
            onClick={openCreate}
            className={cn(
              getTypographyClassName("buttonPrimary"),
              "flex items-center justify-center gap-2 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-4 py-2.5 text-white shadow-xs transition-all hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] cursor-pointer"
            )}
          >
            <Plus size={18} />
            <span>Add accommodation</span>
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
    </div>
  );
}
