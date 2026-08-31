"use client";

import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";
import { AddServiceLineFlow } from "../AddServiceLineFlow.tsx";
import type { ProductCategory } from "../../product/types.ts";
import type { ServiceLineProfile, ServiceLineWriteInput } from "../types.ts";

export interface SwapLineDialogProps {
  line: ServiceLineProfile;
  sheetCurrency: string;
  onClose: () => void;
  onSwap: (input: Omit<ServiceLineWriteInput, "base_costing_revision">) => Promise<unknown>;
}

/**
 * Additive AI-drafter affordance (15.7 §2) — reuses the existing `AddServiceLineFlow`
 * catalog picker, pre-scoped to the flagged line's category, so the sale can pick a
 * replacement product without leaving the grid. It only adds the new line; the sale
 * deletes the superseded AI line with the row's existing delete control once satisfied,
 * the same way every other costing edit in this workbench already works — no new
 * "replace" endpoint or CAS semantics invented here.
 */
export function SwapLineDialog({ line, sheetCurrency, onClose, onSwap }: SwapLineDialogProps) {
  const initialCategory = line.category as ProductCategory;

  const handleAdd = async (input: Omit<ServiceLineWriteInput, "base_costing_revision">) => {
    const result = await onSwap(input);
    if (result) onClose();
    return result;
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        className="relative flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] shadow-2xl"
        role="dialog"
        aria-modal="true"
      >
        <div className="flex items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-surface-muted)] px-6 py-4">
          <div>
            <h3 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>Swap AI-drafted line</h3>
            <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
              Replacing &ldquo;{line.title}&rdquo; — pick a product, then delete the old line once satisfied.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className={cn(getTypographyClassName("buttonSecondary"), "rounded-lg px-2.5 py-1.5 text-[var(--color-muted)] hover:bg-[var(--color-surface)] cursor-pointer")}
          >
            Close
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-6">
          <AddServiceLineFlow sheetCurrency={sheetCurrency} initialCategory={initialCategory} onAdd={handleAdd} />
        </div>
      </div>
    </div>
  );
}

export default SwapLineDialog;
