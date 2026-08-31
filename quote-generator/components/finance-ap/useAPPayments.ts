"use client";

import { useCallback, useState } from "react";
import { recordApPayment, type ApPayment, type ApPaymentMethod } from "../../lib/quotationApi.ts";
import { apiErrorMessage } from "../../lib/apiError.ts";

function newIdempotencyKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `idem_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

/** Record a single payment across N invoice allocations (§5.5 #9) — nguyên tử. */
export function useAPPayments(onRecorded: () => void) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const recordPayment = useCallback(
    async (input: {
      supplierId: string;
      paidAt: string;
      currency: string;
      amountMinor: number;
      fxRatePpm?: number | null;
      method: ApPaymentMethod;
      reference?: string | null;
      notes?: string | null;
      allocations: Array<{ invoiceId: string; amountMinor: number }>;
    }): Promise<ApPayment | null> => {
      setIsSubmitting(true);
      setError(null);
      try {
        const payment = await recordApPayment(input, newIdempotencyKey());
        onRecorded();
        return payment;
      } catch (err) {
        setError(apiErrorMessage(err));
        return null;
      } finally {
        setIsSubmitting(false);
      }
    },
    [onRecorded],
  );

  return { recordPayment, isSubmitting, error };
}
