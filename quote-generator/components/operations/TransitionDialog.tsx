"use client";

import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, Copy, X } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import type { BookingLineProfile, BookingLineStatus } from "./types.ts";

export type TransitionRequest = { line: BookingLineProfile; to: BookingLineStatus };
type TransitionResult = { voucherRef?: string | null } | void;

function useEscapeKey(onClose: () => void) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);
}

function TransitionDialogBody({
  request,
  isSubmitting,
  errorMessage,
  onClose,
  onSubmit,
}: {
  request: TransitionRequest;
  isSubmitting: boolean;
  errorMessage: string | null;
  onClose: () => void;
  onSubmit: (input: { supplier_ref?: string; cancel_reason?: string }) => Promise<TransitionResult>;
}) {
  const [supplierRef, setSupplierRef] = useState("");
  const [cancelReason, setCancelReason] = useState("");
  const [voucherRef, setVoucherRef] = useState<string | null>(null);

  useEscapeKey(onClose);

  const isConfirm = request.to === "confirmed";
  const isCancel = request.to === "cancelled";

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const result = await onSubmit(
      isConfirm
        ? { supplier_ref: supplierRef.trim() || undefined }
        : isCancel
          ? { cancel_reason: cancelReason.trim() }
          : {},
    );
    if (result && "voucherRef" in result && result.voucherRef) {
      setVoucherRef(result.voucherRef);
    } else if (!isConfirm) {
      onClose();
    }
  };

  return (
    <div
      className="relative flex w-full max-w-md flex-col rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] shadow-2xl"
      role="dialog"
      aria-modal="true"
      aria-labelledby="transition-dialog-title"
    >
      <div className="flex items-center justify-between border-b border-[var(--color-border)] px-5 py-4">
        <h2 id="transition-dialog-title" className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
          {isConfirm ? "Confirm booking line" : isCancel ? "Cancel booking line" : "Update status"}
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

      {voucherRef ? (
        <div className="flex flex-col items-center gap-3 p-6 text-center">
          <CheckCircle2 size={32} className="text-emerald-600" aria-hidden="true" />
          <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>Voucher issued</p>
          <button
            type="button"
            onClick={() => navigator.clipboard?.writeText(voucherRef)}
            className={cn(
              getTypographyClassName("cardTitle"),
              "inline-flex items-center gap-2 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-accent-wash)] px-4 py-2 text-[var(--color-accent)]",
            )}
          >
            {voucherRef}
            <Copy size={14} aria-hidden="true" />
          </button>
          <button
            type="button"
            onClick={onClose}
            className={cn(getTypographyClassName("buttonSecondary"), "mt-2 text-[var(--color-muted)] hover:text-[var(--color-on-surface)]")}
          >
            Done
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-4 p-5">
          <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>{request.line.title_snapshot}</p>

          {errorMessage ? (
            <div className={cn(getTypographyClassName("bodySm"), "flex items-center gap-2 rounded-[var(--radius-card)] border border-rose-200 bg-rose-50 p-3 text-rose-700")}>
              <AlertCircle size={16} className="shrink-0" aria-hidden="true" />
              <span>{errorMessage}</span>
            </div>
          ) : null}

          {isConfirm ? (
            <label className="flex flex-col gap-1">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Supplier confirmation code</span>
              <input
                type="text"
                value={supplierRef}
                onChange={(event) => setSupplierRef(event.target.value)}
                placeholder="e.g. CONF-12345"
                className={cn(getTypographyClassName("bodySm"), "rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[var(--color-on-surface)]")}
              />
            </label>
          ) : null}

          {isCancel ? (
            <label className="flex flex-col gap-1">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Reason</span>
              <textarea
                required
                value={cancelReason}
                onChange={(event) => setCancelReason(event.target.value)}
                rows={3}
                className={cn(getTypographyClassName("bodySm"), "rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[var(--color-on-surface)]")}
              />
            </label>
          ) : null}

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
              disabled={isSubmitting || (isCancel && !cancelReason.trim())}
              className={cn(
                getTypographyClassName("buttonPrimary"),
                "rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-accent)] px-4 py-2 text-[var(--color-on-accent)] transition-opacity disabled:opacity-50",
              )}
            >
              {isSubmitting ? "Saving…" : "Confirm"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

export function TransitionDialog({
  request,
  isSubmitting,
  errorMessage,
  onClose,
  onSubmit,
}: {
  request: TransitionRequest | null;
  isSubmitting: boolean;
  errorMessage: string | null;
  onClose: () => void;
  onSubmit: (input: { supplier_ref?: string; cancel_reason?: string }) => Promise<TransitionResult>;
}) {
  if (!request) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
      <TransitionDialogBody
        key={`${request.line.id}-${request.to}`}
        request={request}
        isSubmitting={isSubmitting}
        errorMessage={errorMessage}
        onClose={onClose}
        onSubmit={onSubmit}
      />
    </div>
  );
}
