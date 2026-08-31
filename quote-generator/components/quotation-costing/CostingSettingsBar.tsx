"use client";

import { useState } from "react";
import { Lock } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import { SUPPORTED_CURRENCIES } from "../../lib/rules/pricingReconciler.ts";
import { formatMinorAmount as formatMinor } from "../../lib/moneyFormat.ts";
import type { CostingDriftProfile, CostingSheetProfile, CostingSummary, DraftDaySpec, DraftServicesResponse } from "./types.ts";
import { DriftBadge } from "./DriftBadge.tsx";
import { ApplyPricingButton } from "./ApplyPricingButton.tsx";
import type { ExistingPricingOption } from "./ApplyPricingDialog.tsx";
import { AIDraftButton } from "./ai/AIDraftButton.tsx";

export interface CostingSettingsBarProps {
  sheet: CostingSheetProfile;
  summary: CostingSummary;
  lineCount: number;
  disabled?: boolean;
  drift?: CostingDriftProfile | null;
  existingOptions?: ExistingPricingOption[];
  adultsCount?: number;
  childrenCount?: number;
  onUpdate: (input: { currency?: string; markup_rate_bps?: number; rounding_increment_minor?: number }) => void;
  onApplyPricing?: (targetOptionId: string | null, optionLabel: string) => Promise<void>;
  isApplyingPricing?: boolean;
  /** Additive AI Service Drafter affordances (15.7 §2) — all optional so the bar renders
   * exactly as before when a host doesn't wire them up yet. */
  aiDrafterDays?: DraftDaySpec[];
  manualReviewCount?: number;
  onAiDraftComplete?: (result: DraftServicesResponse) => void;
  onAiDraftConflict?: () => void;
}

export function CostingSettingsBar({
  sheet,
  summary,
  lineCount,
  disabled,
  drift,
  existingOptions,
  adultsCount,
  childrenCount,
  onUpdate,
  onApplyPricing,
  isApplyingPricing,
  aiDrafterDays,
  manualReviewCount = 0,
  onAiDraftComplete,
  onAiDraftConflict,
}: CostingSettingsBarProps) {
  const [markupInput, setMarkupInput] = useState(String(sheet.markup_rate_bps));
  const [roundingInput, setRoundingInput] = useState(String(sheet.rounding_increment_minor));
  const currencyLocked = lineCount > 0;

  return (
    <div className="flex flex-col gap-3 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-xs">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border)] pb-3">
        <div className="flex items-center gap-3">
          <span className={cn(getTypographyClassName("label"), "text-[var(--color-on-surface)]")}>
            Thiết lập & Tổng quan dự toán
          </span>
          <DriftBadge drift={drift} />
          {manualReviewCount > 0 ? (
            <span
              title="Service lines whose AI metadata flags rate_missing, rate_conflict, or needs_manual"
              className={cn(
                getTypographyClassName("label"),
                "inline-flex items-center gap-1 rounded-full border border-rose-300 bg-rose-50 px-2.5 py-1 text-rose-700",
              )}
            >
              {manualReviewCount} dòng cần tay
            </span>
          ) : null}
        </div>

        <div className="flex items-center gap-2">
          {aiDrafterDays && onAiDraftComplete ? (
            <AIDraftButton
              sheetId={sheet.id}
              baseCostingRevision={sheet.costing_revision}
              days={aiDrafterDays}
              disabled={disabled}
              onDraftComplete={onAiDraftComplete}
              onConflict={onAiDraftConflict}
            />
          ) : null}

        {onApplyPricing ? (
          <ApplyPricingButton
            sheet={sheet}
            summary={summary}
            existingOptions={existingOptions}
            adultsCount={adultsCount}
            childrenCount={childrenCount}
            drift={drift}
            onApply={onApplyPricing}
            isApplying={isApplyingPricing}
          />
        ) : (
          // 15.5 §2.3 / chốt #9: no route to apply pricing into something that
          // doesn't exist yet — hint at the "Tạo báo giá từ dự toán" CTA above
          // instead of silently rendering nothing here (16.3 P1 fix).
          <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
            Bấm &ldquo;Tạo báo giá từ dự toán&rdquo; ở trên trước khi áp giá vào báo giá.
          </span>
        )}
        </div>
      </div>

      <div className="flex flex-wrap items-end gap-4">
        <div className="flex flex-col gap-1.5">
          <span className={cn(getTypographyClassName("label"), "flex items-center gap-1 text-[var(--color-muted)]")}>
            Currency
            {currencyLocked ? <Lock size={11} aria-hidden="true" /> : null}
          </span>
          <select
            value={sheet.currency}
            disabled={disabled || currencyLocked}
            onChange={(event) => onUpdate({ currency: event.target.value })}
            className={cn(
              getTypographyClassName("bodySm"),
              "h-9 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2.5 text-[var(--color-on-surface)] disabled:cursor-not-allowed disabled:opacity-60",
            )}
            title={currencyLocked ? "Currency is locked once the sheet has service lines" : undefined}
          >
            {SUPPORTED_CURRENCIES.map((currency) => (
              <option key={currency} value={currency}>
                {currency}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1.5">
          <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Markup (bps)</span>
          <input
            type="number"
            min={0}
            value={markupInput}
            disabled={disabled}
            onChange={(event) => setMarkupInput(event.target.value)}
            onBlur={() => {
              const parsed = Number(markupInput);
              if (Number.isFinite(parsed) && parsed >= 0 && parsed !== sheet.markup_rate_bps) {
                onUpdate({ markup_rate_bps: Math.round(parsed) });
              }
            }}
            className={cn(
              getTypographyClassName("bodySm"),
              "h-9 w-28 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2.5 text-[var(--color-on-surface)]",
            )}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Round up to</span>
          <input
            type="number"
            min={0}
            value={roundingInput}
            disabled={disabled}
            onChange={(event) => setRoundingInput(event.target.value)}
            onBlur={() => {
              const parsed = Number(roundingInput);
              if (Number.isFinite(parsed) && parsed >= 0 && parsed !== sheet.rounding_increment_minor) {
                onUpdate({ rounding_increment_minor: Math.round(parsed) });
              }
            }}
            className={cn(
              getTypographyClassName("bodySm"),
              "h-9 w-28 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2.5 text-[var(--color-on-surface)]",
            )}
          />
        </div>

        <div className="ml-auto flex items-center gap-6">
          <div className="flex flex-col items-end gap-0.5">
            <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>Cost</span>
            <span className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-on-surface)]")}>
              {formatMinor(summary.cost_total_minor, sheet.currency)}
            </span>
          </div>
          <div className="flex flex-col items-end gap-0.5">
            <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>Sell</span>
            <span className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-accent)]")}>
              {formatMinor(summary.sell_total_minor, sheet.currency)}
            </span>
          </div>
          <div className="flex flex-col items-end gap-0.5">
            <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>Margin</span>
            <span className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-on-surface)]")}>
              {formatMinor(summary.margin_minor, sheet.currency)} ({(summary.margin_bps / 100).toFixed(1)}%)
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default CostingSettingsBar;
