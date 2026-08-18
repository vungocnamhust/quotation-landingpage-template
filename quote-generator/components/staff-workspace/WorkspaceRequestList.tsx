"use client";

import { useSearchParams } from "next/navigation";
import { useState, useTransition, useMemo } from "react";
import useSWR from "swr";
import { Search, Inbox, LayoutGrid, List } from "lucide-react";
import { getTypographyClassName } from "../../config/typography";
import { apiErrorMessage, quotationFetch } from "../../lib/apiError";
import { cn } from "../../utils/cn";
import { WorkspaceRequestCard } from "./WorkspaceRequestCard";
import { WorkspaceRequestTable } from "./WorkspaceRequestTable";
import type { QuoteRequestItem } from "../quotation-workspace/factsTypes";

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

  const { data, error, isLoading } = useSWR<Response>(
    `${API_BASE}/api/v2/workspace/requests?${params}`,
    fetcher
  );

  const applyFilter = (next: Partial<{ q: string; role: string; status: string }>) =>
    startTransition(() => {
      if (next.q !== undefined) setQuery(next.q);
      if (next.role !== undefined) setRole(next.role);
      if (next.status !== undefined) setStatus(next.status);
    });

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
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-1 shrink-0">
          <button
            type="button"
            onClick={() => setViewMode("grid")}
            className={cn(
              getTypographyClassName("caption"),
              "flex items-center gap-1.5 rounded-md px-3 py-1.5 transition-all cursor-pointer",
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
              "flex items-center gap-1.5 rounded-md px-3 py-1.5 transition-all cursor-pointer",
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
            <Inbox size={24} aria-hidden="true" />
          </div>
          <h2 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
            No requests found
          </h2>
          <p className={cn(getTypographyClassName("bodyMd"), "mt-1 text-[var(--color-muted)] max-w-sm")}>
            {query.trim()
              ? `No journey requests matching "${query}".`
              : "No enquiries received yet. Create a new request to get started."}
          </p>
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
