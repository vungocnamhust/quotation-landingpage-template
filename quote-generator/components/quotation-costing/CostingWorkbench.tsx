"use client";

import { Loader2, PlusCircle } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import { useCostingWorkspace } from "./useCostingWorkspace.ts";
import { CostingSettingsBar } from "./CostingSettingsBar.tsx";
import { ServiceLinesTable } from "./ServiceLinesTable.tsx";
import { AddServiceLineFlow } from "./AddServiceLineFlow.tsx";
import type { CostingWorkbenchAnchor } from "./types.ts";

export interface CostingWorkbenchProps {
  anchor: CostingWorkbenchAnchor;
  /** Rendered above the workbench once a sheet exists — e.g. a "Create quotation from this sheet" CTA. */
  headerAction?: (sheetId: string) => React.ReactNode;
  className?: string;
}

/**
 * `CostingWorkbench` is the single shell for both Flow 1 (anchored to a
 * `quote_request`, opened from the request detail screen) and Flow 2
 * (anchored to a `quotation`, opened lazily from the workspace's Costing
 * stage). It resolves-or-creates the sheet for `anchor` and renders the same
 * grid + settings + add-line UI either way (15.4 §2.2).
 */
export function CostingWorkbench({ anchor, headerAction, className }: CostingWorkbenchProps) {
  const { sheetId, workbench, isLoading, isCreatingSheet, actionError, createSheet, updateSettings, addLine, removeLine } =
    useCostingWorkspace(anchor);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-16 text-[var(--color-muted)]">
        <Loader2 size={18} className="animate-spin" aria-hidden="true" />
        <span className={getTypographyClassName("bodySm")}>Loading costing sheet...</span>
      </div>
    );
  }

  if (!sheetId || !workbench) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-[var(--radius-card)] border border-dashed border-[var(--color-border)] px-6 py-12 text-center">
        <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>
          No costing sheet yet for this {anchor.requestId ? "request" : "quotation"}.
        </p>
        <button
          type="button"
          disabled={isCreatingSheet}
          onClick={() => createSheet()}
          className={cn(
            getTypographyClassName("buttonPrimary"),
            "flex items-center gap-2 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-5 py-2.5 text-white shadow-md transition-opacity hover:opacity-90 disabled:opacity-60 cursor-pointer",
          )}
        >
          <PlusCircle size={16} aria-hidden="true" />
          <span>Start costing sheet</span>
        </button>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col gap-4", className)}>
      {headerAction ? <div className="flex justify-end">{headerAction(sheetId)}</div> : null}

      {actionError ? (
        <div className={cn(getTypographyClassName("bodySm"), "rounded-[var(--radius-button)] border border-rose-300 bg-rose-50 px-3 py-2 text-rose-700")}>
          {actionError}
        </div>
      ) : null}

      <CostingSettingsBar
        sheet={workbench.sheet}
        summary={workbench.summary}
        lineCount={workbench.items.length}
        onUpdate={(input) => void updateSettings(input)}
      />

      <ServiceLinesTable workbench={workbench} onDeleteLine={(lineId) => void removeLine(lineId)} />

      <AddServiceLineFlow sheetCurrency={workbench.sheet.currency} onAdd={(input) => addLine(input)} />
    </div>
  );
}

export default CostingWorkbench;
