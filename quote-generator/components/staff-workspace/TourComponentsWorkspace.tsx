"use client";

import { useCallback, useMemo, useState } from "react";
import { MapPin, Plus, Sparkles, Truck } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import { DataViewContainer } from "../ui/data-view/DataViewContainer.tsx";
import { WorkspaceNavigationLink } from "./WorkspaceNavigation.tsx";
import {
  updateProductStatus,
  updateSupplierStatus,
  type DestinationProfile,
  type ProductProfile,
  type SupplierProfile,
} from "../../lib/quotationApi.ts";
import {
  CATEGORIES,
  isProductComponentSlot,
  PRODUCT_CATEGORY_BY_SLOT,
} from "./tourComponentsCatalog.ts";
import { useTourComponentsState } from "./useTourComponentsState.ts";
import { useDestinationManager } from "./destinations/useDestinationManager.ts";
import { DestinationCard } from "./destinations/DestinationCard.tsx";
import { createDestinationColumns } from "./destinations/DestinationColumns.tsx";
import { DestinationDrawerModal } from "./destinations/DestinationDrawerModal.tsx";
import { SupplierCard } from "./suppliers/SupplierCard.tsx";
import { createSupplierColumns } from "./suppliers/SupplierColumns.tsx";
import { ProductCard } from "./products/ProductCard.tsx";
import { createProductColumns } from "./products/ProductColumns.tsx";
import {
  SupplierManageDrawer,
  useSupplierSearch,
  type SupplierDrawerMode,
} from "../supplier/index.ts";
import {
  ProductManageDrawer,
  useProductSearch,
  type ProductDrawerMode,
} from "../product/index.ts";

function CatalogActionButton({
  label,
  onClick,
}: {
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        getTypographyClassName("buttonPrimary"),
        "flex items-center justify-center gap-2 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-4 py-2.5 text-white shadow-xs transition-all hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] cursor-pointer",
      )}
    >
      <Plus size={18} aria-hidden="true" />
      <span>{label}</span>
    </button>
  );
}

