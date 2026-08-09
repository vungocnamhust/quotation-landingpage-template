"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState, useTransition } from "react";
import useSWR from "swr";
import { Search, FileText, Calendar, ChevronRight, CheckCircle2, Clock } from "lucide-react";
import { getTypographyClassName } from "../../config/typography";
import { apiErrorMessage, quotationFetch } from "../../lib/apiError";
import { cn } from "../../utils/cn";

const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? "";

type Item = {
  id: string;
  title: string | null;
  customerName: string | null;
  brandId: string;
  status: string;
  locale: string;
  updatedAt: string;
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
    <div className="flex flex-col gap-4">
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
        <div className="workspace-skeleton">
          <div className="workspace-skeleton__line workspace-skeleton__line--wide" />
          <div className="workspace-skeleton__line workspace-skeleton__line--mid" />
          <div className="workspace-skeleton__line workspace-skeleton__line--narrow" />
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

      <div className="grid gap-3">
        {items.map((item) => (
          <Link
            key={item.id}
            href={`/workspace/quotations/${encodeURIComponent(item.id)}`}
            className="group grid items-center gap-3 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] transition-all hover:-translate-y-0.5 hover:border-[var(--color-border-strong)] sm:grid-cols-[minmax(0,1fr)_auto]"
          >
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={cn(
                    getTypographyClassName("caption"),
                    "text-[var(--color-muted)]"
                  )}
                >
                  {item.customerName || "Unnamed client"} · {item.brandId}
                </span>
              </div>
              <h2
                className={cn(
                  getTypographyClassName("cardTitle"),
                  "mt-1 text-[var(--color-on-surface)] group-hover:text-[var(--color-accent)] transition-colors"
                )}
              >
                {item.title || "Untitled journey"}
              </h2>
            </div>

            <div className="flex items-center justify-between gap-4 sm:justify-end">
              <div className="flex flex-col items-start sm:items-end gap-1">
                <StatusBadge status={item.status} />
                <span
                  className={cn(
                    getTypographyClassName("caption"),
                    "flex items-center gap-1 text-[var(--color-muted)]"
                  )}
                >
                  <Calendar size={12} aria-hidden="true" />
                  <span>{new Date(item.updatedAt).toLocaleDateString()}</span>
                </span>
              </div>
              <ChevronRight
                size={18}
                className="text-[var(--color-muted)] transition-transform group-hover:translate-x-1 group-hover:text-[var(--color-accent)]"
                aria-hidden="true"
              />
            </div>
          </Link>
        ))}
      </div>

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
