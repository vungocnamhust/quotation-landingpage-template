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

export type Stage = "facts" | "content" | "design" | "review";

export interface ReviewBlockersPanelProps {
  reviewData?: ReviewResponse | null;
  workflowData?: WorkflowResponse | null;
  publicationJob?: { id: string; status: string; lastError: string | null } | null;
  onSetStage: (stage: Stage) => void;
  onNavigateHandoff?: (target: ResolvedHandoff) => void;
}

export type BlockerCategory = "facts" | "content" | "design" | "publish";

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
  const items = useMemo(() => {
    const missingInputs = reviewData?.missingInputs ?? workflowData?.facts.missingInputs ?? [];
    const blockingDrafts = reviewData?.blockingDrafts ?? workflowData?.content.blockingDrafts ?? [];
    const contentBlockers = reviewData?.contentBlockers ?? workflowData?.content.contentBlockers ?? [];
    const presentationErrors = reviewData?.presentationErrors ?? workflowData?.design.presentationErrors ?? [];
    const contentReadiness = reviewData?.contentReadiness ?? [];

    const list: BlockerItem[] = [];

    // 1. Facts Blockers
    if (missingInputs.length > 0) {
      list.push({
        id: "facts-missing",
        category: "facts",
        title: "Missing Required Facts",
        description: `The quotation is missing ${missingInputs.length} required fact(s): ${missingInputs.join(", ")}.`,
        ctaLabel: "Fix in Facts",
        onAction: () => onSetStage("facts"),
      });
    }

    // 2. Content Blockers / Advisory Drafts
    if (blockingDrafts.length > 0) {
      list.push({
        id: "content-drafts",
        category: "content",
        title: "Unreviewed Content Drafts",
        description: `There are ${blockingDrafts.length} content candidate(s) available for review: ${blockingDrafts.join(", ")}.`,
        ctaLabel: "Review Content Candidates",
        isAdvisory: true,
        onAction: () => onSetStage("content"),
      });
    }

    contentBlockers.forEach((blocker, idx) => {
      list.push({
        id: `content-blocker-${idx}`,
        category: "content",
        title: `Content Blocker in ${blocker.sectionId}`,
        description: blocker.message,
        ctaLabel: `Edit ${blocker.sectionId}`,
        onAction: () => {
          if (onNavigateHandoff) {
            onNavigateHandoff({ stage: "content", section: blocker.sectionId, source: "blocker", wildcardIndices: [] });
          } else {
            onSetStage("content");
          }
        },
      });
    });

    contentReadiness.forEach((item, idx) => {
      if (item.status) {
        list.push({
          id: `content-readiness-${idx}`,
          category: "content",
          title: item.label,
          description: item.missing.map((m) => m.message).join(". ") || "Content incomplete.",
          ctaLabel: item.targetStage === "facts" ? "Go to Facts" : "Go to Content",
          onAction: () => {
            if (item.targetStage === "facts") {
              onSetStage("facts");
            } else if (onNavigateHandoff) {
              onNavigateHandoff({ stage: "content", section: item.sectionId, source: "blocker", wildcardIndices: [] });
            } else {
              onSetStage("content");
            }
          },
        });
      }
    });

    // 3. Design / PDF Layout Blockers
    presentationErrors.forEach((error, idx) => {
      const itineraryMatch = error.match(/^\/itinerary\/days\/(\d+)(?:\/(description|title))?$/);
      const hotelMatch = error.match(/^\/stays\/hotels\/(\d+)$/);

      if (itineraryMatch) {
        const dayIndex = parseInt(itineraryMatch[1], 10);
        const dayNumber = dayIndex + 1;
        const fieldType = itineraryMatch[2];

        if (fieldType === "description") {
          list.push({
            id: `design-error-${idx}`,
            category: "design",
            title: `Nội dung Ngày ${dayNumber} quá dài (vượt quá 1,150 ký tự)`,
            description: `Văn bản mô tả của Ngày ${dayNumber} vượt quá giới hạn trang in A4 PDF. Vui lòng rút gọn nội dung Ngày ${dayNumber} trong Content Studio.`,
            ctaLabel: `Sửa nội dung Ngày ${dayNumber}`,
            onAction: () => {
              if (onNavigateHandoff) {
                onNavigateHandoff({ stage: "content", section: `itinerary:day:${dayNumber}`, source: "blocker", wildcardIndices: [] });
              } else {
                onSetStage("content");
              }
            },
          });
        } else if (fieldType === "title") {
          list.push({
            id: `design-error-${idx}`,
            category: "design",
            title: `Tiêu đề Ngày ${dayNumber} quá dài (vượt quá 170 ký tự)`,
            description: `Tiêu đề Ngày ${dayNumber} vượt quá giới hạn trang in A4 PDF. Vui lòng rút gọn tiêu đề Ngày ${dayNumber}.`,
            ctaLabel: `Sửa tiêu đề Ngày ${dayNumber}`,
            onAction: () => {
              if (onNavigateHandoff) {
                onNavigateHandoff({ stage: "content", section: `itinerary:day:${dayNumber}`, source: "blocker", wildcardIndices: [] });
              } else {
                onSetStage("content");
              }
            },
          });
        } else {
          list.push({
            id: `design-error-${idx}`,
            category: "design",
            title: `Lỗi dữ liệu Ngày ${dayNumber}`,
            description: `Nội dung Ngày ${dayNumber} không hợp lệ cho bố cục trang in PDF.`,
            ctaLabel: `Chỉnh sửa Ngày ${dayNumber}`,
            onAction: () => {
              if (onNavigateHandoff) {
                onNavigateHandoff({ stage: "content", section: `itinerary:day:${dayNumber}`, source: "blocker", wildcardIndices: [] });
              } else {
                onSetStage("content");
              }
            },
          });
        }
      } else if (hotelMatch) {
        const hotelIndex = parseInt(hotelMatch[1], 10);
        const hotelNumber = hotelIndex + 1;
        list.push({
          id: `design-error-${idx}`,
          category: "design",
          title: `Thông tin Khách sạn ${hotelNumber} quá dài (vượt quá 2,100 ký tự)`,
          description: `Văn bản giới thiệu khách sạn vượt quá giới hạn trang in A4 PDF. Vui lòng rút gọn thông tin khách sạn.`,
          ctaLabel: `Chỉnh sửa Khách sạn`,
          onAction: () => {
            if (onNavigateHandoff) {
              onNavigateHandoff({ stage: "content", section: "hotel_plan", source: "blocker", wildcardIndices: [] });
            } else {
              onSetStage("content");
            }
          },
        });
      } else {
        list.push({
          id: `design-error-${idx}`,
          category: "design",
          title: "Presentation & Layout Check Failed",
          description: error,
          ctaLabel: "Inspect Design",
          onAction: () => onSetStage("design"),
        });
      }
    });

    const assetReadiness = reviewData?.assetReadiness;
    if (assetReadiness && !assetReadiness.ready && assetReadiness.missing && assetReadiness.missing.length > 0) {
      list.push({
        id: "asset-missing",
        category: "design",
        title: `Thiếu ${assetReadiness.missing.length} hình ảnh tư liệu trên R2`,
        description: `Báo giá tham chiếu các hình ảnh chưa có trên thư viện R2: ${assetReadiness.missing.join(", ")}.`,
        ctaLabel: "Kiểm tra Design",
        onAction: () => onSetStage("design"),
      });
    }

    // 4. Publish Job Blockers
    if (publicationJob?.status === "failed") {
      list.push({
        id: "publish-failed",
        category: "publish",
        title: "PDF Publication Job Failed",
        description: publicationJob.lastError || "Background PDF rendering job failed.",
        ctaLabel: "Check Target Settings",
        onAction: () => onSetStage("review"),
      });
    }

    return list;
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
