"use client";

import { useEffect } from "react";
import { AlertCircle, X } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";

function useEscapeKey(onClose: () => void, isOpen: boolean) {
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);
}

export function CreateBookingDialog({
  isOpen,
  isSubmitting,
  errorMessage,
  onClose,
  onSubmit,
}: {
  isOpen: boolean;
  isSubmitting: boolean;
  errorMessage: string | null;
  onClose: () => void;
  onSubmit: (input: { quotation_id: string; deposit_received_at: string; customer_balance_due_date?: string }) => void;
}) {
  useEscapeKey(onClose, isOpen);
  if (!isOpen) return null;

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const quotationId = String(form.get("quotation_id") ?? "").trim();
    const depositReceivedAt = String(form.get("deposit_received_at") ?? "");
    const customerBalanceDueDate = String(form.get("customer_balance_due_date") ?? "").trim();
    if (!quotationId || !depositReceivedAt) return;
    onSubmit({
      quotation_id: quotationId,
      deposit_received_at: depositReceivedAt,
      customer_balance_due_date: customerBalanceDueDate || undefined,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
      <div
        className="relative flex w-full max-w-md flex-col rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-booking-title"
      >
        <div className="flex items-center justify-between border-b border-[var(--color-border)] px-5 py-4">
          <h2 id="create-booking-title" className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
            Start a booking
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-2 text-[var(--color-muted)] hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-on-surface)]"
            aria-label="Close dialog"
          >
            <X size={16} aria-hidden="true" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4 p-5">
          <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>
            The quotation must already have an attached costing sheet with service lines.
          </p>

          {errorMessage ? (
            <div className={cn(getTypographyClassName("bodySm"), "flex items-center gap-2 rounded-[var(--radius-card)] border border-rose-200 bg-rose-50 p-3 text-rose-700")}>
              <AlertCircle size={16} className="shrink-0" aria-hidden="true" />
              <span>{errorMessage}</span>
            </div>
          ) : null}

          <label className="flex flex-col gap-1">
            <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Quotation ID</span>
            <input
              name="quotation_id"
              type="text"
              required
              placeholder="qtn_…"
              className={cn(getTypographyClassName("bodySm"), "rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[var(--color-on-surface)]")}
            />
          </label>

          <label className="flex flex-col gap-1">
            <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Deposit received on</span>
            <input
              name="deposit_received_at"
              type="date"
              required
              className={cn(getTypographyClassName("bodySm"), "rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[var(--color-on-surface)]")}
            />
          </label>

          <label className="flex flex-col gap-1">
            <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Customer balance due (optional)</span>
            <input
              name="customer_balance_due_date"
              type="date"
              className={cn(getTypographyClassName("bodySm"), "rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[var(--color-on-surface)]")}
            />
          </label>

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className={cn(getTypographyClassName("buttonSecondary"), "rounded-[var(--radius-button)] px-4 py-2 text-[var(--color-muted)] hover:text-[var(--color-on-surface)]")}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className={cn(
                getTypographyClassName("buttonPrimary"),
                "rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-accent)] px-4 py-2 text-[var(--color-on-accent)] transition-opacity disabled:opacity-50",
              )}
            >
              {isSubmitting ? "Creating…" : "Create booking"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
