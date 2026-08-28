"use client";

import React from "react";
import { User, MapPin, Calendar, Clock, ChevronRight, CheckCircle2, Globe, Users } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import { WorkspaceNavigationLink } from "./WorkspaceNavigation.tsx";

export type TripFacts = {
  destinations?: string[];
  startDate?: string | null;
  endDate?: string | null;
  durationDays?: number | null;
  durationNights?: number | null;
  displayTravelDates?: string | null;
  displayRouteText?: string | null;
  durationText?: string | null;
};

export type CustomerFacts = {
  adults?: number | null;
  children?: number | null;
  nationality?: string | null;
};

export type WorkflowSummary = {
  facts: { ready: boolean };
  content: { ready: boolean };
  design: { ready: boolean };
  review: { ready: boolean };
};

export type CommercialSummary = {
  label: string | null;
  currency: string | null;
  groupTotalAmountMinor: number | null;
};

export type QuotationItem = {
  id: string;
  title: string | null;
  customerName: string | null;
  brandId: string;
  status: string;
  locale: string;
  createdAt?: string;
  updatedAt: string;
  tripFacts?: TripFacts;
  customerFacts?: CustomerFacts;
  workflow?: WorkflowSummary;
  commercial?: CommercialSummary;
  workflowLane?: "facts" | "content" | "review" | "published";
};

function StatusBadge({ status }: { status: string }) {
  const isPublished = status === "published";

  return (
    <span
      className={cn(
        getTypographyClassName("caption"),
        "workspace-status-badge",
        isPublished
          ? "workspace-status-badge--published"
          : "workspace-status-badge--draft"
      )}
    >
      {isPublished ? (
        <CheckCircle2 size={12} aria-hidden="true" />
      ) : (
        <Clock size={12} aria-hidden="true" />
      )}
      <span className="capitalize">{status}</span>
    </span>
  );
}

function formatDateTime(isoString: string): string {
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    return d.toLocaleString("en-GB", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  } catch {
    return isoString;
  }
}

