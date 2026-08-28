"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo, useState, useTransition } from "react";
import useSWR from "swr";
import { Search, FileText } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { apiErrorMessage, quotationFetch } from "../../lib/apiError.ts";
import { normalizeWorkspaceQuotationView } from "../../lib/workspaceQuotationKanban.ts";
import { cn } from "../../utils/cn.ts";
import { WorkspaceQuotationCard, QuotationItem } from "./WorkspaceQuotationCard.tsx";
import { WorkspaceQuotationTable } from "./WorkspaceQuotationTable.tsx";
import { WorkspaceQuotationKanbanCard } from "./WorkspaceQuotationKanbanCard.tsx";
import { DataKanban, type KanbanColumnDef } from "../ui/data-view/DataKanban.tsx";
import { DataViewToggle, type ViewModeOption } from "../ui/data-view/DataViewToggle.tsx";

const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? "";

type Response = {
  items: QuotationItem[];
  nextCursor: string | null;
  summary: Record<string, number>;
};

type QuotationLane = "facts" | "content" | "review" | "published";

const QUOTATION_KANBAN_COLUMNS = [
  { id: "facts", label: "Draft / Facts Incomplete", ariaLabel: "Draft and facts incomplete quotations", emptyDescription: "No quotations need facts." },
  { id: "content", label: "In Editorial / Content Drafting", ariaLabel: "Quotations in editorial", emptyDescription: "No quotations are waiting for content." },
  { id: "review", label: "Design & Review Ready", ariaLabel: "Quotations in design and review", emptyDescription: "No quotations are ready for design and review." },
  { id: "published", label: "Published / Active", ariaLabel: "Published quotations", emptyDescription: "No active quotations yet." },
] as const satisfies readonly KanbanColumnDef<QuotationLane>[];

const fetcher = (url: string) =>
  quotationFetch<Response>(url, undefined, "Your quotations could not be loaded.");

