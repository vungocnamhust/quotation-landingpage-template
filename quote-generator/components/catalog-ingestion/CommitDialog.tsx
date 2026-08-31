"use client";

import { useEffect, useState } from "react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import type { IngestionResolutionEntry } from "./types.ts";

interface Props {
  entries: IngestionResolutionEntry[];
  isCommitting: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

function countByAction(entries: IngestionResolutionEntry[]) {
  return entries.reduce(
    (acc, entry) => {
      if (entry.action === "create") acc.create += 1;
      else if (entry.action === "supersede_rate") acc.supersede += 1;
      else if (entry.action === "skip_duplicate") acc.skip += 1;
      else if (entry.action === "update") acc.update += 1;
      return acc;
    },
    { create: 0, update: 0, supersede: 0, skip: 0 },
  );
}

export function CommitDialog({ entries, isCommitting, onClose, onConfirm }: Props) {
  const [step, setStep] = useState<1 | 2>(1);

  const handleClose = () => {
    setStep(1);
    onClose();
  };

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") handleClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- mount-scoped: this dialog is only ever mounted while open (parent conditionally renders it)
  }, []);

  const counts = countByAction(entries);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Commit ingestion batch"
      className="fixed inset-0 z-50 flex items-center justify-center bg-[color-mix(in_srgb,var(--color-contrast)_35%,transparent)] p-4"
    >
      <section className="w-full max-w-lg rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-6 shadow-[var(--elevation-card)]">
        <h2 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
          {step === 1 ? "Review before commit" : "Confirm commit"}
        </h2>

        <ul className={cn(getTypographyClassName("bodySm"), "mt-4 flex flex-col gap-1.5 text-[var(--color-on-surface)]")}>
          <li>{counts.create} to create</li>
          <li>{counts.update} to update</li>
          <li>{counts.supersede} rate(s) to supersede</li>
          <li>{counts.skip} skipped as duplicates</li>
        </ul>

        {step === 2 ? (
          <p className={cn(getTypographyClassName("bodySm"), "mt-4 rounded-[var(--radius-input)] border border-amber-500/40 bg-amber-500/5 p-3 text-[var(--color-on-surface)]")}>
            This writes to the real catalog through the same services a staff editor uses.
            This cannot be undone from this screen — are you sure?
          </p>
        ) : null}

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={handleClose}
            className={cn(
              getTypographyClassName("buttonSecondary"),
              "rounded-[var(--radius-button)] border border-[var(--color-border-strong)] px-4 py-2.5 text-[var(--color-on-surface)] transition-colors hover:bg-[var(--color-surface-hover)]",
            )}
          >
            Cancel
          </button>
          {step === 1 ? (
            <button
              type="button"
              onClick={() => setStep(2)}
              className={cn(
                getTypographyClassName("buttonPrimary"),
                "rounded-[var(--radius-button)] bg-[var(--color-accent)] px-4 py-2.5 text-white shadow-xs transition-all hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)]",
              )}
            >
              Continue
            </button>
          ) : (
            <button
              type="button"
              disabled={isCommitting}
              onClick={onConfirm}
              className={cn(
                getTypographyClassName("buttonPrimary"),
                "rounded-[var(--radius-button)] bg-[var(--color-accent)] px-4 py-2.5 text-white shadow-xs transition-all hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] disabled:cursor-not-allowed disabled:opacity-50",
              )}
            >
              {isCommitting ? "Committing…" : "Commit"}
            </button>
          )}
        </div>
      </section>
    </div>
  );
}
