"use client";

import { useEffect, useState } from "react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import { SupplierSelect } from "../supplier/SupplierSelect.tsx";
import type { ApSupplierInvoice } from "./types.ts";

const INPUT_CLASS = cn(
  getTypographyClassName("bodyMd"),
  "min-h-11 w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:opacity-60",
);

function Field({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-2">
      <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
        {label}
        {required ? <span className="ml-0.5 text-[var(--color-accent)]">*</span> : null}
      </span>
      {children}
    </label>
  );
}

type Props = {
  open: boolean;
  onClose: () => void;
  onCreated: (invoice: ApSupplierInvoice) => void;
  createInvoice: (input: {
    supplierId: string;
    invoiceNumber?: string | null;
    invoiceDate: string;
    dueDate?: string | null;
    currency: string;
    grossTotalMinor: number;
    notes?: string | null;
  }) => Promise<ApSupplierInvoice | null>;
  isCreating: boolean;
};

export function CreateSupplierInvoiceDialog({ open, onClose, onCreated, createInvoice, isCreating }: Props) {
  const [supplierId, setSupplierId] = useState<string | null>(null);
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [invoiceDate, setInvoiceDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [dueDate, setDueDate] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [grossMajor, setGrossMajor] = useState("");
  const [notes, setNotes] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  const handleSubmit = async () => {
    setFormError(null);
    if (!supplierId) {
      setFormError("Choose a supplier.");
      return;
    }
    const grossMinor = Math.round(parseFloat(grossMajor || "0") * 100);
    if (!grossMinor || grossMinor <= 0) {
      setFormError("Enter a gross total greater than zero.");
      return;
    }
    const created = await createInvoice({
      supplierId,
      invoiceNumber: invoiceNumber || null,
      invoiceDate,
      dueDate: dueDate || null,
      currency,
      grossTotalMinor: grossMinor,
      notes: notes || null,
    });
    if (created) onCreated(created);
  };

  return (
    <div role="dialog" aria-modal="true" aria-label="New supplier invoice" className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
      <div className="flex w-full max-w-lg flex-col gap-4 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--elevation-card)]">
        <h2 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>New supplier invoice</h2>

        <Field label="Supplier" required>
          <SupplierSelect value={supplierId} onChange={(id) => setSupplierId(id)} variant="compact" placeholder="Select supplier..." />
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Invoice number">
            <input className={INPUT_CLASS} value={invoiceNumber} onChange={(e) => setInvoiceNumber(e.target.value)} />
          </Field>
          <Field label="Currency" required>
            <input className={INPUT_CLASS} value={currency} maxLength={3} onChange={(e) => setCurrency(e.target.value.toUpperCase())} />
          </Field>
          <Field label="Invoice date" required>
            <input type="date" className={INPUT_CLASS} value={invoiceDate} onChange={(e) => setInvoiceDate(e.target.value)} />
          </Field>
          <Field label="Due date">
            <input type="date" className={INPUT_CLASS} value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
          </Field>
          <Field label="Gross total" required>
            <input
              type="number"
              step="0.01"
              className={INPUT_CLASS}
              value={grossMajor}
              onChange={(e) => setGrossMajor(e.target.value)}
            />
          </Field>
        </div>

        <Field label="Notes">
          <textarea className={cn(INPUT_CLASS, "min-h-20")} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </Field>

        {formError ? <p className={cn(getTypographyClassName("caption"), "text-rose-600")}>{formError}</p> : null}

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className={cn(getTypographyClassName("buttonSecondary"), "rounded-[var(--radius-button)] border border-[var(--color-border)] px-4 py-2 text-[var(--color-on-surface)]")}
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={isCreating}
            onClick={handleSubmit}
            className={cn(
              getTypographyClassName("buttonPrimary"),
              "rounded-[var(--radius-button)] bg-[var(--color-accent)] px-4 py-2 text-[var(--color-on-accent)] disabled:opacity-60",
            )}
          >
            {isCreating ? "Creating…" : "Create draft"}
          </button>
        </div>
      </div>
    </div>
  );
}
