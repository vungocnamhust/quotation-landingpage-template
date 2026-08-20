"use client";

import { useEffect } from "react";
import { X, History, ArrowRight, Eye, CheckCircle2, Clock } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import type { QuoteRequestItem } from "../quotation-workspace/factsTypes.ts";
import { useRequestRevisionHistory } from "./useRequestRevisionHistory.ts";

type Props = {
  requestId: string;
  currentRevision: number;
  isOpen: boolean;
  onClose: () => void;
  onSelectRevision: (snapshot: QuoteRequestItem) => void;
};

export default function RequestRevisionHistoryModal({
  requestId,
  currentRevision,
  isOpen,
  onClose,
  onSelectRevision,
}: Props) {
  const {
    revisions,
    isLoading,
    loadingRev,
    error,
    inspectError,
    fetchRevisionSnapshot,
  } = useRequestRevisionHistory(requestId, { enabled: isOpen });

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleInspectRevision = async (revNumber: number) => {
    const snapshot = await fetchRevisionSnapshot(revNumber);
    if (snapshot) {
      onSelectRevision(snapshot);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 sm:p-6 transition-opacity duration-200">
      <div
        className="relative flex max-h-[90vh] w-full max-w-2xl flex-col rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] shadow-2xl overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-labelledby="revision-history-title"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[var(--color-border)] px-6 py-4 bg-[var(--color-surface-muted)]">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--color-accent-wash)] text-[var(--color-accent)]">
              <History size={18} aria-hidden="true" />
            </div>
            <div>
              <h2
                id="revision-history-title"
                className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}
              >
                Revision History
              </h2>
              <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
                Request {requestId} • Current Latest: v{currentRevision}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-2 text-[var(--color-muted)] hover:bg-[var(--color-surface)] hover:text-[var(--color-on-surface)] transition-colors cursor-pointer"
            aria-label="Close history modal"
          >
            <X size={18} aria-hidden="true" />
          </button>
        </div>

        {/* Content */}
        <div className="flex flex-1 flex-col overflow-y-auto p-6 gap-4">
          {inspectError ? (
            <div className={cn(getTypographyClassName("bodySm"), "rounded-[var(--radius-card)] border border-rose-200 bg-rose-50 p-3 text-rose-700")}>
              {inspectError}
            </div>
          ) : null}

          {isLoading ? (
            <div className="flex flex-col gap-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-20 animate-pulse rounded-[var(--radius-card)] bg-[var(--color-surface-muted)]" />
              ))}
            </div>
          ) : error ? (
            <p className={cn(getTypographyClassName("bodyMd"), "text-rose-600")}>
              {error}
            </p>
          ) : revisions.length === 0 ? (
            <p className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-muted)] text-center py-8")}>
              No revision history found.
            </p>
          ) : (
            <div className="relative flex flex-col gap-4 before:absolute before:left-4 before:top-3 before:bottom-3 before:w-0.5 before:bg-[var(--color-border)]">
              {revisions.map((rev) => {
                const isLatest = rev.revision === currentRevision;
                const isInspecting = loadingRev === rev.revision;

                return (
                  <div
                    key={rev.revision}
                    className={cn(
                      "relative flex flex-col gap-2 rounded-[var(--radius-card)] border p-4 pl-12 transition-all",
                      isLatest
                        ? "border-emerald-200 bg-emerald-50/40 shadow-xs"
                        : "border-[var(--color-border)] bg-[var(--color-surface)] hover:border-[var(--color-border-strong)]"
                    )}
                  >
                    {/* Timeline Node Dot */}
                    <div
                      className={cn(
                        "absolute left-2.5 top-4 flex h-4 w-4 items-center justify-center rounded-full border-2 bg-white",
                        isLatest
                          ? "border-emerald-500 text-emerald-600"
                          : "border-neutral-400 text-neutral-400"
                      )}
                      aria-hidden="true"
                    >
                      <div
                        className={cn(
                          "h-1.5 w-1.5 rounded-full",
                          isLatest ? "bg-emerald-500" : "bg-neutral-400"
                        )}
                      />
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className={cn(getTypographyClassName("label"), "text-[var(--color-on-surface)]")}>
                          Revision #{rev.revision}
                        </span>

                        {isLatest ? (
                          <span className={cn(getTypographyClassName("caption"), "flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-0.5 text-emerald-800 border border-emerald-200")}>
                            <CheckCircle2 size={12} aria-hidden="true" />
                            <span>Current (Latest)</span>
                          </span>
                        ) : (
                          <span className={cn(getTypographyClassName("caption"), "rounded-full bg-neutral-100 px-2 py-0.5 text-neutral-600 border border-neutral-200")}>
                            Past Version
                          </span>
                        )}

                        <span className={cn(getTypographyClassName("caption"), "rounded-full bg-[var(--color-surface-muted)] px-2 py-0.5 text-[var(--color-muted)] capitalize")}>
                          {rev.change_source.replace("_", " ")}
                        </span>
                      </div>

                      <div className={cn(getTypographyClassName("caption"), "flex items-center gap-1 text-[var(--color-muted)]")}>
                        <Clock size={12} aria-hidden="true" />
                        <span>{new Date(rev.created_at).toLocaleString()}</span>
                      </div>
                    </div>

                    {/* Change Note */}
                    <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>
                      {rev.change_summary || "No description provided."}
                    </p>

                    {/* Action Button */}
                    <div className="flex justify-end pt-1">
                      <button
                        type="button"
                        disabled={isInspecting}
                        onClick={() => handleInspectRevision(rev.revision)}
                        className={cn(
                          getTypographyClassName("caption"),
                          "flex items-center gap-1.5 transition-colors cursor-pointer px-3 py-1.5 rounded-[var(--radius-button)]",
                          isLatest
                            ? "text-emerald-700 hover:bg-emerald-100/70"
                            : "text-[var(--color-accent)] hover:bg-[var(--color-accent-wash)]"
                        )}
                      >
                        <Eye size={13} aria-hidden="true" />
                        <span>
                          {isInspecting
                            ? "Loading snapshot..."
                            : isLatest
                            ? "View current details"
                            : `Inspect version #${rev.revision}`}
                        </span>
                        <ArrowRight size={12} aria-hidden="true" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end border-t border-[var(--color-border)] px-6 py-3 bg-[var(--color-surface-muted)]">
          <button
            type="button"
            onClick={onClose}
            className={cn(
              getTypographyClassName("buttonSecondary"),
              "rounded-[var(--radius-button)] border border-[var(--color-border)] px-4 py-2 text-[var(--color-on-surface)] hover:bg-[var(--color-surface)] cursor-pointer"
            )}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
