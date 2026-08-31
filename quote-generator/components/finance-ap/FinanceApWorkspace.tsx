"use client";

import { useMemo, useState } from "react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import { useToast } from "../staff-workspace/ToastProvider.tsx";
import { APInvoicesBoard, type BoardTab } from "./APInvoicesBoard.tsx";
import { CreateSupplierInvoiceDialog } from "./CreateSupplierInvoiceDialog.tsx";
import { VoucherMatchingWorkbench } from "./VoucherMatchingWorkbench.tsx";
import { RecordPaymentDrawer } from "./RecordPaymentDrawer.tsx";
import { useAPInvoices, type ApInvoiceFilters } from "./useAPInvoices.ts";
import { useVoucherMatching } from "./useVoucherMatching.ts";
import { useAPPayments } from "./useAPPayments.ts";

function filtersForTab(tab: BoardTab, search: string): ApInvoiceFilters {
  const base: ApInvoiceFilters = search ? { search } : {};
  switch (tab) {
    case "due_soon":
      return { ...base, dueWithinDays: 14 };
    case "overdue":
      return { ...base, overdueOnly: true };
    case "disputed":
      return { ...base, status: "disputed" };
    case "unmatched":
      return { ...base, status: "received" };
    case "approved":
      return { ...base, status: "approved" };
    case "all":
    default:
      return base;
  }
}

export function FinanceApWorkspace() {
  const { toast } = useToast();
  const [tab, setTab] = useState<BoardTab>("due_soon");
  const [search, setSearch] = useState("");
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [paymentOpen, setPaymentOpen] = useState(false);

  const filters = useMemo(() => filtersForTab(tab, search), [tab, search]);
  const {
    items,
    isListLoading,
    invoice,
    isCreating,
    actionError,
    createInvoice,
    updateHeader,
    upsertLines,
    applyDetail,
    runAction,
    refreshList,
  } = useAPInvoices(filters, selectedInvoiceId);

  const { matchLine, unmatchLine, waiveLine, disputeLine, approve } = useVoucherMatching(invoice ?? undefined, runAction, applyDetail);
  const { recordPayment, isSubmitting, error: paymentError } = useAPPayments(() => {
    setPaymentOpen(false);
    refreshList();
    toast("Payment recorded", "success");
  });

  const handleAddLine = (input: { lineType: "service" | "adjustment" | "penalty" | "fee"; description: string; amountMinor: number }) => {
    if (!invoice) return;
    const existing = invoice.lines.map((line) => ({
      lineType: line.line_type,
      bookingId: line.booking_id,
      voucherRef: line.voucher_ref,
      description: line.description,
      amountMinor: line.amount_minor,
      sortOrder: line.sort_order,
    }));
    upsertLines(invoice.id, [...existing, { ...input, sortOrder: existing.length }]);
  };

  // Approximation for approved-but-not-yet-fully-paid invoices in the board list — the list
  // endpoint doesn't carry a running balance; a fully-unpaid approved invoice (the common case)
  // has balance == gross. A second partial payment against the same invoice needs the detail view.
  const candidateInvoices = invoice
    ? items
        .filter((item) => item.supplier_id === invoice.supplier_id && item.status === "approved")
        .map((item) => ({ ...item, balance_minor: item.id === invoice.id ? invoice.balance_minor : item.gross_total_minor }))
    : [];

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[380px_1fr]">
      <APInvoicesBoard
        items={items}
        isLoading={isListLoading}
        tab={tab}
        onTabChange={setTab}
        search={search}
        onSearchChange={setSearch}
        selectedInvoiceId={selectedInvoiceId}
        onSelect={setSelectedInvoiceId}
        onCreate={() => setCreateOpen(true)}
      />

      {invoice ? (
        <VoucherMatchingWorkbench
          invoice={invoice}
          actionError={actionError}
          onRecord={() => updateHeader(invoice.id, { action: "record" })}
          onVoid={() => updateHeader(invoice.id, { action: "void" })}
          onAddLine={handleAddLine}
          onMatch={(lineId, voucherRef, mode) => matchLine(lineId, { mode, voucherRef })}
          onUnmatch={unmatchLine}
          onWaive={waiveLine}
          onDispute={disputeLine}
          onApprove={approve}
          onOpenPayment={() => setPaymentOpen(true)}
        />
      ) : (
        <div className="flex items-center justify-center rounded-[var(--radius-card)] border border-dashed border-[var(--color-border)] p-8">
          <p className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-muted)]")}>Select an invoice to reconcile.</p>
        </div>
      )}

      <CreateSupplierInvoiceDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        isCreating={isCreating}
        createInvoice={createInvoice}
        onCreated={(created) => {
          setCreateOpen(false);
          setSelectedInvoiceId(created.id);
          refreshList();
          toast("Invoice created", "success");
        }}
      />

      {invoice ? (
        <RecordPaymentDrawer
          open={paymentOpen}
          onClose={() => setPaymentOpen(false)}
          supplierId={invoice.supplier_id}
          currency={invoice.currency}
          candidateInvoices={candidateInvoices}
          isSubmitting={isSubmitting}
          error={paymentError}
          onSubmit={recordPayment}
        />
      ) : null}
    </div>
  );
}
