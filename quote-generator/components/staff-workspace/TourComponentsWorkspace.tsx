"use client";

import { useCallback, useMemo, useState } from "react";
import { Building2, Palette, Plus, MapPin, Truck } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import { DataViewContainer } from "../ui/data-view/DataViewContainer.tsx";
import { updateSupplierStatus, type AccommodationProfile, type DestinationProfile, type SupplierProfile } from "../../lib/quotationApi.ts";
import {
  CATEGORIES,
  type FlatTravelStyleTag,
  type GenericComponentItem,
} from "./tourComponentsCatalog.ts";
import { useTourComponentsState } from "./useTourComponentsState.ts";
import { useAccommodationManager } from "./accommodations/useAccommodationManager.ts";
import { useTravelStyleCatalog } from "./travel-styles/useTravelStyleCatalog.ts";
import { useDestinationManager } from "./destinations/useDestinationManager.ts";
import { AccommodationCard } from "./accommodations/AccommodationCard.tsx";
import { createAccommodationColumns } from "./accommodations/AccommodationColumns.tsx";
import { AccommodationDrawerModal } from "./accommodations/AccommodationDrawerModal.tsx";
import { DestinationCard } from "./destinations/DestinationCard.tsx";
import { createDestinationColumns } from "./destinations/DestinationColumns.tsx";
import { DestinationDrawerModal } from "./destinations/DestinationDrawerModal.tsx";
import { TravelStyleCard } from "./travel-styles/TravelStyleCard.tsx";
import { createTravelStyleColumns } from "./travel-styles/TravelStyleColumns.tsx";
import { GenericCatalogCard } from "./catalog/GenericCatalogCard.tsx";
import { createGenericCatalogColumns } from "./catalog/GenericCatalogColumns.tsx";
import { SupplierCard } from "./suppliers/SupplierCard.tsx";
import { createSupplierColumns } from "./suppliers/SupplierColumns.tsx";
import { SupplierManageDrawer, useSupplierSearch, type SupplierDrawerMode } from "../supplier/index.ts";

