"use client";

import { AlertTriangle, Ban } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import { BookingLineRow } from "./BookingLineRow.tsx";
import type { BookingLineProfile } from "./types.ts";

function formatDate(value: string | null): string {
  if (!value) return "—";
  const d = new Date(`${value}T00:00:00`);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

export function BookingCard({
  bookingId,
  bookingCode,
  quotationId,
  partyLabel,
  travelStartDate,
  travelEndDate,
  lines,
  hasCashFlowWarning,
  onAdvance,
  onCancelLine,
  onCancelBooking,
}: {
  bookingId: string;
  bookingCode: string;
  quotationId: string;
  partyLabel: string | null;
  travelStartDate: string | null;
  travelEndDate: string | null;
  lines: BookingLineProfile[];
  hasCashFlowWarning: boolean;
  onAdvance: (line: BookingLineProfile, to: "requested" | "confirmed" | "delivered") => void;
  onCancelLine: (line: BookingLineProfile) => void;
  onCancelBooking: () => void;
}) {
  return (
    <div id={bookingId} className="flex flex-col gap-3 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4 shadow-[var(--elevation-card)]">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <a
            href={`/workspace/quotations/${encodeURIComponent(quotationId)}`}
            className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)] hover:text-[var(--color-accent)]")}
          >
            {bookingCode}
          </a>
          <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
            {partyLabel ?? "Party TBD"} · {formatDate(travelStartDate)} – {formatDate(travelEndDate)}
          </p>
        </div>
        <button
          type="button"
          onClick={onCancelBooking}
          className={cn(
            getTypographyClassName("caption"),
            "flex items-center gap-1 rounded-full border border-[var(--color-border)] px-2.5 py-1 text-[var(--color-muted)] transition-colors hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700",
          )}
        >
          <Ban size={12} aria-hidden="true" />
          Cancel booking
        </button>
      </div>

      {hasCashFlowWarning ? (
        <div
          className={cn(
            getTypographyClassName("caption"),
            "flex items-center gap-2 rounded-[var(--radius-card)] border border-amber-200 bg-amber-50 px-3 py-2 text-amber-700",
          )}
        >
          <AlertTriangle size={14} className="shrink-0" aria-hidden="true" />
          <span>Supplier payment falls due before the customer&apos;s balance is expected.</span>
        </div>
      ) : null}

      <div className="flex flex-col gap-2">
        {lines.map((line) => (
          <BookingLineRow key={line.id} line={line} onAdvance={onAdvance} onCancel={onCancelLine} />
        ))}
      </div>
    </div>
  );
}
