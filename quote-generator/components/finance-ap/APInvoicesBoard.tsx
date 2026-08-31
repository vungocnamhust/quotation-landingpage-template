"use client";

import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import { formatMinorAmount } from "../../lib/moneyFormat.ts";
import type { ApSupplierInvoiceListItem } from "./types.ts";

export type BoardTab = "due_soon" | "overdue" | "disputed" | "unmatched" | "approved" | "all";

const TABS: Array<{ key: BoardTab; label: string }> = [
  { key: "due_soon", label: "Due soon" },
  { key: "overdue", label: "Overdue" },
  { key: "disputed", label: "Disputed" },
  { key: "unmatched", label: "Unmatched" },
  { key: "approved", label: "Approved" },
  { key: "all", label: "All" },
];

const STATUS_BADGE: Record<string, string> = {
  draft: "bg-neutral-100 text-neutral-700 border-neutral-200",
  received: "bg-sky-50 text-sky-700 border-sky-200",
  matched: "bg-emerald-50 text-emerald-700 border-emerald-200",
  disputed: "bg-rose-50 text-rose-700 border-rose-200",
  approved: "bg-amber-50 text-amber-800 border-amber-300",
  paid: "bg-emerald-600 text-white border-emerald-700",
  void: "bg-neutral-200 text-neutral-500 border-neutral-300",
};

function dueChipClass(dueDate: string | null, status: string): string {
  if (!dueDate || status === "paid" || status === "void") return "text-[var(--color-muted)]";
  const days = Math.ceil((new Date(`${dueDate}T00:00:00`).getTime() - Date.now()) / 86_400_000);
  if (days < 0) return "text-rose-700";
  if (days <= 7) return "text-amber-700";
  return "text-[var(--color-muted)]";
}

type Props = {
  items: ApSupplierInvoiceListItem[];
  isLoading: boolean;
  tab: BoardTab;
  onTabChange: (tab: BoardTab) => void;
  search: string;
  onSearchChange: (value: string) => void;
  selectedInvoiceId: string | null;
  onSelect: (invoiceId: string) => void;
  onCreate: () => void;
};

export function APInvoicesBoard({ items, isLoading, tab, onTabChange, search, onSearchChange, selectedInvoiceId, onSelect, onCreate }: Props) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-1">
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => onTabChange(t.key)}
              className={cn(
                getTypographyClassName("caption"),
                "rounded-full border px-3 py-1.5 transition-colors",
                tab === t.key
                  ? "border-[var(--color-accent)] bg-[var(--color-accent)] text-[var(--color-on-accent)]"
                  : "border-[var(--color-border)] text-[var(--color-muted)] hover:bg-[var(--color-surface-muted)]",
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={onCreate}
          className={cn(getTypographyClassName("buttonPrimary"), "rounded-[var(--radius-button)] bg-[var(--color-accent)] px-3 py-1.5 text-[var(--color-on-accent)]")}
        >
          New invoice
        </button>
      </div>

      <input
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        placeholder="Search supplier or invoice number…"
        className={cn(
          getTypographyClassName("bodySm"),
          "min-h-10 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)]",
        )}
      />

      <div className="flex flex-col gap-1">
        {isLoading ? <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>Loading…</p> : null}
        {!isLoading && items.length === 0 ? (
          <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>No invoices in this view.</p>
        ) : null}
        {items.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => onSelect(item.id)}
            className={cn(
              "flex items-center justify-between gap-3 rounded-[var(--radius-card)] border px-3 py-2 text-left transition-colors",
              item.id === selectedInvoiceId
                ? "border-[var(--color-accent)] bg-[var(--color-surface-muted)]"
                : "border-[var(--color-border)] bg-[var(--color-surface)] hover:bg-[var(--color-surface-muted)]",
            )}
          >
            <div>
              <p className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-on-surface)]")}>
                {item.invoice_number ?? "(no number)"}
              </p>
              <p className={cn(getTypographyClassName("caption"), dueChipClass(item.due_date, item.status))}>
                Due {item.due_date ?? "—"} · {item.matched_line_count}/{item.total_line_count} matched
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>
                {formatMinorAmount(item.gross_total_minor, item.currency)}
              </span>
              <span className={cn(getTypographyClassName("caption"), "rounded-full border px-2 py-0.5", STATUS_BADGE[item.status])}>
                {item.status}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
