"use client";

import { useCallback, useState } from "react";
import useSWR from "swr";
import {
  addBookingLine,
  cancelBooking,
  createBooking,
  listBookingBoard,
  transitionBookingLine,
  updateBookingLineOps,
} from "../../lib/quotationApi.ts";
import { apiErrorMessage, QuotationApiError } from "../../lib/apiError.ts";
import { mergeBookingDetailIntoBoard, optimisticallyCancelBooking, optimisticallyTransitionBoardLine } from "./operationsBoardCache.ts";
import type { BookingBoardResponse, BookingDetailResponse, BookingLineStatus } from "./types.ts";

function newIdempotencyKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `idem_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

export type OperationsBoardFilters = {
  status?: BookingLineStatus;
  assignee?: string;
};

/**
 * Headless hook for the Operations board (15.6) — owns the board SWR cache
 * and every mutation. There is no client-side deadline math here: the server
 * pre-computes urgency and every deadline from FROZEN terms snapshots
 * (core/rules/booking_rules.py); the board only groups/renders what it's given.
 */
export function useOperationsBoard(filters: OperationsBoardFilters = {}) {
  const [actionError, setActionError] = useState<string | null>(null);

  const { data, isLoading, mutate } = useSWR(
    ["operations-board", filters.status ?? null, filters.assignee ?? null],
    () => listBookingBoard({ status: filters.status, assignee: filters.assignee }),
    { revalidateOnFocus: false },
  );

  const runAction = useCallback(
    async <T,>(action: () => Promise<T>): Promise<T | null> => {
      try {
        const result = await action();
        setActionError(null);
        return result;
      } catch (error) {
        setActionError(apiErrorMessage(error));
        if (error instanceof QuotationApiError && error.kind === "conflict") {
          await mutate();
        }
        return null;
      }
    },
    [mutate],
  );

  const runOptimisticBookingAction = useCallback(
    async (
      optimisticData: (current: BookingBoardResponse | undefined) => BookingBoardResponse | undefined,
      action: () => Promise<BookingDetailResponse>,
    ): Promise<BookingDetailResponse | null> => {
      let detail: BookingDetailResponse | null = null;
      try {
        await mutate(
          async (current) => {
            detail = await action();
            return mergeBookingDetailIntoBoard(current, detail);
          },
          {
            optimisticData: (current) => optimisticData(current ?? { items: [] }) ?? { items: [] },
            rollbackOnError: true,
            populateCache: true,
            revalidate: true,
          },
        );
        setActionError(null);
        return detail;
      } catch (error) {
        setActionError(apiErrorMessage(error));
        if (error instanceof QuotationApiError && error.kind === "conflict") {
          await mutate();
        }
        return null;
      }
    },
    [mutate],
  );

  const createNewBooking = useCallback(
    (input: { quotation_id: string; deposit_received_at: string; customer_balance_due_date?: string | null }) =>
      runAction(async () => {
        const result = await createBooking(input, newIdempotencyKey());
        await mutate();
        return result;
      }),
    [mutate, runAction],
  );

  const transitionLine = useCallback(
    (
      bookingId: string,
      lineId: string,
      baseBookingRevision: number,
      input: { to: BookingLineStatus; supplier_ref?: string | null; cancel_reason?: string | null },
    ) =>
      runOptimisticBookingAction(
        (current) => optimisticallyTransitionBoardLine(current, bookingId, lineId, input.to),
        async () => transitionBookingLine(
          bookingId,
          lineId,
          { base_booking_revision: baseBookingRevision, ...input },
          newIdempotencyKey(),
        ),
      ),
    [runOptimisticBookingAction],
  );

  const updateLineOps = useCallback(
    (
      bookingId: string,
      lineId: string,
      baseBookingRevision: number,
      input: { request_by_date?: string | null; assignee_email?: string | null; notes?: string | null; supplier_ref?: string | null },
    ) =>
      runAction(async () => {
        const result = await updateBookingLineOps(bookingId, lineId, { base_booking_revision: baseBookingRevision, ...input });
        await mutate();
        return result;
      }),
    [mutate, runAction],
  );

  const addLine = useCallback(
    (bookingId: string, baseBookingRevision: number, serviceLineId: string) =>
      runAction(async () => {
        const result = await addBookingLine(bookingId, { base_booking_revision: baseBookingRevision, service_line_id: serviceLineId });
        await mutate();
        return result;
      }),
    [mutate, runAction],
  );

  const cancelWholeBooking = useCallback(
    (bookingId: string, baseBookingRevision: number, reason: string) =>
      runOptimisticBookingAction(
        (current) => optimisticallyCancelBooking(current, bookingId),
        () => cancelBooking(bookingId, { base_booking_revision: baseBookingRevision, reason }),
      ),
    [runOptimisticBookingAction],
  );

  return {
    items: data?.items ?? [],
    isLoading,
    actionError,
    refresh: () => mutate(),
    createNewBooking,
    transitionLine,
    updateLineOps,
    addLine,
    cancelWholeBooking,
  };
}
