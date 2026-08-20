"use client";

import { useMemo } from "react";
import {
  AlertCircle,
  FileText,
  Palette,
  Send,
  ArrowRight,
  Database,
  CheckCircle2,
} from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import type { ReviewResponse, WorkflowResponse } from "./useQuotationWorkspace.ts";
import type { ResolvedHandoff } from "./editableHandoff.ts";
import { fromReviewResponse, type BlockerCategory, type CanonicalBlockerItem } from "../../lib/rules/workflowReconciler.ts";
import { workflowAdapter } from "../../lib/rules/workflowAdapter.ts";

export type Stage = "facts" | "content" | "design" | "review";

export interface ReviewBlockersPanelProps {
  reviewData?: ReviewResponse | null;
  workflowData?: WorkflowResponse | null;
  publicationJob?: { id: string; status: string; lastError: string | null } | null;
  onSetStage: (stage: Stage) => void;
  onNavigateHandoff?: (target: ResolvedHandoff) => void;
}

export type { BlockerCategory };

export type BlockerItem = {
  id: string;
  category: BlockerCategory;
  title: string;
  description: string;
  ctaLabel: string;
  onAction: () => void;
  isAdvisory?: boolean;
};

export function ReviewBlockersPanel({
  reviewData,
  workflowData,
  publicationJob,
  onSetStage,
  onNavigateHandoff,
}: ReviewBlockersPanelProps) {
  const items: BlockerItem[] = useMemo(() => {
    const canonicalItems: CanonicalBlockerItem[] = fromReviewResponse(
      reviewData,
      workflowData,
      publicationJob,
      "vi"
    );

    return canonicalItems.map((item) => ({
      id: item.id,
      category: item.category,
      title: item.title,
      description: item.description,
      ctaLabel: item.ctaLabel,
      isAdvisory: item.isAdvisory,
      onAction: () => {
        if (item.targetHandoff.stage === "facts") {
          onSetStage("facts");
        } else if (item.targetHandoff.stage === "design") {
          onSetStage("design");
        } else if (item.targetHandoff.stage === "publish" || item.targetHandoff.stage === "review") {
          onSetStage("review");
        } else if (onNavigateHandoff) {
          onNavigateHandoff(workflowAdapter.toResolvedHandoff(item));
        } else {
          onSetStage("content");
        }
      },
    }));
  }, [reviewData, workflowData, publicationJob, onSetStage, onNavigateHandoff]);

  const categoryGroups: Array<{
    key: BlockerCategory;
    label: string;
    icon: typeof Database;
    items: BlockerItem[];
  }> = [
    {
      key: "facts",
      label: "Facts",
      icon: Database,
      items: items.filter((i) => i.category === "facts"),
    },
    {
      key: "content",
      label: "Content",
      icon: FileText,
      items: items.filter((i) => i.category === "content"),
    },
    {
      key: "design",
      label: "Design",
      icon: Palette,
      items: items.filter((i) => i.category === "design"),
    },
    {
      key: "publish",
      label: "Publish",
      icon: Send,
      items: items.filter((i) => i.category === "publish"),
    },
  ];

  return (
    <div className="flex flex-col gap-5 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--elevation-card)]">
      <div className="flex items-start gap-3">
        <AlertCircle size={24} className="mt-0.5 text-[var(--color-accent-alt)] shrink-0" aria-hidden="true" />
        <div className="flex flex-col gap-1">
          <h2 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
            Quotation is not ready for publication
          </h2>
          <p className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-muted)]")}>
            Resolve the server-reported review blockers below before publishing this quotation.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {categoryGroups.map((group) => {
          const Icon = group.icon;
          const hardBlockers = group.items.filter((i) => !i.isAdvisory);
          const isDone = hardBlockers.length === 0;

          return (
            <div
              key={group.key}
              className={cn(
                "rounded-[var(--radius-card)] border p-4 flex flex-col gap-3 transition-colors",
                isDone
                  ? "border-[var(--color-border)] bg-[var(--color-surface-muted)] opacity-80"
                  : "border-[var(--color-accent-wash)] bg-[var(--color-surface)] shadow-2xs"
              )}
            >
              <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-2.5">
                <div className="flex items-center gap-2">
                  <Icon
                    size={18}
                    className={cn(
                      isDone ? "text-[var(--color-muted)]" : "text-[var(--color-accent)]"
                    )}
                    aria-hidden="true"
                  />
                  <span className={cn(getTypographyClassName("navTitle"), "text-[var(--color-on-surface)]")}>
                    {group.label}
                  </span>
                </div>
                {isDone ? (
                  <span className={cn(getTypographyClassName("caption"), "flex items-center gap-1.5 text-emerald-600")}>
                    <CheckCircle2 size={14} aria-hidden="true" />
                    Passed
                  </span>
                ) : (
                  <span className={cn(getTypographyClassName("caption"), "rounded-full bg-[var(--color-accent-wash)] px-2.5 py-0.5 text-[var(--color-accent)]")}>
                    {hardBlockers.length} blocker{hardBlockers.length > 1 ? "s" : ""}
                  </span>
                )}
              </div>

              {group.items.length === 0 ? (
                <p className={cn(getTypographyClassName("quote"), "text-[var(--color-muted)] py-1")}>
                  All {group.label.toLowerCase()} checks cleared.
                </p>
              ) : (
                <div className="flex flex-col gap-3">
                  {group.items.map((item) => (
                    <div
                      key={item.id}
                      className={cn(
                        "rounded-[var(--radius-button)] border p-3 flex flex-col gap-2",
                        item.isAdvisory
                          ? "border-[var(--color-border)] bg-[var(--color-surface)]"
                          : "border-[var(--color-border)] bg-[var(--color-surface-muted)]"
                      )}
                    >
                      <div className="flex flex-col gap-0.5">
                        <div className="flex items-center justify-between">
                          <span className={cn(getTypographyClassName("label"), "text-[var(--color-on-surface)]")}>
                            {item.title}
                          </span>
                          {item.isAdvisory ? (
                            <span className={cn(getTypographyClassName("caption"), "rounded-full bg-amber-500/10 px-2 py-0.5 text-amber-700")}>
                              Optional draft
                            </span>
                          ) : null}
                        </div>
                        <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>
                          {item.description}
                        </p>
                      </div>
                      <div className="flex justify-end pt-1">
                        <button
                          type="button"
                          onClick={item.onAction}
                          className={cn(
                            getTypographyClassName("buttonSecondary"),
                            "inline-flex items-center gap-1.5 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] px-3 py-1.5 transition-all"
                          )}
                        >
                          <span>{item.ctaLabel}</span>
                          <ArrowRight size={13} aria-hidden="true" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
