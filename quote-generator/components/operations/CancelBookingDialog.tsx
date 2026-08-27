"use client";

import { useEffect, useState } from "react";
import { AlertCircle, X } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";

export type CancelBookingRequest = { bookingId: string; bookingCode: string; bookingRevision: number };

function useEscapeKey(onClose: () => void) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);
}

function CancelBookingDialogBody({
  request,
  isSubmitting,
  errorMessage,
  onClose,
  onSubmit,
}: {
  request: CancelBookingRequest;
  isSubmitting: boolean;
  errorMessage: string | null;
  onClose: () => void;
  onSubmit: (reason: string) => void;
}) {
  const [reason, setReason] = useState("");
  useEscapeKey(onClose);

  return (
    <div
      className="relative flex w-full max-w-md flex-col rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] shadow-2xl"
      role="dialog"
      aria-modal="true"
      aria-labelledby="cancel-booking-title"
    >
      <div className="flex items-center justify-between border-b border-[var(--color-border)] px-5 py-4">
        <h2 id="cancel-booking-title" className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
          Cancel {request.bookingCode}
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

      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (!reason.trim()) return;
          onSubmit(reason.trim());
        }}
        className="flex flex-col gap-4 p-5"
      >
        <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>
          Every service line still in progress will be cancelled. This cannot be undone.
        </p>

        {errorMessage ? (
          <div className={cn(getTypographyClassName("bodySm"), "flex items-center gap-2 rounded-[var(--radius-card)] border border-rose-200 bg-rose-50 p-3 text-rose-700")}>
            <AlertCircle size={16} className="shrink-0" aria-hidden="true" />
            <span>{errorMessage}</span>
          </div>
        ) : null}

        <label className="flex flex-col gap-1">
          <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Reason</span>
          <textarea
            required
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            rows={3}
            className={cn(getTypographyClassName("bodySm"), "rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[var(--color-on-surface)]")}
          />
        </label>

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className={cn(getTypographyClassName("buttonSecondary"), "rounded-[var(--radius-button)] px-4 py-2 text-[var(--color-muted)] hover:text-[var(--color-on-surface)]")}
          >
            Keep booking
          </button>
          <button
            type="submit"
            disabled={isSubmitting || !reason.trim()}
            className={cn(
              getTypographyClassName("buttonPrimary"),
              "rounded-[var(--radius-button)] border border-rose-300 bg-rose-50 px-4 py-2 text-rose-700 transition-opacity disabled:opacity-50",
            )}
          >
            {isSubmitting ? "Cancelling…" : "Cancel booking"}
          </button>
        </div>
      </form>
    </div>
  );
}

export function CancelBookingDialog({
  request,
  isSubmitting,
  errorMessage,
  onClose,
  onSubmit,
}: {
  request: CancelBookingRequest | null;
  isSubmitting: boolean;
  errorMessage: string | null;
  onClose: () => void;
  onSubmit: (reason: string) => void;
}) {
  if (!request) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
      <CancelBookingDialogBody
        key={request.bookingId}
        request={request}
        isSubmitting={isSubmitting}
        errorMessage={errorMessage}
        onClose={onClose}
        onSubmit={onSubmit}
      />
    </div>
  );
}
