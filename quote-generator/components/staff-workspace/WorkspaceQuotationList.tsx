"use client";

import { useSearchParams } from "next/navigation";
import { useState, useTransition, useMemo } from "react";
import useSWR from "swr";
import { Search, FileText, LayoutGrid, List } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { apiErrorMessage, quotationFetch } from "../../lib/apiError.ts";
import { cn } from "../../utils/cn.ts";
import { WorkspaceQuotationCard, QuotationItem } from "./WorkspaceQuotationCard.tsx";
import { WorkspaceQuotationTable } from "./WorkspaceQuotationTable.tsx";

const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? "";

type Response = {
  items: QuotationItem[];
  nextCursor: string | null;
  summary: Record<string, number>;
};

const fetcher = (url: string) =>
  quotationFetch<Response>(url, undefined, "Your quotations could not be loaded.");

export default function WorkspaceQuotationList({
  dashboard = false,
}: {
  dashboard?: boolean;
}) {
  const searchParams = useSearchParams();
  const [query, setQuery] = useState(searchParams.get("q") ?? "");
  const [status, setStatus] = useState(searchParams.get("status") ?? "");
  const [cursor, setCursor] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"grid" | "table">("grid");
  const [, startTransition] = useTransition();

  const params = new URLSearchParams();
  if (query.trim()) params.set("q", query.trim());
  if (status) params.set("status", status);
  if (cursor) params.set("cursor", cursor);
  params.set("limit", dashboard ? "6" : "24");

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

  // Client-side fulltext search enhancement for nationality, route, client name, title, id
  const items = useMemo(() => {
    const raw = data?.items ?? [];
    if (!query.trim()) return raw;
    const term = query.trim().toLowerCase();
    return raw.filter((item) => {
      const matchTitle = item.title?.toLowerCase().includes(term);
      const matchClient = item.customerName?.toLowerCase().includes(term);
      const matchId = item.id.toLowerCase().includes(term);
      const matchNationality = item.customerFacts?.nationality?.toLowerCase().includes(term);
      const matchRoute =
        item.tripFacts?.displayRouteText?.toLowerCase().includes(term) ||
        item.tripFacts?.destinations?.some((d) => d.toLowerCase().includes(term));
      return matchTitle || matchClient || matchId || matchNationality || matchRoute;
    });
  }, [data?.items, query]);

  return (
    <div className="flex flex-col gap-5">
      {!dashboard ? (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-[var(--elevation-card)]">
          <div className="flex flex-wrap flex-1 gap-3 min-w-[280px]">
            <div className="relative min-w-[220px] flex-1">
              <Search
                size={16}
                className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--color-muted)]"
                aria-hidden="true"
              />
              <input
                value={query}
                onChange={(event) => apply({ q: event.target.value })}
                placeholder="Search client, quotation ID, route, or nationality..."
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

          {/* View Mode Toggle */}
          <div className="flex items-center rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-1 shrink-0">
            <button
              type="button"
              onClick={() => setViewMode("grid")}
              className={cn(
                getTypographyClassName("caption"),
                "flex items-center gap-1.5 rounded-md px-3 py-1.5 transition-all",
                viewMode === "grid"
                  ? "bg-[var(--color-surface)] text-[var(--color-accent)] shadow-xs"
                  : "text-[var(--color-muted)] hover:text-[var(--color-on-surface)]"
              )}
              aria-label="Grid View"
            >
              <LayoutGrid size={15} aria-hidden="true" />
              <span className="hidden sm:inline">Grid</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode("table")}
              className={cn(
                getTypographyClassName("caption"),
                "flex items-center gap-1.5 rounded-md px-3 py-1.5 transition-all",
                viewMode === "table"
                  ? "bg-[var(--color-surface)] text-[var(--color-accent)] shadow-xs"
                  : "text-[var(--color-muted)] hover:text-[var(--color-on-surface)]"
              )}
              aria-label="Table View"
            >
              <List size={15} aria-hidden="true" />
              <span className="hidden sm:inline">Table</span>
            </button>
          </div>
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
              className="h-60 animate-pulse rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5"
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
            {query.trim()
              ? `No quotations found matching "${query}".`
              : "Create a new quotation when the trip facts are confirmed."}
          </p>
        </div>
      ) : null}

      {!isLoading && !error && items.length > 0 ? (
        viewMode === "table" && !dashboard ? (
          <WorkspaceQuotationTable items={items} />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((item) => (
              <WorkspaceQuotationCard key={item.id} item={item} />
            ))}
          </div>
        )
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