export default function TourComponentsWorkspace() {
  const {
    activeCategory,
    currentCategoryMeta,
    search,
    deferredSearch,
    activeFilter,
    setSearch,
    setActiveFilter,
    handleCategoryChange,
  } = useTourComponentsState();
  const isDestinationActive = activeCategory === "destinations";
  const isSupplierActive = activeCategory === "suppliers";
  const isProductSlotActive = isProductComponentSlot(activeCategory);
  const productCategories = isProductSlotActive
    ? PRODUCT_CATEGORY_BY_SLOT[activeCategory]
    : undefined;

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
  const [supplierDrawerMode, setSupplierDrawerMode] =
    useState<SupplierDrawerMode>(null);
  const [editingSupplier, setEditingSupplier] =
    useState<SupplierProfile | null>(null);
  const [supplierPending, setSupplierPending] = useState(false);
  const {
    items: productItems,
    isLoading: isProductLoading,
    error: productError,
    mutate: mutateProducts,
  } = useProductSearch(deferredSearch, {
    active: activeFilter,
    category: productCategories,
    enabled: isProductSlotActive,
  });
  const [productDrawerMode, setProductDrawerMode] =
    useState<ProductDrawerMode>(null);
  const [editingProduct, setEditingProduct] = useState<ProductProfile | null>(
    null,
  );
  const [productPending, setProductPending] = useState(false);

  const openCreateSupplier = useCallback(() => {
    setEditingSupplier(null);
    setSupplierDrawerMode("create");
  }, []);
  const openEditSupplier = useCallback((supplier: SupplierProfile) => {
    setEditingSupplier(supplier);
    setSupplierDrawerMode("edit");
  }, []);
  const closeSupplierDrawer = useCallback(() => {
    setSupplierDrawerMode(null);
    setEditingSupplier(null);
  }, []);
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
    [mutateSuppliers],
  );
  const openCreateProduct = useCallback(() => {
    setEditingProduct(null);
    setProductDrawerMode("create");
  }, []);
  const openEditProduct = useCallback((product: ProductProfile) => {
    setEditingProduct(product);
    setProductDrawerMode("edit");
  }, []);
  const closeProductDrawer = useCallback(() => {
    setProductDrawerMode(null);
    setEditingProduct(null);
  }, []);
  const toggleProductStatus = useCallback(
    async (product: ProductProfile) => {
      setProductPending(true);
      try {
        await updateProductStatus(product.id, !product.is_active);
        await mutateProducts();
      } finally {
        setProductPending(false);
      }
    },
    [mutateProducts],
  );

  const destinationColumns = useMemo(
    () =>
      createDestinationColumns(openEditDestination, toggleDestinationStatus),
    [openEditDestination, toggleDestinationStatus],
  );
  const supplierColumns = useMemo(
    () => createSupplierColumns(openEditSupplier, toggleSupplierStatus),
    [openEditSupplier, toggleSupplierStatus],
  );
  const productColumns = useMemo(
    () =>
      createProductColumns(
        openEditProduct,
        (product) => void toggleProductStatus(product),
      ),
    [openEditProduct, toggleProductStatus],
  );
  const standardFilters = [
    { label: "All", value: "all" },
    { label: "Active", value: "true" },
    { label: "Inactive", value: "false" },
  ];
  const setStandardFilter = (value: string) =>
    setActiveFilter(value as "all" | "true" | "false");

  return (
    <main className="flex flex-col gap-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p
            className={cn(
              getTypographyClassName("overline"),
              "text-[var(--color-accent)]",
            )}
          >
            Commercial operations
          </p>
          <h1
            className={cn(
              getTypographyClassName("pageTitle"),
              "mt-1 text-[var(--color-on-surface)]",
            )}
          >
            Product Catalog
          </h1>
          <p
            className={cn(
              getTypographyClassName("bodyLg"),
              "mt-1 text-[var(--color-muted)]",
            )}
          >
            {currentCategoryMeta.description}
          </p>
        </div>
        <WorkspaceNavigationLink
          href="/workspace/catalog-import"
          className={cn(
            getTypographyClassName("buttonPrimary"),
            "flex items-center gap-2 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-accent-wash)] px-5 py-3 text-[var(--color-accent)] shadow-xs transition-all hover:bg-[var(--color-surface-hover)]",
          )}
        >
          <Sparkles size={16} aria-hidden="true" />
          <span>Import từ văn bản</span>
        </WorkspaceNavigationLink>
      </header>

      <div
        className="flex gap-2 overflow-x-auto pb-1"
        role="tablist"
        aria-label="Product catalog categories"
      >
        {CATEGORIES.map((category) => {
          const Icon = category.icon;
          const isActive = activeCategory === category.key;
          return (
            <button
              key={category.key}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => handleCategoryChange(category.key)}
              className={cn(
                getTypographyClassName("buttonSecondary"),
                "flex shrink-0 items-center gap-2 rounded-[var(--radius-button)] px-4 py-2.5 transition-all cursor-pointer",
                isActive
                  ? "border border-[var(--color-border-strong)] bg-[var(--color-accent)] text-white shadow-xs"
                  : "border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:border-[var(--color-border-strong)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)]",
              )}
            >
              <Icon size={16} aria-hidden="true" />
              <span>{category.label}</span>
            </button>
          );
        })}
      </div>

      {isDestinationActive ? (
        <DataViewContainer<DestinationProfile>
          items={destinationItems}
          keyExtractor={(item) => item.id}
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Search destinations by name or alias…"
          filters={standardFilters}
          activeFilter={activeFilter}
          onFilterChange={setStandardFilter}
          isLoading={isDestinationLoading}
          error={destinationError}
          emptyTitle={currentCategoryMeta.emptyTitle}
          emptyDescription={
            search
              ? "No destinations match your search query."
              : currentCategoryMeta.emptyDescription
          }
          emptyIcon={
            <MapPin size={40} className="mb-3 text-[var(--color-muted)]" />
          }
          actionButton={
            <CatalogActionButton
              label={currentCategoryMeta.actionLabel}
              onClick={openCreateDestination}
            />
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
        <DataViewContainer<SupplierProfile>
          items={supplierItems}
          keyExtractor={(item) => item.id}
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Search suppliers by name or legal name…"
          filters={standardFilters}
          activeFilter={activeFilter}
          onFilterChange={setStandardFilter}
          isLoading={isSupplierLoading || supplierPending}
          error={supplierError}
          emptyTitle={currentCategoryMeta.emptyTitle}
          emptyDescription={
            search
              ? "No suppliers match your search query."
              : currentCategoryMeta.emptyDescription
          }
          emptyIcon={
            <Truck size={40} className="mb-3 text-[var(--color-muted)]" />
          }
          actionButton={
            <CatalogActionButton
              label={currentCategoryMeta.actionLabel}
              onClick={openCreateSupplier}
            />
          }
          gridItemRenderer={(profile) => (
            <SupplierCard
              key={profile.id}
              profile={profile}
              onEdit={openEditSupplier}
              onToggleStatus={(supplier) => void toggleSupplierStatus(supplier)}
            />
          )}
          tableColumns={supplierColumns}
        />
      ) : (
        <DataViewContainer<ProductProfile>
          items={productItems}
          keyExtractor={(item) => item.id}
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder={`Search ${currentCategoryMeta.label.toLowerCase()}…`}
          filters={standardFilters}
          activeFilter={activeFilter}
          onFilterChange={setStandardFilter}
          isLoading={isProductLoading || productPending}
          error={productError}
          emptyTitle={currentCategoryMeta.emptyTitle}
          emptyDescription={
            search
              ? `No ${currentCategoryMeta.label.toLowerCase()} match your search query.`
              : currentCategoryMeta.emptyDescription
          }
          emptyIcon={
            <currentCategoryMeta.icon
              size={40}
              className="mb-3 text-[var(--color-muted)]"
            />
          }
          actionButton={
            <CatalogActionButton
              label={currentCategoryMeta.actionLabel}
              onClick={openCreateProduct}
            />
          }
          gridItemRenderer={(profile) => (
            <ProductCard
              key={profile.id}
              profile={profile}
              onEdit={openEditProduct}
              onToggleStatus={(product) => void toggleProductStatus(product)}
            />
          )}
          tableColumns={productColumns}
        />
      )}

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
      <SupplierManageDrawer
        mode={supplierDrawerMode}
        editingSupplier={editingSupplier}
        onClose={closeSupplierDrawer}
        onSaved={() => void mutateSuppliers()}
        onMutate={mutateSuppliers}
      />
      {productDrawerMode && productCategories ? (
        <ProductManageDrawer
          key={
            editingProduct
              ? `edit:${editingProduct.id}`
              : `create:${activeCategory}`
          }
          mode={productDrawerMode}
          editingProduct={editingProduct}
          presetCategory={productCategories[0]}
          onClose={closeProductDrawer}
          onSaved={() => void mutateProducts()}
          onMutate={mutateProducts}
        />
      ) : null}
    </main>
  );
}
