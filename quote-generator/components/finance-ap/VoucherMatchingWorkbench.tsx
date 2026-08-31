"use client";

import { useState } from "react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import { formatMinorAmount } from "../../lib/moneyFormat.ts";
import type { ApInvoiceLine, ApSupplierInvoice } from "./types.ts";

const STATUS_BADGE: Record<string, string> = {
  draft: "bg-neutral-100 text-neutral-700 border-neutral-200",
  received: "bg-sky-50 text-sky-700 border-sky-200",
  matched: "bg-emerald-50 text-emerald-700 border-emerald-200",
  disputed: "bg-rose-50 text-rose-700 border-rose-200",
  approved: "bg-amber-50 text-amber-800 border-amber-300",
  paid: "bg-emerald-600 text-white border-emerald-700",
  void: "bg-neutral-200 text-neutral-500 border-neutral-300",
};

const MATCH_INDICATOR: Record<string, string> = {
  unmatched: "bg-neutral-100 text-neutral-600 border-neutral-200",
  auto_matched: "bg-emerald-50 text-emerald-700 border-emerald-200",
  manual_matched: "bg-amber-50 text-amber-800 border-amber-300",
  waived: "bg-sky-50 text-sky-700 border-sky-200",
  disputed: "bg-rose-50 text-rose-700 border-rose-200",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={cn(getTypographyClassName("caption"), "rounded-full border px-2 py-0.5", STATUS_BADGE[status] ?? STATUS_BADGE.draft)}>
      {status}
    </span>
  );
}