export default function WorkspaceQuotationList({
  dashboard = false,
}: {
  dashboard?: boolean;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [query, setQuery] = useState(searchParams.get("q") ?? "");
  const [status, setStatus] = useState(searchParams.get("status") ?? "");
  const [cursor, setCursor] = useState<string | null>(null);
  const [laneCursors, setLaneCursors] = useState<Record<QuotationLane, string | null>>({
    facts: null,
    content: null,
    review: null,
    published: null,
  });
  const [, startTransition] = useTransition();
  const requestedView = searchParams.get("view");
  const viewMode: ViewModeOption = dashboard ? "grid" : normalizeWorkspaceQuotationView(requestedView);

  const endpoint = useCallback((lane?: QuotationLane, nextCursor?: string | null) => {
    const params = new URLSearchParams();
    if (query.trim()) params.set("q", query.trim());
    if (status) params.set("status", status);
    if (lane) params.set("workflowLane", lane);
    if (nextCursor) params.set("cursor", nextCursor);
    params.set("limit", dashboard ? "6" : "24");
    return `${API_BASE}/api/v2/workspace/quotations?${params.toString()}`;
  }, [dashboard, query, status]);

  const { data, error, isLoading } = useSWR<Response>(viewMode === "kanban" ? null : endpoint(undefined, cursor), fetcher);
  const factsLane = useSWR<Response>(viewMode === "kanban" ? endpoint("facts", laneCursors.facts) : null, fetcher);
  const contentLane = useSWR<Response>(viewMode === "kanban" ? endpoint("content", laneCursors.content) : null, fetcher);
  const reviewLane = useSWR<Response>(viewMode === "kanban" ? endpoint("review", laneCursors.review) : null, fetcher);
  const publishedLane = useSWR<Response>(viewMode === "kanban" ? endpoint("published", laneCursors.published) : null, fetcher);
  const lanes = useMemo(() => ({ facts: factsLane, content: contentLane, review: reviewLane, published: publishedLane }), [contentLane, factsLane, publishedLane, reviewLane]);

  const replaceQuery = useCallback((next: Partial<{ q: string; status: string; view: ViewModeOption }>) => {
    const params = new URLSearchParams(searchParams.toString());
    const nextQuery = next.q ?? query;
    const nextStatus = next.status ?? status;
    const nextView = next.view ?? viewMode;
    if (nextQuery.trim()) params.set("q", nextQuery.trim()); else params.delete("q");
    if (nextStatus) params.set("status", nextStatus); else params.delete("status");
    if (nextView === "grid") params.delete("view"); else params.set("view", nextView);
    const queryString = params.toString();
    router.replace(queryString ? `${pathname}?${queryString}` : pathname, { scroll: false });
  }, [pathname, query, router, searchParams, status, viewMode]);

  const apply = (next: Partial<{ q: string; status: string }>) =>
    startTransition(() => {
      setCursor(null);
      setLaneCursors({ facts: null, content: null, review: null, published: null });
      if (next.q !== undefined) setQuery(next.q);
      if (next.status !== undefined) setStatus(next.status);
      replaceQuery(next);
    });

  const setViewMode = useCallback((nextView: ViewModeOption) => {
    if (!dashboard) replaceQuery({ view: nextView });
  }, [dashboard, replaceQuery]);

  const filterItem = useCallback((item: QuotationItem, term: string) => {
    const matchTitle = item.title?.toLowerCase().includes(term);
    const matchClient = item.customerName?.toLowerCase().includes(term);
    const matchId = item.id.toLowerCase().includes(term);
    const matchNationality = item.customerFacts?.nationality?.toLowerCase().includes(term);
    const matchRoute =
      item.tripFacts?.displayRouteText?.toLowerCase().includes(term) ||
      item.tripFacts?.destinations?.some((d) => d.toLowerCase().includes(term));
    return Boolean(matchTitle || matchClient || matchId || matchNationality || matchRoute);
  }, []);

  // Client-side fulltext search enhancement for nationality, route, client name, title, id
  const items = useMemo(() => {
    const raw = data?.items ?? [];
    if (!query.trim()) return raw;
    const term = query.trim().toLowerCase();
    return raw.filter((item) => filterItem(item, term));
  }, [data?.items, filterItem, query]);

  const kanbanItems = useMemo(() => {
    const raw = QUOTATION_KANBAN_COLUMNS.flatMap((column) =>
      (lanes[column.id].data?.items ?? []).map((item) => ({
        ...item,
        workflowLane: item.workflowLane ?? column.id,
      }))
    );
    if (!query.trim()) return raw;
    const term = query.trim().toLowerCase();
    return raw.filter((item) => filterItem(item, term));
  }, [filterItem, lanes, query]);
  const loadLaneMore = useCallback((lane: QuotationLane) => {
    const nextCursor = lanes[lane].data?.nextCursor;
    if (nextCursor) {
      setLaneCursors((previous) => ({ ...previous, [lane]: nextCursor }));
    }
  }, [lanes]);

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

          <DataViewToggle viewMode={viewMode} onViewModeChange={setViewMode} kanbanAvailable />
        </div>
      ) : null}

      {viewMode === "kanban" ? (
        <DataKanban
          items={kanbanItems}
          keyExtractor={(item) => item.id}
          kanbanConfig={{
            columns: QUOTATION_KANBAN_COLUMNS,
            statusAccessor: (item) => item.workflowLane ?? "facts",
            renderCard: (item) => <WorkspaceQuotationKanbanCard item={item} />,
            enableDragAndDrop: false,
            getColumnLoadState: (lane) => ({
              isLoading: lanes[lane].isLoading,
              error: lanes[lane].error ? apiErrorMessage(lanes[lane].error) : null,
              hasMore: Boolean(lanes[lane].data?.nextCursor),
              onLoadMore: () => loadLaneMore(lane),
            }),
          }}
        />
      ) : null}

      {viewMode !== "kanban" && error ? (
        <p
          className={cn(
            getTypographyClassName("bodyMd"),
            "rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-5 text-[var(--color-on-surface)] shadow-[var(--elevation-card)]"
          )}
        >
          {apiErrorMessage(error)}
        </p>
      ) : null}

      {viewMode !== "kanban" && isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((idx) => (
            <div
              key={idx}
              className="h-60 animate-pulse rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5"
            />
          ))}
        </div>
      ) : null}

      {viewMode !== "kanban" && !isLoading && !error && !items.length ? (
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

      {viewMode !== "kanban" && !isLoading && !error && items.length > 0 ? (
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

      {!dashboard && viewMode !== "kanban" && data?.nextCursor ? (
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
