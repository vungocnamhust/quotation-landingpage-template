"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState, useTransition } from "react";
import useSWR from "swr";
import { Search, FileText, Calendar, ChevronRight, CheckCircle2, Clock, User, MapPin, Users } from "lucide-react";
import { getTypographyClassName } from "../../config/typography";
import { apiErrorMessage, quotationFetch } from "../../lib/apiError";
import { cn } from "../../utils/cn";

const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? "";

type TripFacts = {
  destinations?: string[];
  startDate?: string | null;
  endDate?: string | null;
  durationDays?: number | null;
  durationNights?: number | null;
  displayTravelDates?: string | null;
  displayRouteText?: string | null;
};

type CustomerFacts = {
  adults?: number | null;
  children?: number | null;
};

type Item = {
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
};

type Response = {
  items: Item[];
  nextCursor: string | null;
  summary: Record<string, number>;
};

const fetcher = (url: string) =>
  quotationFetch<Response>(url, undefined, "Your quotations could not be loaded.");

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
      <span>{status}</span>
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

export default function WorkspaceQuotationList({
  dashboard = false,
}: {
  dashboard?: boolean;
}) {
  const searchParams = useSearchParams();
  const [query, setQuery] = useState(searchParams.get("q") ?? "");
  const [status, setStatus] = useState(searchParams.get("status") ?? "");
  const [cursor, setCursor] = useState<string | null>(null);
  const [, startTransition] = useTransition();

  const params = new URLSearchParams();
  if (query.trim()) params.set("q", query.trim());
  if (status) params.set("status", status);
  if (cursor) params.set("cursor", cursor);
  params.set("limit", dashboard ? "5" : "20");

  const { data, error, isLoading } = useSWR<Response>(
    `${API_BASE}/api/v2/workspace/quotations?${params}`,
    fetcher
  );

  const apply = (next: Partial<{ q: string; status: string }>) =>
    startTransition(() => {
      setCursor(null);
      if (next.q !== undefined) setQuery(next.q);
      if (next.status !== undefined) setStatus(next.status);
    });

  const items = data?.items ?? [];

  return (
    <div className="flex flex-col gap-5">
      {!dashboard ? (
        <div className="flex flex-wrap gap-3 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-[var(--elevation-card)]">
          <div className="relative min-w-0 flex-1">
            <Search
              size={16}
              className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--color-muted)]"
              aria-hidden="true"
            />
            <input
              value={query}
              onChange={(event) => apply({ q: event.target.value })}
              placeholder="Search client or quotation"
              className={cn(
                getTypographyClassName("bodyMd"),
                "min-h-11 w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] pl-10 pr-3 text-[var(--color-on-surface)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)]"
              )}
            />
          </div>
          <select
            value={status}
            onChange={(event) => apply({ status: event.target.value })}
            className={cn(
              getTypographyClassName("bodySm"),
              "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)]"
            )}
          >
            <option value="">All statuses</option>
            <option value="draft">Draft</option>
            <option value="published">Published</option>
          </select>
        </div>
      ) : null}

      {error ? (
        <p
          className={cn(
            getTypographyClassName("bodyMd"),
            "rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-5 text-[var(--color-on-surface)] shadow-[var(--elevation-card)]"
          )}
        >
          {apiErrorMessage(error)}
        </p>
      ) : null}

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((idx) => (
            <div
              key={idx}
              className="h-56 animate-pulse rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5"
            />
          ))}
        </div>
      ) : null}

      {!isLoading && !error && !items.length ? (
        <div className="flex flex-col items-center justify-center rounded-[var(--radius-card)] border border-dashed border-[var(--color-border-strong)] bg-[var(--color-surface)] p-8 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-surface-muted)] text-[var(--color-muted)] mb-3">
            <FileText size={24} aria-hidden="true" />
          </div>
          <h2
            className={cn(
              getTypographyClassName("cardTitle"),
              "text-[var(--color-on-surface)]"
            )}
          >
            Your desk is clear
          </h2>
          <p
            className={cn(
              getTypographyClassName("bodyMd"),
              "mt-1 text-[var(--color-muted)] max-w-sm"
            )}
          >
            Create a new quotation when the trip facts are confirmed.
          </p>
        </div>
      ) : null}

      {!isLoading && !error && items.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => {
            const destinationsText =
              item.tripFacts?.displayRouteText ||
              (item.tripFacts?.destinations && item.tripFacts.destinations.length > 0
                ? item.tripFacts.destinations.join(" → ")
                : null);

            const datesText =
              item.tripFacts?.displayTravelDates ||
              (item.tripFacts?.startDate && item.tripFacts?.endDate
                ? `${item.tripFacts.startDate} – ${item.tripFacts.endDate}`
                : item.tripFacts?.startDate || null);

            const durationText =
              item.tripFacts?.durationDays != null
                ? `${item.tripFacts.durationDays}D${item.tripFacts.durationNights != null ? `${item.tripFacts.durationNights}N` : ""}`
                : null;

            const paxText =
              item.customerFacts?.adults != null
                ? `${item.customerFacts.adults} Adult${item.customerFacts.adults > 1 ? "s" : ""}${
                    item.customerFacts.children ? `, ${item.customerFacts.children} Child${item.customerFacts.children > 1 ? "ren" : ""}` : ""
                  }`
                : null;

            return (
              <article key={item.id} className="h-full">
                <Link
                  href={`/workspace/quotations/${encodeURIComponent(item.id)}`}
                  className="group flex flex-col justify-between h-full rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] transition-all hover:-translate-y-0.5 hover:border-[var(--color-border-strong)] hover:shadow-md"
                >
                  <div>
                    {/* Top Row: Quotation ID Pill + Brand/Locale + Status Badge */}
                    <div className="flex items-center justify-between gap-2 pb-3 border-b border-[var(--color-border)]">
                      <div className="flex items-center gap-1.5 min-w-0">
                        <span
                          className={cn(
                            getTypographyClassName("caption"),
                            "font-mono rounded-md bg-[var(--color-surface-muted)] px-2 py-0.5 text-[var(--color-muted)] truncate"
                          )}
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

                    {/* Customer & Journey Title */}
                    <div className="mt-3.5">
                      <p
                        className={cn(
                          getTypographyClassName("caption"),
                          "flex items-center gap-1.5 text-[var(--color-muted)]"
                        )}
                      >
                        <User size={13} className="shrink-0 text-[var(--color-accent)]" aria-hidden="true" />
                        <span className="truncate">{item.customerName || "Unnamed client"}</span>
                      </p>
                      <h2
                        className={cn(
                          getTypographyClassName("cardTitle"),
                          "mt-1.5 line-clamp-2 text-[var(--color-on-surface)] group-hover:text-[var(--color-accent)] transition-colors"
                        )}
                      >
                        {item.title || "Untitled journey"}
                      </h2>
                    </div>

                    {/* Trip Facts Metadata */}
                    <div
                      className={cn(
                        getTypographyClassName("caption"),
                        "mt-4 flex flex-col gap-2 text-[var(--color-muted)]"
                      )}
                    >
                      {destinationsText ? (
                        <div className="flex items-center gap-1.5">
                          <MapPin size={13} className="shrink-0 text-[var(--color-accent)]" aria-hidden="true" />
                          <span className="truncate">{destinationsText}</span>
                        </div>
                      ) : null}

                      {datesText || durationText ? (
                        <div className="flex items-center gap-1.5">
                          <Calendar size={13} className="shrink-0 text-[var(--color-muted)]" aria-hidden="true" />
                          <span className="truncate">
                            {datesText} {durationText ? `(${durationText})` : ""}
                          </span>
                        </div>
                      ) : null}

                      {paxText ? (
                        <div className="flex items-center gap-1.5">
                          <Users size={13} className="shrink-0 text-[var(--color-muted)]" aria-hidden="true" />
                          <span className="truncate">{paxText}</span>
                        </div>
                      ) : null}
                    </div>
                  </div>

                  {/* Footer Row: Updated Date + Time and Open CTA */}
                  <div className="mt-5 flex items-center justify-between border-t border-[var(--color-border)] pt-3.5">
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
                </Link>
              </article>
            );
          })}
        </div>
      ) : null}

      {!dashboard && data?.nextCursor ? (
        <button
          type="button"
          onClick={() => setCursor(data.nextCursor)}
          className={cn(
            getTypographyClassName("buttonSecondary"),
            "self-start rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 text-[var(--color-on-surface)] transition-all hover:border-[var(--color-border-strong)]"
          )}
        >
          Load more
        </button>
      ) : null}
    </div>
  );
}