function LineRow({
  line,
  currency,
  onMatch,
  onUnmatch,
  onWaive,
  onDispute,
  disabled,
}: {
  line: ApInvoiceLine;
  currency: string;
  onMatch: (lineId: number, voucherRef: string, mode: "auto" | "manual") => void;
  onUnmatch: (lineId: number) => void;
  onWaive: (lineId: number, note: string) => void;
  onDispute: (lineId: number, note: string) => void;
  disabled: boolean;
}) {
  const [voucherRef, setVoucherRef] = useState(line.voucher_ref ?? "");
  const [note, setNote] = useState("");
  const isMatched = line.match_status === "auto_matched" || line.match_status === "manual_matched" || line.match_status === "waived";

  return (
    <div className="flex flex-col gap-2 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-on-surface)]")}>{line.description}</p>
          <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
            {line.line_type} · {formatMinorAmount(line.amount_minor, currency)}
          </p>
        </div>
        <span className={cn(getTypographyClassName("caption"), "rounded-full border px-2 py-0.5", MATCH_INDICATOR[line.match_status])}>
          {line.match_status.replace(/_/g, " ")}
        </span>
      </div>

      {line.expected_cost_minor != null ? (
        <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
          Expected {formatMinorAmount(line.expected_cost_minor, currency)} · Variance{" "}
          <span className={line.variance_minor ? "text-amber-700" : "text-emerald-700"}>
            {line.variance_minor != null ? formatMinorAmount(line.variance_minor, currency) : "—"}
          </span>
        </p>
      ) : null}

      {line.match_issues_json.length > 0 ? (
        <p className={cn(getTypographyClassName("caption"), "text-rose-600")}>{line.match_issues_json.join(", ")}</p>
      ) : null}

      {line.match_note ? (
        <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>&ldquo;{line.match_note}&rdquo;</p>
      ) : null}

      {!disabled && !isMatched ? (
        <div className="flex flex-wrap items-center gap-2">
          <input
            value={voucherRef}
            onChange={(e) => setVoucherRef(e.target.value)}
            placeholder="Voucher ref (VC-YYYY-####)"
            className={cn(
              getTypographyClassName("bodySm"),
              "min-h-9 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2 text-[var(--color-on-surface)]",
            )}
          />
          <button
            type="button"
            disabled={!voucherRef}
            onClick={() => onMatch(line.id, voucherRef, "auto")}
            className={cn(getTypographyClassName("caption"), "rounded-full border border-[var(--color-border)] px-3 py-1 hover:bg-[var(--color-surface-muted)] disabled:opacity-50")}
          >
            Auto-match
          </button>
          <button
            type="button"
            disabled={!voucherRef}
            onClick={() => onMatch(line.id, voucherRef, "manual")}
            className={cn(getTypographyClassName("caption"), "rounded-full border border-[var(--color-border)] px-3 py-1 hover:bg-[var(--color-surface-muted)] disabled:opacity-50")}
          >
            Manual link
          </button>
        </div>
      ) : null}

      {!disabled && isMatched ? (
        <button
          type="button"
          onClick={() => onUnmatch(line.id)}
          className={cn(getTypographyClassName("caption"), "self-start rounded-full border border-[var(--color-border)] px-3 py-1 hover:bg-[var(--color-surface-muted)]")}
        >
          Unmatch
        </button>
      ) : null}

      {!disabled && line.match_status !== "disputed" ? (
        <div className="flex flex-wrap items-center gap-2">
          <input
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Note (required)"
            className={cn(
              getTypographyClassName("bodySm"),
              "min-h-9 flex-1 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2 text-[var(--color-on-surface)]",
            )}
          />
          <button
            type="button"
            disabled={!note}
            onClick={() => onDispute(line.id, note)}
            className={cn(getTypographyClassName("caption"), "rounded-full border border-rose-200 px-3 py-1 text-rose-700 hover:bg-rose-50 disabled:opacity-50")}
          >
            Dispute
          </button>
          {isMatched ? (
            <button
              type="button"
              disabled={!note}
              onClick={() => onWaive(line.id, note)}
              className={cn(getTypographyClassName("caption"), "rounded-full border border-sky-200 px-3 py-1 text-sky-700 hover:bg-sky-50 disabled:opacity-50")}
            >
              Waive
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

type Props = {
  invoice: ApSupplierInvoice;
  onRecord: () => void;
  onVoid: () => void;
  onAddLine: (input: { lineType: "service" | "adjustment" | "penalty" | "fee"; description: string; amountMinor: number }) => void;
  onMatch: (lineId: number, voucherRef: string, mode: "auto" | "manual") => void;
  onUnmatch: (lineId: number) => void;
  onWaive: (lineId: number, note: string) => void;
  onDispute: (lineId: number, note: string) => void;
  onApprove: () => void;
  onOpenPayment: () => void;
  actionError: string | null;
};

export function VoucherMatchingWorkbench({
  invoice,
  onRecord,
  onVoid,
  onAddLine,
  onMatch,
  onUnmatch,
  onWaive,
  onDispute,
  onApprove,
  onOpenPayment,
  actionError,
}: Props) {
  const [newLineDescription, setNewLineDescription] = useState("");
  const [newLineAmount, setNewLineAmount] = useState("");
  const [newLineType, setNewLineType] = useState<"service" | "adjustment" | "penalty" | "fee">("service");

  const linesLocked = invoice.status === "approved" || invoice.status === "paid" || invoice.status === "void";
  const canReplaceLines = invoice.status === "draft" || invoice.status === "received";

  return (
    <div className="flex flex-col gap-4 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
            {invoice.invoice_number ?? "(no invoice number)"}
          </p>
          <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
            {formatMinorAmount(invoice.gross_total_minor, invoice.currency)} · balance{" "}
            {formatMinorAmount(invoice.balance_minor, invoice.currency)}
          </p>
        </div>
        <StatusBadge status={invoice.status} />
      </div>

      {actionError ? <p className={cn(getTypographyClassName("caption"), "text-rose-600")}>{actionError}</p> : null}

      <div className="flex flex-wrap gap-2">
        {invoice.status === "draft" ? (
          <button
            type="button"
            onClick={onRecord}
            className={cn(getTypographyClassName("buttonSecondary"), "rounded-[var(--radius-button)] border border-[var(--color-border)] px-3 py-1.5")}
          >
            Record invoice
          </button>
        ) : null}
        {invoice.status === "draft" || invoice.status === "received" ? (
          <button
            type="button"
            onClick={onVoid}
            className={cn(getTypographyClassName("buttonSecondary"), "rounded-[var(--radius-button)] border border-rose-200 px-3 py-1.5 text-rose-700")}
          >
            Void
          </button>
        ) : null}
        {invoice.status === "matched" ? (
          <button
            type="button"
            onClick={onApprove}
            className={cn(getTypographyClassName("buttonPrimary"), "rounded-[var(--radius-button)] bg-[var(--color-accent)] px-3 py-1.5 text-[var(--color-on-accent)]")}
          >
            Approve
          </button>
        ) : null}
        {invoice.status === "approved" ? (
          <button
            type="button"
            onClick={onOpenPayment}
            className={cn(getTypographyClassName("buttonPrimary"), "rounded-[var(--radius-button)] bg-[var(--color-accent)] px-3 py-1.5 text-[var(--color-on-accent)]")}
          >
            Record payment
          </button>
        ) : null}
      </div>

      <div className="flex flex-col gap-2">
        {invoice.lines.map((line) => (
          <LineRow
            key={line.id}
            line={line}
            currency={invoice.currency}
            onMatch={onMatch}
            onUnmatch={onUnmatch}
            onWaive={onWaive}
            onDispute={onDispute}
            disabled={linesLocked}
          />
        ))}
        {invoice.lines.length === 0 ? (
          <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>No lines yet.</p>
        ) : null}
      </div>

      {canReplaceLines ? (
        <div className="flex flex-wrap items-end gap-2 border-t border-[var(--color-border)] pt-3">
          <select
            value={newLineType}
            onChange={(e) => setNewLineType(e.target.value as typeof newLineType)}
            className={cn(getTypographyClassName("bodySm"), "min-h-9 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2")}
          >
            <option value="service">service</option>
            <option value="adjustment">adjustment</option>
            <option value="penalty">penalty</option>
            <option value="fee">fee</option>
          </select>
          <input
            value={newLineDescription}
            onChange={(e) => setNewLineDescription(e.target.value)}
            placeholder="Line description (from the invoice)"
            className={cn(getTypographyClassName("bodySm"), "min-h-9 flex-1 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2")}
          />
          <input
            type="number"
            step="0.01"
            value={newLineAmount}
            onChange={(e) => setNewLineAmount(e.target.value)}
            placeholder="Amount"
            className={cn(getTypographyClassName("bodySm"), "min-h-9 w-28 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2")}
          />
          <button
            type="button"
            disabled={!newLineDescription || !newLineAmount}
            onClick={() => {
              onAddLine({
                lineType: newLineType,
                description: newLineDescription,
                amountMinor: Math.round(parseFloat(newLineAmount || "0") * 100),
              });
              setNewLineDescription("");
              setNewLineAmount("");
            }}
            className={cn(getTypographyClassName("caption"), "rounded-full border border-[var(--color-border)] px-3 py-1.5 hover:bg-[var(--color-surface)] disabled:opacity-50")}
          >
            Add line
          </button>
        </div>
      ) : null}
    </div>
  );
}
