"use client";

import { AlertTriangle, ChevronRight, Copy } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import type { BookingBoardItem, BookingLineStatus, BookingLineUrgency } from "./types.ts";
import { formatOperationDate, getNextStatus, getStatusLabel, getUrgencyLabel } from "./operationsView.ts";

const URGENCY_CHIP_CLASS: Record<BookingLineUrgency | "none", string> = {
  overdue: "border-rose-200 bg-rose-50 text-rose-700",
  due_soon: "border-amber-200 bg-amber-50 text-amber-700",
  ok: "border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-muted)]",
  none: "border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-muted)]",
};

export type OperationsLineActionHandlers = {
  onAdvance: (item: BookingBoardItem, to: "requested" | "confirmed" | "delivered") => void;
  onCancelLine: (item: BookingBoardItem) => void;
  onCancelBooking: (item: BookingBoardItem) => void;
};

export function OperationsStatusBadge({ status }: { status: BookingLineStatus }) {
  return (
    <span className={cn(getTypographyClassName("caption"), "inline-flex rounded-full border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-2.5 py-0.5 text-[var(--color-muted)]")}>
      {getStatusLabel(status)}
    </span>
  );
}

export function OperationsUrgencyBadge({ urgency }: { urgency: BookingLineUrgency | null }) {
  const resolvedUrgency = urgency ?? "none";
  return (
    <span className={cn(getTypographyClassName("caption"), "inline-flex rounded-full border px-2.5 py-0.5", URGENCY_CHIP_CLASS[resolvedUrgency])}>
      {getUrgencyLabel(urgency)}
    </span>
  );
}

export function OperationsLineActions({ item, onAdvance, onCancelLine, onCancelBooking }: { item: BookingBoardItem } & OperationsLineActionHandlers) {
  const nextStatus = getNextStatus(item.line.status);
  const isTerminal = nextStatus === null;

  return (
    <div className="flex flex-wrap items-center gap-2">
      {!isTerminal && nextStatus ? (
        <button
          type="button"
          onClick={() => onAdvance(item, nextStatus)}
          className={cn(getTypographyClassName("buttonSecondary"), "inline-flex items-center gap-1 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-accent-wash)] px-3 py-2 text-[var(--color-accent)] transition-colors hover:bg-[var(--color-surface-hover)]")}
        >
          Mark {getStatusLabel(nextStatus)}
          <ChevronRight size={14} aria-hidden="true" />
        </button>
      ) : null}
      {!isTerminal ? (
        <button
          type="button"
          onClick={() => onCancelLine(item)}
          className={cn(getTypographyClassName("buttonSecondary"), "rounded-[var(--radius-button)] border border-[var(--color-border)] px-3 py-2 text-[var(--color-muted)] transition-colors hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700")}
        >
          Cancel line
        </button>
      ) : null}
      <button
        type="button"
        onClick={() => onCancelBooking(item)}
        className={cn(getTypographyClassName("buttonSecondary"), "rounded-[var(--radius-button)] px-2 py-2 text-[var(--color-muted)] transition-colors hover:text-rose-700")}
      >
        Cancel booking
      </button>
    </div>
  );
}

export function OperationsLineCard({ item, onAdvance, onCancelLine, onCancelBooking }: { item: BookingBoardItem } & OperationsLineActionHandlers) {
  const { line } = item;

  return (
    <article className="flex h-full flex-col gap-4 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-[var(--elevation-card)]">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <a href={`/workspace/quotations/${encodeURIComponent(item.quotation_id)}`} className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)] hover:text-[var(--color-accent)]")}>
            {item.booking_code}
          </a>
          <p className={cn(getTypographyClassName("caption"), "mt-1 text-[var(--color-muted)]")}>{item.party_label_snapshot ?? "Party TBD"}</p>
        </div>
        <div className="flex flex-wrap justify-end gap-1.5">
          <OperationsStatusBadge status={line.status} />
          <OperationsUrgencyBadge urgency={line.urgency} />
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <p className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-on-surface)]")}>{line.title_snapshot}</p>
        <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>{line.supplier_name_snapshot ?? "No supplier on file"}</p>
        <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
          Service {formatOperationDate(line.service_date)} · Request by {formatOperationDate(line.request_by_date)}
        </p>
      </div>

      {line.voucher_ref ? (
        <button type="button" onClick={() => navigator.clipboard?.writeText(line.voucher_ref ?? "")} className={cn(getTypographyClassName("caption"), "inline-flex w-fit items-center gap-1 text-[var(--color-accent)] hover:underline")}>
          <Copy size={12} aria-hidden="true" />
          Voucher {line.voucher_ref}
        </button>
      ) : null}

      {item.cash_flow_warning ? (
        <p className={cn(getTypographyClassName("caption"), "flex items-start gap-2 rounded-[var(--radius-card)] border border-amber-200 bg-amber-50 px-3 py-2 text-amber-700")}>
          <AlertTriangle size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
          Supplier payment is due before the customer balance.
        </p>
      ) : null}

      <div className="mt-auto border-t border-[var(--color-border)] pt-3">
        <OperationsLineActions item={item} onAdvance={onAdvance} onCancelLine={onCancelLine} onCancelBooking={onCancelBooking} />
      </div>
    </article>
  );
}
