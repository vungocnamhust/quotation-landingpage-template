"use client";

import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import type { IngestionBatchStatus, IngestionBatchSummary } from "./types.ts";

const STATUS_STYLE: Record<IngestionBatchStatus, string> = {
  draft: "bg-slate-500/10 border-slate-500/30 text-slate-600 dark:text-slate-300",
  needs_clarification: "bg-amber-500/10 border-amber-500/30 text-amber-600 dark:text-amber-400",
  ready: "bg-sky-500/10 border-sky-500/30 text-sky-600 dark:text-sky-400",
  committed: "bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400",
  rejected: "bg-rose-500/10 border-rose-500/30 text-rose-600 dark:text-rose-400",
  archived: "bg-slate-500/10 border-slate-500/30 text-slate-500 dark:text-slate-400",
};

const STATUS_LABEL: Record<IngestionBatchStatus, string> = {
  draft: "Draft",
  needs_clarification: "Needs clarification",
  ready: "Ready to commit",
  committed: "Committed",
  rejected: "Rejected",
  archived: "Archived",
};

export function BatchStatusBadge({ status }: { status: IngestionBatchStatus }) {
  return (
    <span
      className={cn(
        getTypographyClassName("label"),
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1",
        STATUS_STYLE[status],
      )}
    >
      {STATUS_LABEL[status]}
    </span>
  );
}

interface Props {
  batches: IngestionBatchSummary[];
  selectedId: string | null;
  isLoading: boolean;
  errorMessage?: string | null;
  onSelect: (id: string) => void;
}

export function BatchList({ batches, selectedId, isLoading, errorMessage, onSelect }: Props) {
  return (
    <section className="flex flex-col gap-3 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-5 shadow-xs">
      <h2 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>Batches</h2>

      {errorMessage ? (
        <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-danger)]")}>{errorMessage}</p>
      ) : null}

      {isLoading ? (
        <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>Loading…</p>
      ) : batches.length === 0 ? (
        <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>
          No batches yet — paste a tariff to get started.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {batches.map((batch) => (
            <li key={batch.id}>
              <button
                type="button"
                onClick={() => onSelect(batch.id)}
                className={cn(
                  "flex w-full flex-col gap-1.5 rounded-[var(--radius-input)] border px-3 py-2.5 text-left transition-colors",
                  batch.id === selectedId
                    ? "border-[var(--color-accent)] bg-[var(--color-accent-wash)]"
                    : "border-[var(--color-border-strong)] hover:bg-[var(--color-surface-hover)]",
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <BatchStatusBadge status={batch.status} />
                  {batch.unresolved_count > 0 ? (
                    <span className={cn(getTypographyClassName("caption"), "text-[var(--color-danger)]")}>
                      {batch.unresolved_count} unresolved
                    </span>
                  ) : null}
                </div>
                <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>
                  {batch.products_count} product(s), {batch.rate_groups_count} rate group(s)
                </p>
                <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
                  {batch.source_channel} · {new Date(batch.created_at).toLocaleString()}
                </p>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
