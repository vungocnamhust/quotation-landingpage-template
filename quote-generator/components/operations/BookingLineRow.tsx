"use client";

import { Phone, MessageCircle, Copy, ChevronRight } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import type { BookingLineProfile, BookingLineUrgency } from "./types.ts";

const URGENCY_CHIP_CLASS: Record<BookingLineUrgency | "none", string> = {
  overdue: "bg-rose-50 text-rose-700 border-rose-200",
  due_soon: "bg-amber-50 text-amber-700 border-amber-200",
  ok: "bg-gray-50 text-gray-600 border-gray-200",
  none: "bg-gray-50 text-gray-500 border-gray-200",
};

const STATUS_LABEL: Record<string, string> = {
  to_request: "To request",
  requested: "Requested",
  confirmed: "Confirmed",
  delivered: "Delivered",
  cancelled: "Cancelled",
};

const NEXT_STATUS: Record<string, "requested" | "confirmed" | "delivered" | null> = {
  to_request: "requested",
  requested: "confirmed",
  confirmed: "delivered",
  delivered: null,
  cancelled: null,
};

function formatDate(value: string | null): string {
  if (!value) return "—";
  const d = new Date(`${value}T00:00:00`);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

function daysUntil(value: string | null): number | null {
  if (!value) return null;
  const target = new Date(`${value}T00:00:00`);
  if (Number.isNaN(target.getTime())) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((target.getTime() - today.getTime()) / 86_400_000);
}

export function BookingLineRow({
  line,
  onAdvance,
  onCancel,
}: {
  line: BookingLineProfile;
  onAdvance: (line: BookingLineProfile, to: "requested" | "confirmed" | "delivered") => void;
  onCancel: (line: BookingLineProfile) => void;
}) {
  const nextStatus = NEXT_STATUS[line.status];
  const isTerminal = line.status === "delivered" || line.status === "cancelled";
  const freeUntilDays = daysUntil(line.penalty_free_until);
  const contact = line.supplier_contact_snapshot_json;

  return (
    <div className="flex flex-col gap-3 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>{line.title_snapshot}</p>
          <span
            className={cn(
              getTypographyClassName("caption"),
              "rounded-full border px-2.5 py-0.5",
              URGENCY_CHIP_CLASS[line.urgency ?? "none"],
            )}
          >
            {line.request_by_date
              ? `Request by ${formatDate(line.request_by_date)}`
              : "No request deadline"}
          </span>
          <span className={cn(getTypographyClassName("caption"), "rounded-full border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-2.5 py-0.5 text-[var(--color-muted)]")}>
            {STATUS_LABEL[line.status] ?? line.status}
          </span>
        </div>

        <p className={cn(getTypographyClassName("bodySm"), "mt-1 text-[var(--color-muted)]")}>
          {line.supplier_name_snapshot ?? "No supplier on file"}
          {contact?.phone ? (
            <a href={`tel:${contact.phone}`} className="ml-2 inline-flex items-center gap-1 text-[var(--color-accent)] hover:underline">
              <Phone size={12} aria-hidden="true" />
              {contact.phone}
            </a>
          ) : null}
          {contact?.zalo ? (
            <a
              href={`https://zalo.me/${contact.zalo}`}
              target="_blank"
              rel="noreferrer"
              className="ml-2 inline-flex items-center gap-1 text-[var(--color-accent)] hover:underline"
            >
              <MessageCircle size={12} aria-hidden="true" />
              Zalo
            </a>
          ) : null}
        </p>

        <div className={cn(getTypographyClassName("caption"), "mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[var(--color-muted)]")}>
          <span>
            {freeUntilDays == null
              ? "No free-cancellation window"
              : freeUntilDays >= 0
                ? `Free to cancel for ${freeUntilDays} more day${freeUntilDays === 1 ? "" : "s"}`
                : "Cancellation penalty applies now"}
          </span>
          <span>Balance due to supplier: {formatDate(line.balance_due_date)}</span>
          {line.voucher_ref ? (
            <button
              type="button"
              onClick={() => navigator.clipboard?.writeText(line.voucher_ref ?? "")}
              className="inline-flex items-center gap-1 text-[var(--color-accent)] hover:underline"
            >
              <Copy size={12} aria-hidden="true" />
              {line.voucher_ref}
            </button>
          ) : null}
        </div>
      </div>

      {!isTerminal ? (
        <div className="flex shrink-0 items-center gap-2">
          {nextStatus ? (
            <button
              type="button"
              onClick={() => onAdvance(line, nextStatus)}
              className={cn(
                getTypographyClassName("buttonSecondary"),
                "inline-flex items-center gap-1 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-accent-wash)] px-3 py-2 text-[var(--color-accent)] transition-colors hover:bg-[var(--color-surface-hover)]",
              )}
            >
              Mark {STATUS_LABEL[nextStatus]}
              <ChevronRight size={14} aria-hidden="true" />
            </button>
          ) : null}
          <button
            type="button"
            onClick={() => onCancel(line)}
            className={cn(
              getTypographyClassName("buttonSecondary"),
              "rounded-[var(--radius-button)] border border-[var(--color-border)] px-3 py-2 text-[var(--color-muted)] transition-colors hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700",
            )}
          >
            Cancel
          </button>
        </div>
      ) : null}
    </div>
  );
}
