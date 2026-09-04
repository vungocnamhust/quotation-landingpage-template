"use client";

import { useToast } from "../staff-workspace/ToastProvider.tsx";
import { Loader2, PlusCircle } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import { useCostingWorkspace } from "./useCostingWorkspace.ts";
import { CostingSettingsBar } from "./CostingSettingsBar.tsx";
import { ServiceLinesTable } from "./ServiceLinesTable.tsx";
import { AddServiceLineFlow } from "./AddServiceLineFlow.tsx";
import { deriveDaySpecsFromLines } from "./ai/deriveDaySpecs.ts";
import type { ApplyPricingResponse, CostingWorkbenchAnchor, DraftDaySpec } from "./types.ts";
import type { ExistingPricingOption } from "./ApplyPricingDialog.tsx";

function useSafeToast() {
  try {
    return useToast();
  } catch {
    return null;
  }
}

// Mirrors schemas/service_draft.py DraftFlag — see ServiceLineRow.tsx for the row-level check.
const NEEDS_MANUAL_REVIEW_FLAGS = new Set(["rate_missing", "rate_conflict", "needs_manual"]);

export interface CostingWorkbenchProps {
  anchor: CostingWorkbenchAnchor;
  /** Rendered above the workbench once a sheet exists — e.g. a "Create quotation from this sheet" CTA. */
  headerAction?: (sheetId: string) => React.ReactNode;
  baseRevision?: number;
  existingOptions?: ExistingPricingOption[];
  adultsCount?: number;
  childrenCount?: number;
  onApplyPricingSuccess?: (response: ApplyPricingResponse) => void;
  /** Fired on a 409 from apply-pricing, alongside the existing costing-only
   * reload — lets the host also refresh the facts/document resource that owns
   * `baseRevision`, so a retry doesn't repeat the same conflict (16.3 P0 fix). */
  onApplyPricingConflict?: () => void;
  /** Day -> destination/date anchors for the AI Service Drafter (15.7 §1.6) — pass this
   * from a host that already has the itinerary loaded (e.g. `factsData.facts.itinerary_days`)
   * so Draft can run on days that have no service lines yet. When omitted, the workbench
   * falls back to deriving anchors from the sheet's existing lines (`deriveDaySpecsFromLines`),
   * which only covers days the sheet already has catalog-sourced lines on. */
  aiDrafterDays?: DraftDaySpec[];
  className?: string;
}

/**
 * `CostingWorkbench` is the single shell for both Flow 1 (anchored to a
 * `quote_request`, opened from the request detail screen) and Flow 2
 * (anchored to a `quotation`, opened lazily from the workspace's Costing
 * stage). It resolves-or-creates the sheet for `anchor` and renders the same
 * grid + settings + add-line UI either way (15.4 §2.2).
 */
