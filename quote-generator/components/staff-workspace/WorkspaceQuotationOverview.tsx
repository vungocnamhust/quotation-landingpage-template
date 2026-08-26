"use client";

import useSWR from "swr";
import { CheckCircle2, AlertCircle, Eye, ArrowRight } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { quotationFetch } from "../../lib/apiError.ts";
import { cn } from "../../utils/cn.ts";
import { WorkspaceNavigationLink } from "./WorkspaceNavigation.tsx";

const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? "";

type Overview = {
  quotation: {
    id: string;
    title: string | null;
    customerName: string | null;
    brandId: string;
    status: string;
    locale: string;
    updatedAt: string;
  };
  workflow: {
    facts: { ready: boolean; missingInputs?: string[] };
    content: { ready: boolean; contentBlockers?: Array<{ path: string; message: string }> };
    design: { ready: boolean; presentationErrors?: string[] };
    review: { ready: boolean; blockers?: string[] };
  };
  publications: Array<{ targetId: string; status: string }>;
};

const fetcher = (url: string) =>
  quotationFetch<Overview>(url, undefined, "Quotation overview could not be loaded.");

export default function WorkspaceQuotationOverview({
  quotationId,
}: {
  quotationId: string;
}) {
  const { data, error, isLoading } = useSWR<Overview>(
    `${API_BASE}/api/v2/workspace/quotations/${encodeURIComponent(quotationId)}/overview`,
    fetcher
  );

  if (isLoading) {
    return (
      <div className="workspace-skeleton">
        <div className="workspace-skeleton__line workspace-skeleton__line--wide" />
        <div className="workspace-skeleton__line workspace-skeleton__line--mid" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-7 shadow-[var(--elevation-card)]">
        <h1
          className={cn(
            getTypographyClassName("pageTitle"),
            "text-[var(--color-on-surface)]"
          )}
        >
          Quotation unavailable
        </h1>
        <p
          className={cn(
            getTypographyClassName("bodyMd"),
            "mt-3 text-[var(--color-muted)]"
          )}
        >
          It may no longer be assigned to your Travel Designer profile.
        </p>
        <WorkspaceNavigationLink
          href="/workspace/quotations"
          className={cn(
            getTypographyClassName("buttonSecondary"),
            "mt-5 inline-block text-[var(--color-on-surface)] transition-colors hover:text-[var(--color-accent)]"
          )}
        >
          Back to my quotations
        </WorkspaceNavigationLink>
      </div>
    );
  }

  const { quotation, workflow, publications } = data;
  const factsMissing = workflow.facts.missingInputs?.length ?? 0;
  const contentMissing = workflow.content.contentBlockers?.length ?? 0;
  const designErrors = workflow.design.presentationErrors?.length ?? 0;
  const reviewBlockers = workflow.review.blockers?.length ?? 0;

  const stages = [
    {
      label: "Facts",
      ready: workflow.facts.ready,
      stageKey: "facts",
      detailText: workflow.facts.ready
        ? "Ready"
        : factsMissing > 0
        ? `${factsMissing} missing input${factsMissing > 1 ? "s" : ""}`
        : "Needs attention",
    },
    {
      label: "Content",
      ready: workflow.content.ready,
      stageKey: "content",
      detailText: workflow.content.ready
        ? "Ready"
        : contentMissing > 0
        ? `${contentMissing} item${contentMissing > 1 ? "s" : ""} incomplete`
        : "Needs attention",
    },
    {
      label: "Design",
      ready: workflow.design.ready,
      stageKey: "design",
      detailText: workflow.design.ready
        ? "Ready"
        : designErrors > 0
        ? `${designErrors} layout issue${designErrors > 1 ? "s" : ""}`
        : "Needs attention",
    },
    {
      label: "Review",
      ready: workflow.review.ready,
      stageKey: "review",
      detailText: workflow.review.ready
        ? "Ready"
        : reviewBlockers > 0
        ? `${reviewBlockers} blocker${reviewBlockers > 1 ? "s" : ""} remaining`
        : "Needs attention",
    },
  ] as const;

  const readyCount = stages.filter((s) => s.ready).length;
  const publishedCount = publications.filter((p) => p.status === "published").length;
  const targetStage = workflow.review.ready
    ? "review"
    : workflow.design.ready
    ? "design"
    : workflow.content.ready
    ? "content"
    : "facts";

  return (
    <main className="flex flex-col gap-7">
      <header className="flex flex-col gap-5 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--elevation-card)]">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p
              className={cn(
                getTypographyClassName("overline"),
                "text-[var(--color-accent)]"
              )}
            >
              {quotation.customerName || "Unnamed client"}
            </p>
            <h1
              className={cn(
                getTypographyClassName("pageTitle"),
                "mt-1 text-[var(--color-on-surface)]"
              )}
            >
              {quotation.title || "Untitled journey"}
            </h1>
            <p
              className={cn(
                getTypographyClassName("bodySm"),
                "mt-2 text-[var(--color-muted)]"
              )}
            >
              Brand: {quotation.brandId} · Status:{" "}
              <span className="text-[var(--color-on-surface)]">
                {quotation.status}
              </span>{" "}
              · Updated {new Date(quotation.updatedAt).toLocaleDateString()}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {workflow.design.ready ? (
              <WorkspaceNavigationLink
                href={`/workspace/quotations/${encodeURIComponent(quotationId)}/edit?stage=design`}
                className={cn(
                  getTypographyClassName("buttonSecondary"),
                  "flex items-center gap-2 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 text-[var(--color-on-surface)] transition-all hover:border-[var(--color-border-strong)]"
                )}
              >
                <Eye size={16} aria-hidden="true" />
                <span>Open preview</span>
              </WorkspaceNavigationLink>
            ) : null}

            <WorkspaceNavigationLink
              href={`/workspace/quotations/${encodeURIComponent(quotationId)}/edit?stage=${targetStage}`}
              className={cn(
                getTypographyClassName("buttonPrimary"),
                "flex items-center gap-2 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-accent)] px-5 py-3 text-[var(--color-on-contrast)] shadow-[var(--elevation-card)] transition-all hover:opacity-92 hover:shadow-md"
              )}
            >
              <span>Continue quotation</span>
              <ArrowRight size={16} aria-hidden="true" />
            </WorkspaceNavigationLink>
          </div>
        </div>

        {/* Workflow Progress Bar */}
        <div className="flex flex-col gap-2 border-t border-[var(--color-border)] pt-4">
          <div className="flex items-center justify-between">
            <span
              className={cn(
                getTypographyClassName("caption"),
                "text-[var(--color-muted)]"
              )}
            >
              Workflow readiness
            </span>
            <span
              className={cn(
                getTypographyClassName("caption"),
                "text-[var(--color-accent)]"
              )}
            >
              {readyCount} of 4 steps ready
            </span>
          </div>
          <div className="workspace-overview-progress">
            <div
              className="workspace-overview-progress__bar"
              style={{ width: `${(readyCount / 4) * 100}%` }}
              role="progressbar"
              aria-valuenow={readyCount}
              aria-valuemin={0}
              aria-valuemax={4}
            />
          </div>
        </div>
      </header>

      {/* Analytics Summary Pills */}
      <section className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-[var(--elevation-card)]">
          <p
            className={cn(
              getTypographyClassName("caption"),
              "text-[var(--color-muted)]"
            )}
          >
            Quotation ID
          </p>
          <p
            className={cn(
              getTypographyClassName("cardTitle"),
              "mt-1 truncate text-[var(--color-on-surface)]"
            )}
          >
            {quotation.id}
          </p>
        </div>
        <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-[var(--elevation-card)]">
          <p
            className={cn(
              getTypographyClassName("caption"),
              "text-[var(--color-muted)]"
            )}
          >
            Locale & Language
          </p>
          <p
            className={cn(
              getTypographyClassName("cardTitle"),
              "mt-1 text-[var(--color-on-surface)]"
            )}
          >
            {quotation.locale}
          </p>
        </div>
        <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-[var(--elevation-card)]">
          <p
            className={cn(
              getTypographyClassName("caption"),
              "text-[var(--color-muted)]"
            )}
          >
            Publications
          </p>
          <p
            className={cn(
              getTypographyClassName("cardTitle"),
              "mt-1 text-[var(--color-on-surface)]"
            )}
          >
            {publishedCount} active target{publishedCount !== 1 ? "s" : ""}
          </p>
        </div>
      </section>

      {/* Stage Cards */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stages.map(({ label, ready, stageKey, detailText }, index) => (
          <WorkspaceNavigationLink
            key={label}
            href={`/workspace/quotations/${encodeURIComponent(quotationId)}/edit?stage=${stageKey}`}
            className="workspace-stage-card group"
          >
            <div className="flex items-center justify-between">
              <span
                className={cn(
                  getTypographyClassName("caption"),
                  "text-[var(--color-muted)]"
                )}
              >
                Step {index + 1}
              </span>
              {ready ? (
                <CheckCircle2
                  size={18}
                  className="workspace-stage-card__icon--ready"
                  aria-hidden="true"
                />
              ) : (
                <AlertCircle
                  size={18}
                  className="workspace-stage-card__icon--pending"
                  aria-hidden="true"
                />
              )}
            </div>

            <h2
              className={cn(
                getTypographyClassName("cardTitle"),
                "mt-1 text-[var(--color-on-surface)] group-hover:text-[var(--color-accent)] transition-colors"
              )}
            >
              {label}
            </h2>

            <p
              className={cn(
                getTypographyClassName("bodySm"),
                ready ? "text-[var(--color-accent)]" : "text-[var(--color-muted)]"
              )}
            >
              {detailText}
            </p>
          </WorkspaceNavigationLink>
        ))}
      </section>
    </main>
  );
}
