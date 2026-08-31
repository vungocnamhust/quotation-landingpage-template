"use client";

import { useEffect, useMemo, useState } from "react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import { formatMinorAmount } from "../../lib/moneyFormat.ts";
import type { ApPaymentMethod, ApSupplierInvoiceListItem } from "./types.ts";

const INPUT_CLASS = cn(
  getTypographyClassName("bodyMd"),
  "min-h-11 w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)]",
);

const METHODS: ApPaymentMethod[] = ["bank_transfer", "cash", "card", "other"];

type Props = {
  open: boolean;
  onClose: () => void;
  supplierId: string;
  currency: string;
  /** Approved invoices for this supplier with an outstanding balance — remaining-balance display only, server is the source of truth. */
  candidateInvoices: Array<ApSupplierInvoiceListItem & { balance_minor: number }>;
  onSubmit: (input: {
    supplierId: string;
    paidAt: string;
    currency: string;
    amountMinor: number;
    method: ApPaymentMethod;
    reference?: string | null;
    notes?: string | null;
    allocations: Array<{ invoiceId: string; amountMinor: number }>;
  }) => void;
  isSubmitting: boolean;
  error: string | null;
};

export function RecordPaymentDrawer({ open, onClose, supplierId, currency, candidateInvoices, onSubmit, isSubmitting, error }: Props) {
  const [paidAt, setPaidAt] = useState(() => new Date().toISOString().slice(0, 10));
  const [method, setMethod] = useState<ApPaymentMethod>("bank_transfer");
  const [reference, setReference] = useState("");
  const [allocations, setAllocations] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  const totalMajor = useMemo(
    () => Object.values(allocations).reduce((sum, value) => sum + (parseFloat(value) || 0), 0),
    [allocations],
  );

  if (!open) return null;

  const handleSubmit = () => {
    const entries = Object.entries(allocations)
      .map(([invoiceId, value]) => ({ invoiceId, amountMinor: Math.round((parseFloat(value) || 0) * 100) }))
      .filter((entry) => entry.amountMinor > 0);
    if (entries.length === 0) return;
    onSubmit({
      supplierId,
      paidAt,
      currency,
      amountMinor: entries.reduce((sum, e) => sum + e.amountMinor, 0),
      method,
      reference: reference || null,
      allocations: entries,
    });
  };

  return (
    <div role="dialog" aria-modal="true" aria-label="Record payment" className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs">
      <div className="flex h-full w-full max-w-md flex-col gap-4 overflow-y-auto bg-[var(--color-surface)] p-6 shadow-[var(--elevation-card)]">
        <h2 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>Record payment</h2>

        <div className="grid grid-cols-2 gap-3">
          <label className="flex flex-col gap-2">
            <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Paid at</span>
            <input type="date" className={INPUT_CLASS} value={paidAt} onChange={(e) => setPaidAt(e.target.value)} />
          </label>
          <label className="flex flex-col gap-2">
            <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Method</span>
            <select className={INPUT_CLASS} value={method} onChange={(e) => setMethod(e.target.value as ApPaymentMethod)}>
              {METHODS.map((m) => (
                <option key={m} value={m}>
                  {m.replace(/_/g, " ")}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label className="flex flex-col gap-2">
          <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Reference (UNC / bank ref)</span>
          <input className={INPUT_CLASS} value={reference} onChange={(e) => setReference(e.target.value)} />
        </label>

        <div className="flex flex-col gap-2">
          <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Allocate to invoices</span>
          {candidateInvoices.length === 0 ? (
            <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>No approved outstanding invoices for this supplier.</p>
          ) : null}
          {candidateInvoices.map((inv) => {
            const allocatedMajor = parseFloat(allocations[inv.id] || "0") || 0;
            const remaining = inv.balance_minor / 100 - allocatedMajor;
            return (
              <div key={inv.id} className="flex items-center gap-2 rounded-[var(--radius-button)] border border-[var(--color-border)] p-2">
                <div className="flex-1">
                  <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>{inv.invoice_number ?? inv.id}</p>
                  <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
                    remaining {formatMinorAmount(Math.round(remaining * 100), currency)}
                  </p>
                </div>
                <input
                  type="number"
                  step="0.01"
                  value={allocations[inv.id] ?? ""}
                  onChange={(e) => setAllocations((current) => ({ ...current, [inv.id]: e.target.value }))}
                  className={cn(getTypographyClassName("bodySm"), "min-h-9 w-28 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2")}
                />
              </div>
            );
          })}
        </div>

        <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>
          Total: {formatMinorAmount(Math.round(totalMajor * 100), currency)}
        </p>

        {error ? <p className={cn(getTypographyClassName("caption"), "text-rose-600")}>{error}</p> : null}

        <div className="mt-auto flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className={cn(getTypographyClassName("buttonSecondary"), "rounded-[var(--radius-button)] border border-[var(--color-border)] px-4 py-2")}
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={isSubmitting || totalMajor <= 0}
            onClick={handleSubmit}
            className={cn(getTypographyClassName("buttonPrimary"), "rounded-[var(--radius-button)] bg-[var(--color-accent)] px-4 py-2 text-[var(--color-on-accent)] disabled:opacity-60")}
          >
            {isSubmitting ? "Recording…" : "Record payment"}
          </button>
        </div>
      </div>
    </div>
  );
}
