"use client";

import { useEffect } from "react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";

type Props = {
  isOpen: boolean;
  businessVersionNumber?: number;
  onConfirm: () => void;
  onCancel: () => void;
};

/**
 * Plan 16 §B.3, Case 2 — clicking a locked (immutable) Fact on the Design
 * canvas must never write a shadow value. This confirms the only path that
 * can change it: opening Facts in edit mode, which on submit creates a new
 * business version. Confirming here only flips edit mode + navigates to
 * Facts; the version itself is created only when the user submits that form.
 */
export default function EditQuotationConfirmModal({ isOpen, businessVersionNumber, onConfirm, onCancel }: Props) {
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onCancel]);

  if (!isOpen) return null;

  const nextVersion = typeof businessVersionNumber === "number" ? businessVersionNumber + 1 : undefined;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="edit-quotation-confirm-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div className="w-full max-w-md rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-5 shadow-2xl">
        <h2 id="edit-quotation-confirm-title" className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
          Start Edit Quotation?
        </h2>
        <p className={cn(getTypographyClassName("bodySm"), "mt-2 text-[var(--color-muted)]")}>
          Facts for this version are frozen. Editing this field will create business
          version{nextVersion ? ` ${nextVersion}` : " N+1"}; the current version and every
          publish made from it stay unchanged.
        </p>
        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className={cn(getTypographyClassName("buttonSecondary"), "rounded-[var(--radius-button)] border border-[var(--color-border)] px-4 py-2 cursor-pointer")}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className={cn(getTypographyClassName("buttonPrimary"), "rounded-[var(--radius-button)] bg-[var(--color-action-primary-surface)] px-4 py-2 text-[var(--color-action-primary-text)] cursor-pointer")}
          >
            Start Edit Quotation
          </button>
        </div>
      </div>
    </div>
  );
}
