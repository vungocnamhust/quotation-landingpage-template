"use client";

import { useSearchParams } from "next/navigation";
import { useState, useTransition, useMemo } from "react";
import useSWR from "swr";
import { Search, Inbox, LayoutGrid, List } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { apiErrorMessage, quotationFetch } from "../../lib/apiError.ts";
import { cn } from "../../utils/cn.ts";
import { WorkspaceRequestCard } from "./WorkspaceRequestCard.tsx";
import { WorkspaceRequestTable } from "./WorkspaceRequestTable.tsx";
import type { QuoteRequestItem } from "../quotation-workspace/factsTypes.ts";

const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? "";

type Response = {
  items: QuoteRequestItem[];
  total: number;
  nextCursor: string | null;
  summary: Record<string, number>;
};

const fetcher = (url: string) =>
  quotationFetch<Response>(url, undefined, "Your requests could not be loaded.");

export default function WorkspaceRequestList() {
  const searchParams = useSearchParams();
  const [query, setQuery] = useState(searchParams.get("q") ?? "");
  const [role, setRole] = useState(searchParams.get("role") ?? "");
  const [status, setStatus] = useState(searchParams.get("status") ?? "");
  const [viewMode, setViewMode] = useState<"grid" | "table">("grid");
  const [, startTransition] = useTransition();

  const params = new URLSearchParams();
  if (query.trim()) params.set("q", query.trim());
  if (role) params.set("role", role);
  if (status) params.set("status", status);

  const { data, error, isLoading, mutate } = useSWR<Response>(
    `${API_BASE}/api/v2/workspace/requests?${params}`,
    fetcher
  );

  const applyFilter = (next: Partial<{ q: string; role: string; status: string }>) =>
    startTransition(() => {
      if (next.q !== undefined) setQuery(next.q);
      if (next.role !== undefined) setRole(next.role);
      if (next.status !== undefined) setStatus(next.status);
    });

  const clearAllFilters = () => {
    applyFilter({ q: "", role: "", status: "" });
  };

  const hasActiveFilters = Boolean(query.trim() || role || status);
  const items = useMemo(() => data?.items ?? [], [data?.items]);

  return (
    <div className="flex flex-col gap-5">
      {/* Header & Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-[var(--elevation-card)]">
        <div className="flex flex-wrap flex-1 gap-3 min-w-[280px]">
          {/* Search Input */}
          <div className="relative min-w-[200px] flex-1">
            <Search
              size={16}
              className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--color-muted)]"
              aria-hidden="true"
            />
            <input
              value={query}
              onChange={(e) => applyFilter({ q: e.target.value })}
              placeholder="Search request ID, requester name, company, or destination..."
              className={cn(
                getTypographyClassName("bodyMd"),
                "min-h-11 w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] pl-10 pr-3 text-[var(--color-on-surface)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)]"
              )}
            />
          </div>

          {/* Role Filter */}
          <select
            value={role}
            onChange={(e) => applyFilter({ role: e.target.value })}
            className={cn(
              getTypographyClassName("bodySm"),
              "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)]"
            )}
          >
            <option value="">All Roles</option>
            <option value="traveller">Traveller</option>
            <option value="advisor">Travel Advisor</option>
          </select>

          {/* Status Filter */}
          <select
            value={status}
            onChange={(e) => applyFilter({ status: e.target.value })}
            className={cn(
              getTypographyClassName("bodySm"),
              "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)]"
            )}
          >
            <option value="">All Statuses</option>
            <option value="new">New Request</option>
            <option value="under_review">Under Review</option>
            <option value="quotation_created">Quotation Created</option>
            <option value="archived">Archived</option>
          </select>

          {hasActiveFilters ? (
            <button
              type="button"
              onClick={clearAllFilters}
              className={cn(
                getTypographyClassName("buttonSecondary"),
                "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border)] px-3 text-[var(--color-muted)] hover:text-[var(--color-on-surface)] hover:bg-[var(--color-surface-muted)] transition-colors cursor-pointer"
              )}
            >
              Clear filters
            </button>
          ) : null}
        </div>

        {/* View Toggle (Grid / Table) */}
        <div className="flex items-center gap-1 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] p-1">
          <button
            type="button"
            onClick={() => setViewMode("grid")}
            className={cn(
              getTypographyClassName("caption"),
              "flex items-center gap-1.5 rounded-[calc(var(--radius-button)-2px)] px-3 py-1.5 transition-all cursor-pointer",
              viewMode === "grid"
                ? "bg-[var(--color-accent-wash)] text-[var(--color-accent)] shadow-2xs"
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
              "flex items-center gap-1.5 rounded-[calc(var(--radius-button)-2px)] px-3 py-1.5 transition-all cursor-pointer",
              viewMode === "table"
                ? "bg-[var(--color-accent-wash)] text-[var(--color-accent)] shadow-2xs"
                : "text-[var(--color-muted)] hover:text-[var(--color-on-surface)]"
            )}
            aria-label="Table View"
          >
            <List size={15} aria-hidden="true" />
            <span className="hidden sm:inline">Table</span>
          </button>
        </div>
      </div>

      {error ? (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-card)] border border-rose-200 bg-rose-50 p-5 text-rose-800 shadow-[var(--elevation-card)]">
          <div className="flex flex-col gap-0.5">
            <p className={cn(getTypographyClassName("label"), "text-rose-900")}>Could not load requests</p>
            <p className={cn(getTypographyClassName("bodySm"), "text-rose-700")}>{apiErrorMessage(error)}</p>
          </div>
          <button
            type="button"
            onClick={() => mutate()}
            className={cn(
              getTypographyClassName("buttonSecondary"),
              "rounded-[var(--radius-button)] border border-rose-300 bg-white px-3.5 py-1.5 text-rose-800 hover:bg-rose-100 transition-colors cursor-pointer"
            )}
          >
            Retry
          </button>
        </div>
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
            <Inbox size={24} aria-hidden="true" />
          </div>
          <h2 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
            No requests found
          </h2>
          <p className={cn(getTypographyClassName("bodyMd"), "mt-1 text-[var(--color-muted)] max-w-sm")}>
            {hasActiveFilters
              ? "No journey requests matching your active filters."
              : "No enquiries received yet. Create a new request to get started."}
          </p>
          {hasActiveFilters ? (
            <button
              type="button"
              onClick={clearAllFilters}
              className={cn(
                getTypographyClassName("buttonSecondary"),
                "mt-4 rounded-[var(--radius-button)] border border-[var(--color-border)] px-4 py-2 text-[var(--color-on-surface)] hover:bg-[var(--color-surface-muted)] cursor-pointer"
              )}
            >
              Clear all filters
            </button>
          ) : null}
        </div>
      ) : null}

      {!isLoading && !error && items.length > 0 ? (
        viewMode === "table" ? (
          <WorkspaceRequestTable items={items} />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((item) => (
              <WorkspaceRequestCard key={item.id} item={item} />
            ))}
          </div>
        )
      ) : null}
    </div>
  );
}
