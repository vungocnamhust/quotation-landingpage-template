"use client";

import { useState } from "react";
import { createPortal } from "react-dom";
import { Repeat, Sparkles, Trash2 } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import type { ServiceLineProfile, ServiceLineWriteInput } from "./types.ts";
import { formatMinorAmount as formatMinor } from "../../lib/moneyFormat.ts";
import { SwapLineDialog } from "./ai/SwapLineDialog.tsx";

// Mirrors schemas/service_draft.py DraftFlag — a line carrying either of these needs a
// sale decision before it should be trusted as-is (15.7 §2, ai_meta_json.flags).
const NEEDS_MANUAL_REVIEW_FLAGS = new Set(["rate_missing", "needs_manual"]);

export interface ServiceLineRowProps {
  line: ServiceLineProfile;
  sheetCurrency?: string;
  disabled?: boolean;
  onDelete: (lineId: string) => void;
  /** Additive AI-drafter affordance (15.7 §2) — omit to keep the row exactly as before. */
  onSwap?: (input: Omit<ServiceLineWriteInput, "base_costing_revision">) => Promise<unknown>;
}

export function ServiceLineRow({ line, sheetCurrency = "USD", disabled, onDelete, onSwap }: ServiceLineRowProps) {
  const [isSwapOpen, setIsSwapOpen] = useState(false);
  const isCatalogLine = Boolean(line.product_id);
  const hasFx = line.cost_currency !== sheetCurrency;
  const isAiDraft = line.source === "ai_draft";
  const aiFlags = line.ai_meta_json?.flags ?? [];
  const needsManualReview = aiFlags.some((flag) => NEEDS_MANUAL_REVIEW_FLAGS.has(flag));

  return (
    <tr className="border-b border-[var(--color-border)] last:border-b-0">
      <td className="px-3 py-2">
        <div className="flex flex-col gap-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>{line.title}</span>
            {isAiDraft ? (
              <span
                title={line.ai_meta_json?.reason || "Drafted by AI Service Drafter"}
                className={cn(
                  getTypographyClassName("caption"),
                  "inline-flex items-center gap-1 rounded-full border border-violet-300 bg-violet-50 px-2 py-0.5 text-violet-700",
                )}
              >
                <Sparkles size={10} aria-hidden="true" />
                AI
              </span>
            ) : null}
            {needsManualReview ? (
              <span
                title={`Needs manual review (${aiFlags.filter((flag) => NEEDS_MANUAL_REVIEW_FLAGS.has(flag)).join(", ")})`}
                className={cn(
                  getTypographyClassName("caption"),
                  "inline-flex items-center gap-1 rounded-full border border-rose-300 bg-rose-50 px-2 py-0.5 text-rose-700",
                )}
              >
                Needs review
              </span>
            ) : null}
          </div>
          <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
            {[line.category, line.subcategory].filter(Boolean).join(" · ")}
            {isCatalogLine ? " · catalog" : " · manual"}
            {hasFx ? ` · fx from ${formatMinor(line.unit_cost_minor, line.cost_currency)}` : ""}
          </span>
        </div>
      </td>
      <td className={cn(getTypographyClassName("caption"), "px-3 py-2 text-[var(--color-muted)]")}>
        {line.qty_unit} {line.unit} × {line.qty_time} {line.time_basis}
      </td>
      <td className={cn(getTypographyClassName("bodySm"), "px-3 py-2 text-right text-[var(--color-on-surface)]")}>
        {formatMinor(line.cost_minor, sheetCurrency)}
      </td>
      <td className={cn(getTypographyClassName("bodySm"), "px-3 py-2 text-right text-[var(--color-accent)]")}>
        {formatMinor(line.sell_minor, sheetCurrency)}
      </td>
      <td className="px-3 py-2 text-right">
        <div className="flex items-center justify-end gap-1">
          {isAiDraft && onSwap ? (
            <button
              type="button"
              disabled={disabled}
              onClick={() => setIsSwapOpen(true)}
              className="rounded-full p-1.5 text-[var(--color-muted)] transition-colors hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-accent)] disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer"
              aria-label={`Swap line ${line.title}`}
              title="Swap for a different product"
            >
              <Repeat size={14} aria-hidden="true" />
            </button>
          ) : null}
          <button
            type="button"
            disabled={disabled}
            onClick={() => onDelete(line.id)}
            className="rounded-full p-1.5 text-[var(--color-muted)] transition-colors hover:bg-[var(--color-surface-muted)] hover:text-rose-600 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer"
            aria-label={`Delete line ${line.title}`}
          >
            <Trash2 size={14} aria-hidden="true" />
          </button>
        </div>
      </td>

      {isSwapOpen && onSwap && typeof document !== "undefined"
        ? createPortal(
            <SwapLineDialog line={line} sheetCurrency={sheetCurrency} onClose={() => setIsSwapOpen(false)} onSwap={onSwap} />,
            document.body,
          )
        : null}
    </tr>
  );
}

export default ServiceLineRow;
