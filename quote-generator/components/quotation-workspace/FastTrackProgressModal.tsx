"use client";

import { CheckCircle2, Loader2, Sparkles, Image as ImageIcon, Layout } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import type { FastTrackProgress } from "../../lib/quotationFastTrack.ts";

type Props = {
  isOpen: boolean;
  progress: FastTrackProgress | null;
};

export default function FastTrackProgressModal({ isOpen, progress }: Props) {
  if (!isOpen) return null;

  // Every number here now comes from the server's real progress stream
  // (16.3 F-21) — the assemble POST is the only source of truth for
  // completion, but these percentages reflect events the server actually
  // published as it worked, not fabricated client-side counts.
  const currentStage = progress?.stage ?? "create";
  const currentNum = progress?.current ?? 0;
  const totalNum = progress?.total ?? 1;
  const progressPercent =
    currentStage === "create"
      ? 15
      : currentStage === "facts_media"
      ? 35
      : currentStage === "content_generation"
      ? Math.min(90, Math.round(35 + (currentNum / Math.max(1, totalNum)) * 50))
      : currentStage === "review"
      ? 95
      : 100;

  const steps = [
    {
      id: "create",
      title: "Initialize Quotation Facts",
      description: "Hydrating guest composition, route schedule, and pricing structure.",
      icon: Layout,
      isDone: ["facts_media", "content_generation", "complete"].includes(currentStage),
      isCurrent: currentStage === "create",
    },
    {
      id: "facts_media",
      title: "Auto-Resolve Media Assets",
      description: "Assigning hero imagery and hotel photography from catalog.",
      icon: ImageIcon,
      isDone: ["content_generation", "complete"].includes(currentStage),
      isCurrent: currentStage === "facts_media",
    },
    {
      id: "content_generation",
      title: "Generate AI Storylines & Copy",
      description:
        currentStage === "content_generation" && progress?.current && progress?.total
          ? `Drafting & applying narrative copy (${progress.current}/${progress.total} sections)...`
          : "Writing engaging destination narratives, daily itineraries, and terms.",
      icon: Sparkles,
      isDone: ["review", "complete"].includes(currentStage),
      isCurrent: currentStage === "content_generation",
    },
  ];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="fasttrack-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm transition-all"
    >
      <div className="flex w-full max-w-lg flex-col gap-6 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-6 shadow-2xl">
        {/* Header */}
        <div className="flex items-center gap-3 border-b border-[var(--color-border)] pb-4">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[var(--color-accent-wash)] text-[var(--color-accent)]">
            <Sparkles size={20} className="animate-pulse" />
          </div>
          <div>
            <h2
              id="fasttrack-modal-title"
              className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}
            >
              Assembling Quotation Studio
            </h2>
            <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
              Automated Fast-Track Pipeline in progress…
            </p>
          </div>
        </div>

        {/* Dynamic Progress Bar */}
        <div className="flex flex-col gap-1.5">
          <div className="flex justify-between items-center text-[var(--color-muted)]">
            <span className={cn(getTypographyClassName("caption"))}>
              {progress?.message || "Processing..."}
            </span>
            <span className={cn(getTypographyClassName("label"), "text-[var(--color-accent)]")}>
              {progressPercent}%
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--color-surface-muted)] border border-[var(--color-border)]">
            <div
              className="h-full bg-[var(--color-accent)] transition-all duration-300 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* Steps Breakdown */}
        <div className="flex flex-col gap-3">
          {steps.map((step, idx) => {
            const Icon = step.icon;
            return (
              <div
                key={step.id}
                className={cn(
                  "flex items-start gap-3 rounded-[var(--radius-button)] p-3 border transition-colors",
                  step.isCurrent
                    ? "border-[var(--color-accent)] bg-[var(--color-accent-wash)]/40"
                    : step.isDone
                    ? "border-emerald-200 bg-emerald-50/50"
                    : "border-[var(--color-border)] bg-[var(--color-surface-muted)] opacity-60"
                )}
              >
                <div className="mt-0.5 shrink-0">
                  {step.isDone ? (
                    <CheckCircle2 size={18} className="text-emerald-600" />
                  ) : step.isCurrent ? (
                    <Loader2 size={18} className="animate-spin text-[var(--color-accent)]" />
                  ) : (
                    <Icon size={18} className="text-[var(--color-muted)]" />
                  )}
                </div>

                <div className="min-w-0 flex-1">
                  <p
                    className={cn(
                      getTypographyClassName("label"),
                      step.isDone
                        ? "text-emerald-900"
                        : step.isCurrent
                        ? "text-[var(--color-accent)]"
                        : "text-[var(--color-muted)]"
                    )}
                  >
                    {idx + 1}. {step.title}
                  </p>
                  <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)] mt-0.5")}>
                    {step.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        <p className={cn(getTypographyClassName("caption"), "text-center text-[var(--color-muted)]")}>
          Please keep this window open while AI narrative and media assets are synchronized.
        </p>
      </div>
    </div>
  );
}
