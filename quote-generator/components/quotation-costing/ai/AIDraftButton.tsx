"use client";

import { useState } from "react";
import { Sparkles } from "lucide-react";
import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";
import { TripProfileReviewDialog } from "./TripProfileReviewDialog.tsx";
import type { DraftDaySpec, DraftServicesResponse } from "../types.ts";

export interface AIDraftButtonProps {
  sheetId: string;
  baseCostingRevision: number;
  days: DraftDaySpec[];
  disabled?: boolean;
  onDraftComplete: (result: DraftServicesResponse) => void;
  onConflict?: () => void;
  className?: string;
}

/**
 * Entry point for the AI Service Drafter (15.7 §2) — mounted on `CostingSettingsBar`.
 * Opens the human-in-the-loop `TripProfileReviewDialog`; that dialog owns the only
 * path to Analyze/Draft, this button just gates whether there's anything to draft
 * against (a day/destination anchor from `days`).
 */
export function AIDraftButton({ sheetId, baseCostingRevision, days, disabled, onDraftComplete, onConflict, className }: AIDraftButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const noDays = days.length === 0;

  return (
    <>
      <button
        type="button"
        disabled={disabled || noDays}
        title={noDays ? "No day/destination data available to draft against yet." : undefined}
        onClick={() => setIsOpen(true)}
        className={cn(
          getTypographyClassName("buttonPrimary"),
          "flex items-center gap-1.5 rounded-[var(--radius-button)] border border-[var(--color-accent)] bg-[var(--color-accent-wash)] px-3.5 py-1.5 text-[var(--color-accent)] transition-colors hover:bg-[var(--color-accent)] hover:text-white disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer",
          className,
        )}
      >
        <Sparkles size={14} aria-hidden="true" />
        <span>AI Drafter</span>
      </button>

      {isOpen ? (
        <TripProfileReviewDialog
          sheetId={sheetId}
          baseCostingRevision={baseCostingRevision}
          days={days}
          onClose={() => setIsOpen(false)}
          onDraftComplete={(result) => {
            onDraftComplete(result);
            setIsOpen(false);
          }}
          onConflict={onConflict}
        />
      ) : null}
    </>
  );
}

export default AIDraftButton;
