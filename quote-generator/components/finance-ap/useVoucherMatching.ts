"use client";

import { useCallback } from "react";
import {
  actOnSupplierInvoiceLine,
  approveSupplierInvoice,
  matchSupplierInvoiceLine,
  type ApSupplierInvoice,
} from "../../lib/quotationApi.ts";

type RunAction = <T>(action: () => Promise<T>) => Promise<T | null>;

/**
 * Line-level match/unmatch/waive/dispute + invoice approve — shares the parent
 * `useAPInvoices` hook's CAS-aware `runAction`/`applyDetail` funnel so a lost
 * revision race reloads the same detail cache both hooks read from.
 */
export function useVoucherMatching(
  invoice: ApSupplierInvoice | undefined,
  runAction: RunAction,
  applyDetail: (result: ApSupplierInvoice) => ApSupplierInvoice,
) {
  const baseInvoiceRevision = invoice?.invoice_revision ?? 0;

  const matchLine = useCallback(
    (
      lineId: number,
      input: { mode: "auto" | "manual"; bookingLineId?: string | null; voucherRef?: string | null; toleranceBps?: number },
    ) => {
      if (!invoice) return Promise.resolve(null);
      return runAction(async () => {
        const result = await matchSupplierInvoiceLine(invoice.id, lineId, { baseInvoiceRevision, ...input });
        return applyDetail(result);
      });
    },
    [applyDetail, baseInvoiceRevision, invoice, runAction],
  );

  const unmatchLine = useCallback(
    (lineId: number) => {
      if (!invoice) return Promise.resolve(null);
      return runAction(async () => {
        const result = await actOnSupplierInvoiceLine(invoice.id, lineId, "unmatch", { baseInvoiceRevision });
        return applyDetail(result);
      });
    },
    [applyDetail, baseInvoiceRevision, invoice, runAction],
  );

  const waiveLine = useCallback(
    (lineId: number, note: string) => {
      if (!invoice) return Promise.resolve(null);
      return runAction(async () => {
        const result = await actOnSupplierInvoiceLine(invoice.id, lineId, "waive", { baseInvoiceRevision, note });
        return applyDetail(result);
      });
    },
    [applyDetail, baseInvoiceRevision, invoice, runAction],
  );

  const disputeLine = useCallback(
    (lineId: number, note: string) => {
      if (!invoice) return Promise.resolve(null);
      return runAction(async () => {
        const result = await actOnSupplierInvoiceLine(invoice.id, lineId, "dispute", { baseInvoiceRevision, note });
        return applyDetail(result);
      });
    },
    [applyDetail, baseInvoiceRevision, invoice, runAction],
  );

  const approve = useCallback(() => {
    if (!invoice) return Promise.resolve(null);
    return runAction(async () => {
      const result = await approveSupplierInvoice(invoice.id, baseInvoiceRevision);
      return applyDetail(result);
    });
  }, [applyDetail, baseInvoiceRevision, invoice, runAction]);

  return { matchLine, unmatchLine, waiveLine, disputeLine, approve };
}
