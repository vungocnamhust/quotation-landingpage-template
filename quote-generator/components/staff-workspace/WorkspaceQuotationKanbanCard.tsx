"use client";

import { ArrowRight, CheckCircle2, CircleAlert, MapPin, User } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { formatCommercialTotal } from "../../lib/workspaceQuotationKanban.ts";
import { cn } from "../../utils/cn.ts";
import type { QuotationItem } from "./WorkspaceQuotationCard.tsx";
import { WorkspaceNavigationLink } from "./WorkspaceNavigation.tsx";

export function WorkspaceQuotationKanbanCard({ item }: { item: QuotationItem }) {
  const route = item.tripFacts?.displayRouteText || item.tripFacts?.destinations?.join(" → ") || "Route TBD";
  const commercialTotal = formatCommercialTotal(item.commercial);
  const readiness = item.workflow ?? {
    facts: { ready: false },
    content: { ready: false },
    design: { ready: false },
    review: { ready: false },
  };
  const readySteps = Object.values(readiness).filter((step) => step.ready).length;

  return (
    <article className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-[var(--elevation-card)]">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className={cn(getTypographyClassName("caption"), "truncate text-[var(--color-muted)]")}>
            #{item.id}
          </p>
          <h3 className={cn(getTypographyClassName("cardTitle"), "mt-1 line-clamp-2 text-[var(--color-on-surface)]")}>
            {item.title || "Untitled journey"}
          </h3>
        </div>
        <span className={cn(getTypographyClassName("caption"), "shrink-0 rounded-[var(--radius-button)] bg-[var(--color-accent-wash)] px-2 py-1 text-[var(--color-accent)]")}>
          {item.status}
        </span>
      </div>

      <div className={cn(getTypographyClassName("caption"), "mt-3 flex flex-col gap-2 border-y border-[var(--color-border)] py-3 text-[var(--color-muted)]")}>
        <p className="flex items-center gap-2 truncate"><User size={13} className="shrink-0 text-[var(--color-accent)]" aria-hidden="true" /><span className="truncate text-[var(--color-on-surface)]">{item.customerName || "Unnamed client"}</span></p>
        <p className="flex items-center gap-2 truncate"><MapPin size={13} className="shrink-0 text-[var(--color-accent)]" aria-hidden="true" /><span className="truncate" title={route}>{route}</span></p>
      </div>

      <div className="mt-3 flex items-center justify-between gap-3">
        <span className={cn(getTypographyClassName("caption"), "inline-flex items-center gap-1 text-[var(--color-muted)]")}>
          {readiness.review.ready ? <CheckCircle2 size={13} className="text-[var(--color-accent)]" aria-hidden="true" /> : <CircleAlert size={13} aria-hidden="true" />}
          {readySteps} of 4 ready
        </span>
        <span className={cn(getTypographyClassName("caption"), "truncate text-[var(--color-on-surface)]")} title={item.commercial?.label ?? undefined}>
          {commercialTotal ?? "Commercial total pending"}
        </span>
      </div>

      <WorkspaceNavigationLink
        href={`/workspace/quotations/${encodeURIComponent(item.id)}/edit`}
        className={cn(getTypographyClassName("buttonSecondary"), "mt-4 inline-flex items-center gap-1 text-[var(--color-accent)] hover:underline")}
      >
        Open quotation <ArrowRight size={14} aria-hidden="true" />
      </WorkspaceNavigationLink>
    </article>
  );
}