export function formatNationality(rawNat?: string | null): string | null {
  if (!rawNat || !rawNat.trim()) return null;
  const cleaned = rawNat.trim();
  if (cleaned.toLowerCase() === "vietnam" || cleaned.toLowerCase() === "vn") return "Vietnam";
  if (cleaned.toLowerCase() === "us" || cleaned.toLowerCase() === "usa" || cleaned.toLowerCase() === "american") return "United States";
  if (cleaned.toLowerCase() === "uk" || cleaned.toLowerCase() === "british") return "United Kingdom";
  if (cleaned.toLowerCase() === "au" || cleaned.toLowerCase() === "australian") return "Australia";
  return cleaned
    .split(/\s+/)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

export function formatTravelDates(
  startDateStr?: string | null,
  endDateStr?: string | null,
  fallbackDisplay?: string | null
): string | null {
  if (fallbackDisplay && fallbackDisplay.trim()) return fallbackDisplay.trim();
  if (!startDateStr) return null;

  try {
    const start = new Date(startDateStr);
    if (isNaN(start.getTime())) return startDateStr;

    const startDay = start.getDate();
    const startMonth = start.toLocaleString("en-GB", { month: "short" });
    const startYear = start.getFullYear();

    if (!endDateStr) {
      return `${startDay} ${startMonth} ${startYear}`;
    }

    const end = new Date(endDateStr);
    if (isNaN(end.getTime())) {
      return `${startDay} ${startMonth} ${startYear} – ${endDateStr}`;
    }

    const endDay = end.getDate();
    const endMonth = end.toLocaleString("en-GB", { month: "short" });
    const endYear = end.getFullYear();

    if (startYear === endYear) {
      if (startMonth === endMonth && startDay === endDay) {
        return `${startDay} ${startMonth} ${startYear}`;
      }
      return `${startDay} ${startMonth} – ${endDay} ${endMonth} ${endYear}`;
    }
    return `${startDay} ${startMonth} ${startYear} – ${endDay} ${endMonth} ${endYear}`;
  } catch {
    return startDateStr;
  }
}

export function formatDuration(
  days?: number | null,
  nights?: number | null,
  startDateStr?: string | null,
  endDateStr?: string | null
): string | null {
  let computedDays = days;
  let computedNights = nights;

  if ((computedDays == null || computedDays <= 0) && startDateStr && endDateStr) {
    try {
      const s = new Date(startDateStr);
      const e = new Date(endDateStr);
      if (!isNaN(s.getTime()) && !isNaN(e.getTime())) {
        const diffTime = Math.abs(e.getTime() - s.getTime());
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        if (diffDays > 0) {
          computedDays = diffDays + 1;
          computedNights = diffDays;
        }
      }
    } catch {
      // Ignore calculation errors
    }
  }

  if (computedDays != null && computedDays > 0) {
    if (computedNights != null && computedNights > 0) {
      return `${computedDays}D${computedNights}N`;
    }
    return `${computedDays} Days`;
  }
  return null;
}

export const WorkspaceQuotationCard = React.memo(function WorkspaceQuotationCard({
  item,
}: {
  item: QuotationItem;
}) {
  const destinationsText =
    item.tripFacts?.displayRouteText ||
    (item.tripFacts?.destinations && item.tripFacts.destinations.length > 0
      ? item.tripFacts.destinations.join(" → ")
      : null);

  const datesText = formatTravelDates(
    item.tripFacts?.startDate,
    item.tripFacts?.endDate,
    item.tripFacts?.displayTravelDates
  );

  const durationText =
    item.tripFacts?.durationText ||
    formatDuration(
      item.tripFacts?.durationDays,
      item.tripFacts?.durationNights,
      item.tripFacts?.startDate,
      item.tripFacts?.endDate
    );

  const nationalityText = formatNationality(item.customerFacts?.nationality);

  const adults = item.customerFacts?.adults;
  const children = item.customerFacts?.children;
  const paxText =
    adults != null && adults > 0
      ? `${adults} Adult${adults > 1 ? "s" : ""}${
          children != null && children > 0 ? `, ${children} Child${children > 1 ? "ren" : ""}` : ""
        }`
      : null;

  return (
    <article className="h-full">
      <WorkspaceNavigationLink
        href={`/workspace/quotations/${encodeURIComponent(item.id)}`}
        className="group flex flex-col justify-between h-full rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] transition-all hover:-translate-y-0.5 hover:border-[var(--color-border-strong)] hover:shadow-md"
      >
        <div>
          {/* Top Row: ID Pill + Brand/Locale + Status Badge */}
          <div className="flex items-center justify-between gap-2 pb-3 border-b border-[var(--color-border)]">
            <div className="flex items-center gap-1.5 min-w-0">
              <span
                className={cn(
                  getTypographyClassName("caption"),
                  "font-mono rounded-md bg-[var(--color-surface-muted)] px-2 py-0.5 text-[var(--color-muted)] truncate"
                )}
                title={`#${item.id}`}
              >
                #{item.id}
              </span>
              <span
                className={cn(
                  getTypographyClassName("caption"),
                  "rounded-md bg-[var(--color-accent-wash)] px-2 py-0.5 text-[var(--color-accent)] shrink-0"
                )}
              >
                {item.brandId} · {item.locale.toUpperCase()}
              </span>
            </div>
            <StatusBadge status={item.status} />
          </div>

          {/* Customer & Nationality Header */}
          <div className="mt-3.5">
            <div className="flex items-center justify-between gap-2">
              <p
                className={cn(
                  getTypographyClassName("caption"),
                  "flex items-center gap-1.5 text-[var(--color-muted)] truncate min-w-0"
                )}
              >
                <User size={13} className="shrink-0 text-[var(--color-accent)]" aria-hidden="true" />
                <span className="truncate text-[var(--color-on-surface)]">
                  {item.customerName || "Unnamed client"}
                </span>
              </p>

              {/* Nationality Badge */}
              {nationalityText != null ? (
                <span
                  className={cn(
                    getTypographyClassName("caption"),
                    "inline-flex items-center gap-1 shrink-0 rounded-md bg-[var(--color-surface-muted)] border border-[var(--color-border)] px-2 py-0.5 text-[var(--color-on-surface)]"
                  )}
                  title={`Nationality: ${nationalityText}`}
                >
                  <Globe size={11} className="text-[var(--color-accent)] shrink-0" aria-hidden="true" />
                  <span>{nationalityText}</span>
                </span>
              ) : null}
            </div>

            {/* Journey Title */}
            <h2
              className={cn(
                getTypographyClassName("cardTitle"),
                "mt-2 line-clamp-2 text-[var(--color-on-surface)] group-hover:text-[var(--color-accent)] transition-colors"
              )}
            >
              {item.title || "Untitled journey"}
            </h2>
          </div>

          {/* Trip Facts Metadata Section */}
          <div
            className={cn(
              getTypographyClassName("caption"),
              "mt-4 flex flex-col gap-2 rounded-lg bg-[var(--color-surface-wash,var(--color-surface-muted))] p-3 border border-[var(--color-border)] text-[var(--color-muted)]"
            )}
          >
            {/* Route */}
            {destinationsText != null ? (
              <div className="flex items-center gap-2">
                <MapPin size={13} className="shrink-0 text-[var(--color-accent)]" aria-hidden="true" />
                <span
                  className="truncate text-[var(--color-on-surface)]"
                  title={destinationsText}
                >
                  {destinationsText}
                </span>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-[var(--color-muted)]">
                <MapPin size={13} className="shrink-0 opacity-50" aria-hidden="true" />
                <span>Route TBD</span>
              </div>
            )}

            {/* Dates & Duration */}
            <div className="flex items-center justify-between gap-2 pt-1 border-t border-[var(--color-border)]/50">
              <div className="flex items-center gap-2 min-w-0">
                <Calendar size={13} className="shrink-0 text-[var(--color-accent)]" aria-hidden="true" />
                <span className="truncate text-[var(--color-on-surface)]">
                  {datesText != null ? datesText : "Dates TBD"}
                </span>
              </div>

              {durationText != null ? (
                <span
                  className={cn(
                    getTypographyClassName("caption"),
                    "shrink-0 rounded-md bg-[var(--color-accent-wash)] px-2 py-0.5 text-[var(--color-accent)]"
                  )}
                >
                  {durationText}
                </span>
              ) : null}
            </div>

            {/* Pax Count */}
            {paxText != null ? (
              <div className="flex items-center gap-2 pt-1 border-t border-[var(--color-border)]/50">
                <Users size={13} className="shrink-0 text-[var(--color-muted)]" aria-hidden="true" />
                <span className="truncate">{paxText}</span>
              </div>
            ) : null}
          </div>
        </div>

        {/* Footer Row: Updated Date + Time and Open CTA */}
        <div className="mt-4 flex items-center justify-between border-t border-[var(--color-border)] pt-3.5">
          <span
            className={cn(
              getTypographyClassName("caption"),
              "flex items-center gap-1.5 text-[var(--color-muted)]"
            )}
          >
            <Clock size={12} aria-hidden="true" />
            <span>Updated {formatDateTime(item.updatedAt)}</span>
          </span>

          <span
            className={cn(
              getTypographyClassName("caption"),
              "flex items-center gap-1 text-[var(--color-accent)] group-hover:translate-x-0.5 transition-transform"
            )}
          >
            <span>Open</span>
            <ChevronRight size={14} aria-hidden="true" />
          </span>
        </div>
      </WorkspaceNavigationLink>
    </article>
  );
});
