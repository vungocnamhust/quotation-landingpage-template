"use client";

import { User, Briefcase, Calendar, MapPin, Users, ArrowRight } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import type { QuoteRequestItem } from "../quotation-workspace/factsTypes.ts";
import { WorkspaceNavigationLink } from "./WorkspaceNavigation.tsx";

type Props = {
  item: QuoteRequestItem;
};

export function WorkspaceRequestCard({ item }: Props) {
  const isTraveller = item.role === "traveller";
  const title = item.customer_name || (isTraveller ? "Anonymous Traveller" : "Anonymous Advisor");
  const destinationsText = item.destinations?.length > 0 ? item.destinations.join(" & ") : "Not specified";
  const datesText = item.raw_dates_text || (item.start_date ? `${item.start_date} ${item.end_date ? `- ${item.end_date}` : ""}` : "Dates flexible");

  const statusLabel =
    item.status === "quotation_created"
      ? "Quotation Created"
      : item.status === "under_review"
      ? "Under Review"
      : item.status === "archived"
      ? "Archived"
      : "New Request";


  const statusClass =
    item.status === "quotation_created"
      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
      : item.status === "under_review"
      ? "bg-amber-50 text-amber-700 border-amber-200"
      : item.status === "archived"
      ? "bg-gray-50 text-gray-600 border-gray-200"
      : "bg-blue-50 text-blue-700 border-blue-200";

  return (
    <div className="flex flex-col justify-between gap-4 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] transition-all hover:border-[var(--color-border-strong)]">
      {/* Top Meta Bar */}
      <div className="flex items-center justify-between gap-2">
        <span
          className={cn(
            getTypographyClassName("caption"),
            "flex items-center gap-1.5 rounded-full px-2.5 py-1 border",
            isTraveller
              ? "bg-sky-50 text-sky-700 border-sky-200"
              : "bg-purple-50 text-purple-700 border-purple-200"
          )}
        >
          {isTraveller ? <User size={13} aria-hidden="true" /> : <Briefcase size={13} aria-hidden="true" />}
          <span>{isTraveller ? "TRAVELLER" : "TRAVEL ADVISOR"}</span>
        </span>

        <span className={cn(getTypographyClassName("caption"), "rounded-full px-2.5 py-1 border", statusClass)}>
          {statusLabel}
        </span>
      </div>

      {/* Main Info Block */}
      <div className="flex flex-col gap-2">
        <WorkspaceNavigationLink
          href={`/workspace/requests/${item.id}`}
          className={cn(
            getTypographyClassName("cardTitle"),
            "text-[var(--color-on-surface)] hover:text-[var(--color-accent)] transition-colors line-clamp-1"
          )}
        >
          {title}
        </WorkspaceNavigationLink>

        {item.company_name ? (
          <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
            {item.company_name} {item.market ? `• ${item.market}` : ""}
          </p>
        ) : null}

        <div className={cn(getTypographyClassName("caption"), "mt-2 flex flex-col gap-1.5 text-[var(--color-muted)]")}>
          <div className="flex items-center gap-2 truncate">
            <MapPin size={14} className="shrink-0 text-[var(--color-muted)]" aria-hidden="true" />
            <span className="truncate">{destinationsText}</span>
          </div>

          <div className="flex items-center gap-2 truncate">
            <Calendar size={14} className="shrink-0 text-[var(--color-muted)]" aria-hidden="true" />
            <span className="truncate">{datesText}</span>
          </div>

          <div className="flex items-center gap-2 truncate">
            <Users size={14} className="shrink-0 text-[var(--color-muted)]" aria-hidden="true" />
            <span className="truncate">
              {item.adults || 2} Adults {item.children ? `, ${item.children_details || `${item.children} Children`}` : ""}
            </span>
          </div>
        </div>
      </div>

      {/* Footer Actions */}
      <div className="flex items-center justify-between border-t border-[var(--color-border)] pt-3">
        <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
          ID: {item.id}
        </span>

        <WorkspaceNavigationLink
          href={`/workspace/requests/${item.id}`}
          className={cn(
            getTypographyClassName("caption"),
            "flex items-center gap-1 text-[var(--color-accent)] hover:underline"
          )}
        >
          <span>View Request</span>
          <ArrowRight size={14} aria-hidden="true" />
        </WorkspaceNavigationLink>
      </div>

    </div>
  );
}
