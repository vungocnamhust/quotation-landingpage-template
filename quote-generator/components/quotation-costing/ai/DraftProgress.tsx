"use client";

import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";
import type { AiRunStatus, DraftServicesResponse } from "../types.ts";

export interface DraftProgressProps {
  result: DraftServicesResponse;
}

const STATUS_BANNER: Record<AiRunStatus, string> = {
  succeeded: "border-emerald-300 bg-emerald-50 text-emerald-700",
  partial: "border-amber-300 bg-amber-50 text-amber-700",
  failed: "border-rose-300 bg-rose-50 text-rose-700",
};

const STATUS_LABEL: Record<AiRunStatus, string> = {
  succeeded: "Drafter run succeeded",
  partial: "Drafter run partially succeeded",
  failed: "Drafter run failed",
};

/** Per-day tick-through of a Draft response (15.7 §2) — makes succeeded/partial/failed
 * days and the manual-review count visible before the sale returns to the grid. */
export function DraftProgress({ result }: DraftProgressProps) {
  return (
    <div className="flex flex-col gap-3">
      <div className={cn(getTypographyClassName("bodySm"), "rounded-[var(--radius-button)] border px-3 py-2", STATUS_BANNER[result.status])}>
        {STATUS_LABEL[result.status]} — {result.created_line_ids.length} line(s) created
        {result.manual_review_count > 0 ? `, ${result.manual_review_count} need manual review` : ""}.
      </div>

      <div className="flex flex-col gap-2">
        {result.day_outcomes.map((outcome) => {
          const failed = result.days_failed.includes(outcome.day_number);
          const hasFlags = (outcome.draft?.services ?? []).some((service) => service.flags.length > 0);
          return (
            <div
              key={outcome.day_number}
              className="flex items-start gap-2 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2"
            >
              {failed ? (
                <XCircle size={16} className="mt-0.5 shrink-0 text-rose-600" aria-hidden="true" />
              ) : hasFlags ? (
                <AlertTriangle size={16} className="mt-0.5 shrink-0 text-amber-600" aria-hidden="true" />
              ) : (
                <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-emerald-600" aria-hidden="true" />
              )}
              <div className="flex flex-col gap-0.5">
                <span className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>
                  Day {outcome.day_number} — {outcome.lines_created} line(s)
                </span>
                {outcome.error ? <span className={cn(getTypographyClassName("caption"), "text-rose-600")}>{outcome.error}</span> : null}
                {(outcome.draft?.skipped_reasons ?? []).map((reason) => (
                  <span key={`${outcome.day_number}-${reason}`} className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
                    {reason}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default DraftProgress;
