"use client";

import React, { useState } from "react";
import { Search, PackageOpen } from "lucide-react";
import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";
import { DataViewToggle, type ViewModeOption } from "./DataViewToggle.tsx";
import { DataGrid } from "./DataGrid.tsx";
import { DataTable, type ColumnDef } from "./DataTable.tsx";
import { DataKanban, type KanbanConfig } from "./DataKanban.tsx";

export interface FilterOption {
  label: string;
  value: string;
}

export interface DataViewContainerProps<T> {
  // Data
  items: T[];
  keyExtractor: (item: T, index: number) => string;

  // Search & Filter
  search?: string;
  onSearchChange?: (val: string) => void;
  searchPlaceholder?: string;

  filters?: readonly FilterOption[];
  activeFilter?: string;
  onFilterChange?: (val: string) => void;

  // View Mode
  defaultViewMode?: ViewModeOption;
  viewMode?: ViewModeOption;
  onViewModeChange?: (mode: ViewModeOption) => void;

  // Renderers
  gridItemRenderer: (item: T, index: number) => React.ReactNode;
  tableColumns: ColumnDef<T>[];
  kanbanConfig?: KanbanConfig<T, string>;

  // State Overrides
  isLoading?: boolean;
  error?: Error | string | null;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyIcon?: React.ReactNode;
  actionButton?: React.ReactNode;
  headerTitleSlot?: React.ReactNode;

  // Custom ClassNames
  gridClassName?: string;
  tableContainerClassName?: string;
  className?: string;
}

export function DataViewContainer<T>({
  items,
  keyExtractor,
  search,
  onSearchChange,
  searchPlaceholder = "Search items…",
  filters,
  activeFilter,
  onFilterChange,
  defaultViewMode = "grid",
  viewMode: externalViewMode,
  onViewModeChange: externalOnViewModeChange,
  gridItemRenderer,
  tableColumns,
  kanbanConfig,
  isLoading = false,
  error,
  emptyTitle = "No items found",
  emptyDescription = "There are no items matching your current criteria.",
  emptyIcon = <PackageOpen size={40} className="mb-3 text-[var(--color-muted)]" />,
  actionButton,
  headerTitleSlot,
  gridClassName,
  tableContainerClassName,
  className,
}: DataViewContainerProps<T>) {
  const [internalViewMode, setInternalViewMode] = useState<ViewModeOption>(defaultViewMode);

  const requestedViewMode = externalViewMode ?? internalViewMode;
  const currentViewMode = requestedViewMode === "kanban" && !kanbanConfig ? "grid" : requestedViewMode;
  const handleViewModeChange = (mode: ViewModeOption) => {
    if (externalOnViewModeChange) {
      externalOnViewModeChange(mode);
    } else {
      setInternalViewMode(mode);
    }
  };

  return (
    <div className={cn("flex flex-col gap-6", className)}>
      {/* Header bar with title slot, search, filters & view toggle */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-3">
          {headerTitleSlot != null ? headerTitleSlot : null}

          {/* Search box */}
          {onSearchChange != null ? (
            <div className="relative min-w-[15rem] flex-1 sm:w-72 sm:flex-none">
              <Search
                size={18}
                className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--color-muted)]"
              />
              <input
                type="text"
                value={search ?? ""}
                onChange={(e) => onSearchChange(e.target.value)}
                placeholder={searchPlaceholder}
                className={cn(
                  getTypographyClassName("bodyMd"),
                  "min-h-11 w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] pl-10 pr-4 text-[var(--color-on-surface)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)]"
                )}
              />
            </div>
          ) : null}

          {/* Status Filter Pills */}
          {filters != null && filters.length > 0 && onFilterChange != null ? (
            <div className="flex items-center rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] p-1 shadow-2xs">
              {filters.map((filter) => (
                <button
                  key={filter.value}
                  type="button"
                  onClick={() => onFilterChange(filter.value)}
                  className={cn(
                    getTypographyClassName("caption"),
                    "rounded-[calc(var(--radius-button)-2px)] px-3 py-1.5 transition-all",
                    activeFilter === filter.value
                      ? "bg-[var(--color-accent)] text-white shadow-2xs"
                      : "text-[var(--color-muted)] hover:text-[var(--color-on-surface)]"
                  )}
                >
                  {filter.label}
                </button>
              ))}
            </div>
          ) : null}
        </div>

        {/* Action Button & View Toggle */}
        <div className="flex items-center gap-3">
          {actionButton}

          <DataViewToggle
            viewMode={currentViewMode}
            onViewModeChange={handleViewModeChange}
            kanbanAvailable={Boolean(kanbanConfig)}
          />
        </div>
      </div>

      {/* Main Content State: Error / Loading / Empty / Data */}
      {error ? (
        <div className="rounded-[var(--radius-card)] border border-rose-200 bg-rose-50/50 p-6 text-center text-rose-700">
          <p className={getTypographyClassName("bodyMd")}>
            {typeof error === "string" ? error : error.message || "Failed to load catalog data."}
          </p>
        </div>
      ) : isLoading ? (
        currentViewMode === "grid" ? (
          <div className={cn("grid gap-4 sm:grid-cols-2 lg:grid-cols-3", gridClassName)}>
            {[1, 2, 3, 4, 5, 6].map((idx) => (
              <div
                key={idx}
                className="h-44 animate-pulse rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5"
              />
            ))}
          </div>
        ) : (
          <div className="h-64 animate-pulse rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)]" />
        )
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-[var(--radius-card)] border border-dashed border-[var(--color-border-strong)] bg-[var(--color-surface)] p-12 text-center">
          {emptyIcon}
          <h3
            className={cn(
              getTypographyClassName("cardTitle"),
              "text-[var(--color-on-surface)]"
            )}
          >
            {emptyTitle}
          </h3>
          <p
            className={cn(
              getTypographyClassName("bodySm"),
              "mt-1 max-w-sm text-[var(--color-muted)]"
            )}
          >
            {emptyDescription}
          </p>
        </div>
      ) : currentViewMode === "kanban" && kanbanConfig ? <DataKanban items={items} keyExtractor={keyExtractor} kanbanConfig={kanbanConfig} /> : currentViewMode === "grid" ? (
        <DataGrid
          items={items}
          keyExtractor={keyExtractor}
          renderItem={gridItemRenderer}
          gridClassName={gridClassName}
        />
      ) : (
        <DataTable
          items={items}
          columns={tableColumns}
          keyExtractor={keyExtractor}
          containerClassName={tableContainerClassName}
        />
      )}
    </div>
  );
}
