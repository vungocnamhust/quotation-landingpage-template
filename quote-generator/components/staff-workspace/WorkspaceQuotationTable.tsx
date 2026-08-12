"use client";

import React from "react";
import Link from "next/link";
import { User, MapPin, Calendar, Clock, ChevronRight, CheckCircle2, Globe } from "lucide-react";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";
import { QuotationItem, formatNationality, formatTravelDates, formatDuration } from "./WorkspaceQuotationCard";

function StatusBadge({ status }: { status: string }) {
  const isPublished = status === "published";

  return (
    <span
      className={cn(
        getTypographyClassName("caption"),
        "workspace-status-badge inline-flex items-center gap-1",
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

export const WorkspaceQuotationTable = React.memo(function WorkspaceQuotationTable({
  items,
}: {
  items: QuotationItem[];
}) {
  return (
    <div className="overflow-x-auto rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] shadow-[var(--elevation-card)]">
      <table className="w-full text-left border-collapse min-w-[800px]">
        <thead>
          <tr className="border-b border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-muted)]">
            <th className={cn(getTypographyClassName("label"), "px-4 py-3")}>ID & Status</th>
            <th className={cn(getTypographyClassName("label"), "px-4 py-3")}>Client & Nationality</th>
            <th className={cn(getTypographyClassName("label"), "px-4 py-3")}>Journey & Route</th>
            <th className={cn(getTypographyClassName("label"), "px-4 py-3")}>Dates & Duration</th>
            <th className={cn(getTypographyClassName("label"), "px-4 py-3")}>Updated</th>
            <th className={cn(getTypographyClassName("label"), "px-4 py-3 text-right")}>Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--color-border)]">
          {items.map((item) => {
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

            return (
              <tr
                key={item.id}
                className="group transition-colors hover:bg-[var(--color-surface-hover)]"
              >
                {/* ID & Status */}
                <td className="px-4 py-3.5 align-middle">
                  <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-1.5">
                      <span
                        className={cn(
                          getTypographyClassName("caption"),
                          "font-mono rounded bg-[var(--color-surface-muted)] px-1.5 py-0.5 text-[var(--color-muted)]"
                        )}
                      >
                        #{item.id}
                      </span>
                      <StatusBadge status={item.status} />
                    </div>
                    <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
                      {item.brandId} · {item.locale.toUpperCase()}
                    </span>
                  </div>
                </td>

                {/* Client & Nationality */}
                <td className="px-4 py-3.5 align-middle">
                  <div className="flex flex-col gap-1">
                    <p
                      className={cn(
                        getTypographyClassName("bodySm"),
                        "flex items-center gap-1.5 text-[var(--color-on-surface)]"
                      )}
                    >
                      <User size={13} className="shrink-0 text-[var(--color-accent)]" aria-hidden="true" />
                      <span>{item.customerName || "Unnamed client"}</span>
                    </p>
                    {nationalityText != null ? (
                      <p
                        className={cn(
                          getTypographyClassName("caption"),
                          "inline-flex items-center gap-1 text-[var(--color-muted)]"
                        )}
                      >
                        <Globe size={11} className="text-[var(--color-accent)] shrink-0" aria-hidden="true" />
                        <span>{nationalityText}</span>
                      </p>
                    ) : null}
                  </div>
                </td>

                {/* Journey Title & Route */}
                <td className="px-4 py-3.5 align-middle max-w-xs">
                  <div className="flex flex-col gap-1">
                    <Link
                      href={`/workspace/quotations/${encodeURIComponent(item.id)}`}
                      className={cn(
                        getTypographyClassName("cardTitle"),
                        "truncate text-[var(--color-on-surface)] group-hover:text-[var(--color-accent)] transition-colors"
                      )}
                    >
                      {item.title || "Untitled journey"}
                    </Link>
                    {destinationsText != null ? (
                      <p
                        className={cn(
                          getTypographyClassName("caption"),
                          "flex items-center gap-1 text-[var(--color-muted)] truncate"
                        )}
                        title={destinationsText}
                      >
                        <MapPin size={12} className="shrink-0 text-[var(--color-accent)]" aria-hidden="true" />
                        <span className="truncate">{destinationsText}</span>
                      </p>
                    ) : null}
                  </div>
                </td>

                {/* Dates & Duration */}
                <td className="px-4 py-3.5 align-middle">
                  <div className="flex flex-col gap-1">
                    <p
                      className={cn(
                        getTypographyClassName("caption"),
                        "flex items-center gap-1.5 text-[var(--color-on-surface)]"
                      )}
                    >
                      <Calendar size={13} className="shrink-0 text-[var(--color-accent)]" aria-hidden="true" />
                      <span>{datesText != null ? datesText : "Dates TBD"}</span>
                    </p>
                    {durationText != null ? (
                      <span
                        className={cn(
                          getTypographyClassName("caption"),
                          "inline-self-start rounded bg-[var(--color-accent-wash)] px-1.5 py-0.5 text-[var(--color-accent)]"
                        )}
                      >
                        {durationText}
                      </span>
                    ) : null}
                  </div>
                </td>

                {/* Updated */}
                <td className="px-4 py-3.5 align-middle">
                  <span
                    className={cn(
                      getTypographyClassName("caption"),
                      "flex items-center gap-1 text-[var(--color-muted)]"
                    )}
                  >
                    <Clock size={12} aria-hidden="true" />
                    <span>{formatDateTime(item.updatedAt)}</span>
                  </span>
                </td>

                {/* Action */}
                <td className="px-4 py-3.5 align-middle text-right">
                  <Link
                    href={`/workspace/quotations/${encodeURIComponent(item.id)}`}
                    className={cn(
                      getTypographyClassName("buttonSecondary"),
                      "inline-flex items-center gap-1 text-[var(--color-accent)] hover:underline"
                    )}
                  >
                    <span>Open</span>
                    <ChevronRight size={14} aria-hidden="true" />
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
});
