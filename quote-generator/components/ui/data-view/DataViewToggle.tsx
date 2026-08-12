"use client";

import React from "react";
import { LayoutGrid, Table } from "lucide-react";
import { getTypographyClassName } from "../../../config/typography";
import { cn } from "../../../utils/cn";

export type ViewModeOption = "grid" | "table";

export interface DataViewToggleProps {
  viewMode: ViewModeOption;
  onViewModeChange: (mode: ViewModeOption) => void;
  className?: string;
}

export const DataViewToggle = React.memo(function DataViewToggle({
  viewMode,
  onViewModeChange,
  className,
}: DataViewToggleProps) {
  return (
    <div
      role="group"
      aria-label="View mode toggle"
      className={cn(
        "inline-flex items-center rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] p-1 shadow-2xs",
        className
      )}
    >
      <button
        type="button"
        aria-label="Grid view"
        aria-pressed={viewMode === "grid"}
        onClick={() => onViewModeChange("grid")}
        className={cn(
          getTypographyClassName("caption"),
          "inline-flex items-center gap-1.5 rounded-[calc(var(--radius-button)-2px)] px-2.5 py-1.5 transition-all",
          viewMode === "grid"
            ? "bg-[var(--color-accent)] text-white shadow-2xs"
            : "text-[var(--color-muted)] hover:text-[var(--color-on-surface)]"
        )}
      >
        <LayoutGrid size={15} aria-hidden="true" />
        <span className="hidden sm:inline">Grid</span>
      </button>

      <button
        type="button"
        aria-label="Table view"
        aria-pressed={viewMode === "table"}
        onClick={() => onViewModeChange("table")}
        className={cn(
          getTypographyClassName("caption"),
          "inline-flex items-center gap-1.5 rounded-[calc(var(--radius-button)-2px)] px-2.5 py-1.5 transition-all",
          viewMode === "table"
            ? "bg-[var(--color-accent)] text-white shadow-2xs"
            : "text-[var(--color-muted)] hover:text-[var(--color-on-surface)]"
        )}
      >
        <Table size={15} aria-hidden="true" />
        <span className="hidden sm:inline">Table</span>
      </button>
    </div>
  );
});
