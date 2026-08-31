"use client";

import { useCallback, useState } from "react";
import useSWR from "swr";
import {
  createSupplierInvoice,
  getSupplierInvoice,
  listSupplierInvoices,
  updateSupplierInvoice,
  upsertSupplierInvoiceLines,
  type ApInvoiceLineDraft,
  type ApInvoiceStatus,
  type ApSupplierInvoice,
} from "../../lib/quotationApi.ts";
import { apiErrorMessage, QuotationApiError } from "../../lib/apiError.ts";

function newIdempotencyKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `idem_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

export type ApInvoiceFilters = {
  supplierId?: string;
  status?: ApInvoiceStatus;
  dueWithinDays?: number;
  overdueOnly?: boolean;
  search?: string;
};

/**
 * SWR hub for the AP invoices board + a single selected invoice's detail
 * (mirrors `useCostingWorkspace` — every write's response replaces the
 * detail cache directly rather than triggering a revalidating refetch).
 */
export function useAPInvoices(filters: ApInvoiceFilters, selectedInvoiceId: string | null) {
  const [actionError, setActionError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const {
    data: items,
    isLoading: isListLoading,
    mutate: mutateList,
  } = useSWR(
    ["ap-invoices", filters.supplierId, filters.status, filters.dueWithinDays, filters.overdueOnly, filters.search],
    () => listSupplierInvoices(filters),
    { revalidateOnFocus: false },
  );

  const {
    data: invoice,
    isLoading: isInvoiceLoading,
    mutate: mutateInvoice,
  } = useSWR(selectedInvoiceId ? ["ap-invoice", selectedInvoiceId] : null, ([, id]) => getSupplierInvoice(id), {
    revalidateOnFocus: false,
  });

  const applyDetail = useCallback(
    (result: ApSupplierInvoice) => {
      mutateInvoice(result, { revalidate: false });
      setActionError(null);
      return result;
    },
    [mutateInvoice],
  );

  const runAction = useCallback(
    async <T,>(action: () => Promise<T>): Promise<T | null> => {
      try {
        return await action();
      } catch (error) {
        setActionError(apiErrorMessage(error));
        if (error instanceof QuotationApiError && error.kind === "conflict" && selectedInvoiceId) {
          await mutateInvoice();
        }
        return null;
      }
    },
    [mutateInvoice, selectedInvoiceId],
  );

  const createInvoice = useCallback(
    (input: {
      supplierId: string;
      invoiceNumber?: string | null;
      invoiceDate: string;
      dueDate?: string | null;
      currency: string;
      grossTotalMinor: number;
      taxMinor?: number;
      notes?: string | null;
    }) => {
      setIsCreating(true);
      return runAction(async () => {
        const created = await createSupplierInvoice(input, newIdempotencyKey());
        await mutateList();
        return created;
      }).finally(() => setIsCreating(false));
    },
    [mutateList, runAction],
  );

  const baseInvoiceRevision = invoice?.invoice_revision ?? 0;

  const updateHeader = useCallback(
    (
      invoiceId: string,
      input: {
        action?: "record" | "void";
        invoiceNumber?: string | null;
        invoiceDate?: string | null;
        dueDate?: string | null;
        currency?: string;
        grossTotalMinor?: number;
        taxMinor?: number;
        notes?: string | null;
      },
    ) =>
      runAction(async () => {
        const result = await updateSupplierInvoice(invoiceId, { baseInvoiceRevision, ...input });
        await mutateList();
        return applyDetail(result);
      }),
    [applyDetail, baseInvoiceRevision, mutateList, runAction],
  );

  const upsertLines = useCallback(
    (invoiceId: string, lines: ApInvoiceLineDraft[]) =>
      runAction(async () => {
        const result = await upsertSupplierInvoiceLines(invoiceId, baseInvoiceRevision, lines);
        return applyDetail(result);
      }),
    [applyDetail, baseInvoiceRevision, runAction],
  );

  return {
    items: items ?? [],
    isListLoading,
    invoice,
    isInvoiceLoading,
    isCreating,
    actionError,
    createInvoice,
    updateHeader,
    upsertLines,
    applyDetail,
    runAction,
    baseInvoiceRevision,
    refreshList: mutateList,
    refreshInvoice: () => (selectedInvoiceId ? mutateInvoice() : undefined),
  };
}