export function CostingWorkbench({
  anchor,
  headerAction,
  baseRevision,
  existingOptions,
  adultsCount,
  childrenCount,
  onApplyPricingSuccess,
  onApplyPricingConflict,
  aiDrafterDays,
  className,
}: CostingWorkbenchProps) {
  const toastCtx = useSafeToast();
  const {
    sheetId,
    workbench,
    isLoading,
    isCreatingSheet,
    isApplyingPricing,
    actionError,
    rateCandidates,
    createSheet,
    updateSettings,
    addLine,
    removeLine,
    applyPricing,
    refresh,
  } = useCostingWorkspace(anchor, {
    notifyToast: (message, type) => {
      toastCtx?.toast(message, type);
    },
  });

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

        {actionError ? (
          <div
            role="alert"
            className={cn(
              getTypographyClassName("bodySm"),
              "flex flex-col items-center gap-2 max-w-md w-full rounded-[var(--radius-button)] border border-rose-300 bg-rose-50 p-3 text-rose-700 text-center",
            )}
          >
            <p>{actionError}</p>
            {rateCandidates?.length ? (
              <ul className="mt-2 list-disc pl-5 text-left">
                {rateCandidates.map((candidate) => (
                  <li key={candidate.rate_id}>
                    {candidate.season || candidate.rate_id} · {candidate.validity?.valid_from}–{candidate.validity?.valid_to}
                  </li>
                ))}
              </ul>
            ) : null}
            <button
              type="button"
              disabled={isCreatingSheet}
              onClick={() => void createSheet()}
              className={cn(
                getTypographyClassName("caption"),
                "underline hover:no-underline text-rose-800 disabled:opacity-50 cursor-pointer",
              )}
            >
              Retry
            </button>
          </div>
        ) : null}

        <button
          type="button"
          disabled={isCreatingSheet}
          onClick={() => void createSheet()}
          className={cn(
            getTypographyClassName("buttonPrimary"),
            "flex items-center gap-2 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-5 py-2.5 text-white shadow-md transition-opacity hover:opacity-90 disabled:opacity-60 cursor-pointer",
          )}
        >
          {isCreatingSheet ? (
            <>
              <Loader2 size={16} className="animate-spin" aria-hidden="true" />
              <span>Creating costing sheet...</span>
            </>
          ) : (
            <>
              <PlusCircle size={16} aria-hidden="true" />
              <span>Start costing sheet</span>
            </>
          )}
        </button>
      </div>
    );
  }

  const handleApplyPricing = async (targetOptionId: string | null, optionLabel: string) => {
    if (baseRevision == null) {
      // 16.3 F-25: a not-yet-loaded document revision must never silently become 1.
      throw new Error("Bản ghi báo giá chưa tải xong phiên bản hiện tại. Vui lòng đợi rồi thử lại.");
    }
    const res = await applyPricing(
      {
        base_revision: baseRevision,
        target_option_id: targetOptionId,
        option_label: optionLabel,
      },
      undefined,
      onApplyPricingConflict,
    );
    if (!res) {
      // runAction swallowed the failure into the workbench banner; the confirm
      // dialog must not close as if the apply succeeded (16.3 F-24).
      throw new Error("Không thể áp dụng giá dự toán. Vui lòng kiểm tra thông báo lỗi và thử lại.");
    }
    if (onApplyPricingSuccess) {
      onApplyPricingSuccess(res);
    }
  };

  const resolvedAiDays = aiDrafterDays ?? deriveDaySpecsFromLines(workbench.items);
  const manualReviewCount = workbench.items.filter((line) =>
    (line.ai_meta_json?.flags ?? []).some((flag) => NEEDS_MANUAL_REVIEW_FLAGS.has(flag)),
  ).length;

  const handleAiDraftComplete = () => {
    // The Draft response's created lines already live server-side (written through
    // costing_service like any other line) — reload the authoritative workbench state
    // instead of hand-merging the response into the SWR cache (16.3-style discipline:
    // never recompute/derive what the server already returns fresh).
    void refresh();
  };

  return (
    <div className={cn("flex flex-col gap-4", className)}>
      {headerAction ? <div className="flex justify-end">{headerAction(sheetId)}</div> : null}

      {actionError ? (
        <div className={cn(getTypographyClassName("bodySm"), "rounded-[var(--radius-button)] border border-rose-300 bg-rose-50 px-3 py-2 text-rose-700")}>
          <p>{actionError}</p>
          {rateCandidates?.length ? (
            <ul className="mt-2 list-disc pl-5">
              {rateCandidates.map((candidate) => (
                <li key={candidate.rate_id}>
                  {candidate.season || candidate.rate_id} · {candidate.validity?.valid_from}–{candidate.validity?.valid_to}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      <CostingSettingsBar
        sheet={workbench.sheet}
        summary={workbench.summary}
        lineCount={workbench.items.length}
        drift={workbench.drift}
        existingOptions={existingOptions}
        adultsCount={adultsCount}
        childrenCount={childrenCount}
        onUpdate={(input) => void updateSettings(input)}
        onApplyPricing={workbench.sheet.quotation_id ? handleApplyPricing : undefined}
        isApplyingPricing={isApplyingPricing}
        aiDrafterDays={resolvedAiDays}
        manualReviewCount={manualReviewCount}
        onAiDraftComplete={handleAiDraftComplete}
        onAiDraftConflict={() => void refresh()}
      />

      <ServiceLinesTable
        workbench={workbench}
        onDeleteLine={(lineId) => void removeLine(lineId)}
        onSwapLine={(input) => addLine(input)}
      />

      <AddServiceLineFlow sheetCurrency={workbench.sheet.currency} onAdd={(input) => addLine(input)} />
    </div>
  );
}

export default CostingWorkbench;