export default function TourComponentsWorkspace() {
  const {
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
  } = useTourComponentsState();

  const isAccommodationActive = activeCategory === "accommodations";
  const isTravelStyleActive = activeCategory === "travel_styles";
  const isDestinationActive = activeCategory === "destinations";
  const isSupplierActive = activeCategory === "suppliers";

  const {
    items: accommodationItems,
    isLoading: isAccommodationLoading,
    error: accommodationError,
    isDrawerOpen: isAccommodationDrawerOpen,
    editing: editingAccommodation,
    draft: accommodationDraft,
    destinationRef,
    pending: isAccommodationPending,
    message: accommodationMessage,
    setDraft: setAccommodationDraft,
    setDestinationRef,
    openCreate: openCreateAccommodation,
    openEdit: openEditAccommodation,
    closeDrawer: closeAccommodationDrawer,
    saveAccommodation,
    uploadAsset,
    toggleAccommodationStatus,
  } = useAccommodationManager(isAccommodationActive, activeFilter, deferredSearch);

  const {
    items: travelStyleItems,
    isLoading: isTravelStyleLoading,
    error: travelStyleError,
  } = useTravelStyleCatalog(isTravelStyleActive, travelStyleGroupFilter, deferredSearch);

  const {
    items: destinationItems,
    isLoading: isDestinationLoading,
    error: destinationError,
    isDrawerOpen: isDestinationDrawerOpen,
    editing: editingDestination,
    draft: destinationDraft,
    pending: isDestinationPending,
    message: destinationMessage,
    setDraft: setDestinationDraft,
    openCreate: openCreateDestination,
    openEdit: openEditDestination,
    closeDrawer: closeDestinationDrawer,
    saveDestination,
    toggleDestinationStatus,
  } = useDestinationManager(isDestinationActive, activeFilter, deferredSearch);

  const {
    items: supplierItems,
    isLoading: isSupplierLoading,
    error: supplierError,
    mutate: mutateSuppliers,
  } = useSupplierSearch(deferredSearch, {
    active: activeFilter,
    enabled: isSupplierActive,
  });
  const [supplierDrawerMode, setSupplierDrawerMode] = useState<SupplierDrawerMode>(null);
  const [editingSupplier, setEditingSupplier] = useState<SupplierProfile | null>(null);
  const [supplierPending, setSupplierPending] = useState(false);

  const openCreateSupplier = () => {
    setEditingSupplier(null);
    setSupplierDrawerMode("create");
  };
  const openEditSupplier = (supplier: SupplierProfile) => {
    setEditingSupplier(supplier);
    setSupplierDrawerMode("edit");
  };
  const closeSupplierDrawer = () => {
    setSupplierDrawerMode(null);
    setEditingSupplier(null);
  };
  const toggleSupplierStatus = useCallback(
    async (supplier: SupplierProfile) => {
      setSupplierPending(true);
      try {
        await updateSupplierStatus(supplier.id, !supplier.is_active);
        await mutateSuppliers();
      } finally {
        setSupplierPending(false);
      }
    },
    [mutateSuppliers]
  );

  const accommodationColumns = useMemo(
    () => createAccommodationColumns(openEditAccommodation, toggleAccommodationStatus),
    [openEditAccommodation, toggleAccommodationStatus]
  );

  const destinationColumns = useMemo(
    () => createDestinationColumns(openEditDestination, toggleDestinationStatus),
    [openEditDestination, toggleDestinationStatus]
  );

  const travelStyleColumns = useMemo(() => createTravelStyleColumns(), []);
  const genericColumns = useMemo(() => createGenericCatalogColumns(), []);
  const supplierColumns = useMemo(
    () => createSupplierColumns(openEditSupplier, toggleSupplierStatus),
    [toggleSupplierStatus]
  );

  return (
    <main className="flex flex-col gap-6">
      {/* Header section */}
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p
            className={cn(
              getTypographyClassName("overline"),
              "text-[var(--color-accent)]"
            )}
          >
            Catalog management
          </p>
          <h1
            className={cn(
              getTypographyClassName("pageTitle"),
              "mt-1 text-[var(--color-on-surface)]"
            )}
          >
            Tour Components
          </h1>
          <p
            className={cn(
              getTypographyClassName("bodyLg"),
              "mt-1 text-[var(--color-muted)]"
            )}
          >
            {currentCategoryMeta.description}
          </p>
        </div>
      </header>

      {/* Sub-category Pills Navigation */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {CATEGORIES.map((cat) => {
          const Icon = cat.icon;
          const isActive = activeCategory === cat.key;
          return (
            <button
              key={cat.key}
              type="button"
              onClick={() => handleCategoryChange(cat.key)}
              className={cn(
                getTypographyClassName("buttonSecondary"),
                "flex shrink-0 items-center gap-2 rounded-[var(--radius-button)] px-4 py-2.5 transition-all cursor-pointer",
                isActive
                  ? "border border-[var(--color-border-strong)] bg-[var(--color-accent)] text-white shadow-xs"
                  : "border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:border-[var(--color-border-strong)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)]"
              )}
            >
              <Icon size={16} aria-hidden="true" />
              <span>{cat.label}</span>
            </button>
          );
        })}
      </div>

      {/* Category 1: Accommodations */}
      {isAccommodationActive ? (
        <DataViewContainer<AccommodationProfile>
          items={accommodationItems}
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
          isLoading={isAccommodationLoading}
          error={accommodationError}
          emptyTitle={currentCategoryMeta.emptyTitle}
          emptyDescription={
            search
              ? "No accommodations match your search query."
              : currentCategoryMeta.emptyDescription
          }
          emptyIcon={<Building2 size={40} className="mb-3 text-[var(--color-muted)]" />}
          actionButton={
            <button
              type="button"
              onClick={openCreateAccommodation}
              className={cn(
                getTypographyClassName("buttonPrimary"),
                "flex items-center justify-center gap-2 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-4 py-2.5 text-white shadow-xs transition-all hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] cursor-pointer"
              )}
            >
              <Plus size={18} />
              <span>{currentCategoryMeta.actionLabel}</span>
            </button>
          }
          gridItemRenderer={(profile) => (
            <AccommodationCard
              key={profile.id}
              profile={profile}
              onEdit={openEditAccommodation}
              onToggleStatus={toggleAccommodationStatus}
            />
          )}
          tableColumns={accommodationColumns}
        />
      ) : isTravelStyleActive ? (
        /* Category 2: Real Database Travel Styles */
        <DataViewContainer<FlatTravelStyleTag>
          items={travelStyleItems}
          keyExtractor={(tag) => tag.id}
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Search travel styles by name, slug or group…"
          filters={[
            { label: "All Groups", value: "all" },
            { label: "Group Composition", value: "group_composition" },
            { label: "Tour Type", value: "tour_type" },
            { label: "Purpose & Theme", value: "purpose" },
            { label: "Interest & Experience", value: "interest_experience" },
          ]}
          activeFilter={travelStyleGroupFilter}
          onFilterChange={setTravelStyleGroupFilter}
          isLoading={isTravelStyleLoading}
          error={travelStyleError}
          emptyTitle={currentCategoryMeta.emptyTitle}
          emptyDescription={
            search
              ? "No travel style tags match your search query."
              : currentCategoryMeta.emptyDescription
          }
          emptyIcon={<Palette size={40} className="mb-3 text-[var(--color-muted)]" />}
          gridItemRenderer={(tag) => <TravelStyleCard key={tag.id} tag={tag} />}
          tableColumns={travelStyleColumns}
        />
      ) : isDestinationActive ? (
        /* Category 3: Real Database Destinations */
        <DataViewContainer<DestinationProfile>
          items={destinationItems}
          keyExtractor={(item) => item.id}
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Search destinations by name or alias…"
          filters={[
            { label: "All", value: "all" },
            { label: "Active", value: "true" },
            { label: "Inactive", value: "false" },
          ]}
          activeFilter={activeFilter}
          onFilterChange={(val) => setActiveFilter(val as "all" | "true" | "false")}
          isLoading={isDestinationLoading}
          error={destinationError}
          emptyTitle={currentCategoryMeta.emptyTitle}
          emptyDescription={
            search
              ? "No destinations match your search query."
              : currentCategoryMeta.emptyDescription
          }
          emptyIcon={<MapPin size={40} className="mb-3 text-[var(--color-muted)]" />}
          actionButton={
            <button
              type="button"
              onClick={openCreateDestination}
              className={cn(
                getTypographyClassName("buttonPrimary"),
                "flex items-center justify-center gap-2 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-4 py-2.5 text-white shadow-xs transition-all hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] cursor-pointer"
              )}
            >
              <Plus size={18} />
              <span>{currentCategoryMeta.actionLabel}</span>
            </button>
          }
          gridItemRenderer={(profile) => (
            <DestinationCard
              key={profile.id}
              profile={profile}
              onEdit={openEditDestination}
              onToggleStatus={toggleDestinationStatus}
            />
          )}
          tableColumns={destinationColumns}
        />
      ) : isSupplierActive ? (
        /* Category: Suppliers (creditor-side registry) */
        <DataViewContainer<SupplierProfile>
          items={supplierItems}
          keyExtractor={(item) => item.id}
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Search suppliers by name or legal name…"
          filters={[
            { label: "All", value: "all" },
            { label: "Active", value: "true" },
            { label: "Inactive", value: "false" },
          ]}
          activeFilter={activeFilter}
          onFilterChange={(val) => setActiveFilter(val as "all" | "true" | "false")}
          isLoading={isSupplierLoading || supplierPending}
          error={supplierError}
          emptyTitle={currentCategoryMeta.emptyTitle}
          emptyDescription={
            search ? "No suppliers match your search query." : currentCategoryMeta.emptyDescription
          }
          emptyIcon={<Truck size={40} className="mb-3 text-[var(--color-muted)]" />}
          actionButton={
            <button
              type="button"
              onClick={openCreateSupplier}
              className={cn(
                getTypographyClassName("buttonPrimary"),
                "flex items-center justify-center gap-2 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-4 py-2.5 text-white shadow-xs transition-all hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] cursor-pointer"
              )}
            >
              <Plus size={18} />
              <span>{currentCategoryMeta.actionLabel}</span>
            </button>
          }
          gridItemRenderer={(profile) => (
            <SupplierCard key={profile.id} profile={profile} onEdit={openEditSupplier} onToggleStatus={(supplier) => void toggleSupplierStatus(supplier)} />
          )}
          tableColumns={supplierColumns}
        />
      ) : (
        /* Category 4..6: Cars, Experiences, Tickets (Clean Empty State) */
        <DataViewContainer<GenericComponentItem>
          items={genericItems}
          keyExtractor={(item) => item.id}
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder={`Search ${currentCategoryMeta.label.toLowerCase()}…`}
          emptyTitle={currentCategoryMeta.emptyTitle}
          emptyDescription={
            search
              ? `No ${currentCategoryMeta.label.toLowerCase()} match your search query.`
              : currentCategoryMeta.emptyDescription
          }
          emptyIcon={
            <currentCategoryMeta.icon size={40} className="mb-3 text-[var(--color-muted)]" />
          }
          actionButton={
            <button
              type="button"
              className={cn(
                getTypographyClassName("buttonPrimary"),
                "flex items-center justify-center gap-2 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-4 py-2.5 text-white shadow-xs transition-all hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] cursor-pointer"
              )}
            >
              <Plus size={18} />
              <span>{currentCategoryMeta.actionLabel}</span>
            </button>
          }
          gridItemRenderer={(item) => <GenericCatalogCard key={item.id} item={item} />}
          tableColumns={genericColumns}
        />
      )}

      {/* Accommodations Drawer Modal */}
      <AccommodationDrawerModal
        isOpen={isAccommodationDrawerOpen}
        editing={editingAccommodation}
        draft={accommodationDraft}
        destinationRef={destinationRef}
        pending={isAccommodationPending}
        message={accommodationMessage}
        onClose={closeAccommodationDrawer}
        onDraftChange={setAccommodationDraft}
        onDestinationChange={setDestinationRef}
        onUploadAsset={(target, file) => void uploadAsset(target, file)}
        onSave={() => void saveAccommodation()}
      />

      {/* Destinations Drawer Modal */}
      <DestinationDrawerModal
        isOpen={isDestinationDrawerOpen}
        editing={editingDestination}
        draft={destinationDraft}
        pending={isDestinationPending}
        message={destinationMessage}
        onClose={closeDestinationDrawer}
        onDraftChange={setDestinationDraft}
        onSave={() => void saveDestination()}
      />

      {/* Supplier Manage Drawer */}
      <SupplierManageDrawer
        mode={supplierDrawerMode}
        editingSupplier={editingSupplier}
        onClose={closeSupplierDrawer}
        onSaved={() => void mutateSuppliers()}
        onMutate={mutateSuppliers}
      />
    </main>
  );
}

