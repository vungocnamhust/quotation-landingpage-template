"use client";

import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { attachCostingSheetToQuotation } from "../../lib/quotationApi.ts";
import { apiErrorMessage } from "../../lib/apiError.ts";
import type { AttachRecovery } from "../../lib/attachRecovery.ts";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";

type Props = {
  quotationId: string;
  recovery: AttachRecovery;
  onRecovered: () => void;
};

/** Persistent, user-controlled recovery for an attach response lost in transit. */
export function AttachRecoveryBanner({ quotationId, recovery, onRecovered }: Props) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const retry = async () => {
    setPending(true);
    setError(null);
    try {
      await attachCostingSheetToQuotation(recovery.sheetId, quotationId, recovery.idempotencyKey);
      onRecovered();
    } catch (cause) {
      setError(apiErrorMessage(cause));
    } finally {
      setPending(false);
    }
  };

  return (
    <section
      role="alert"
      aria-live="polite"
      className={cn(
        "sticky top-3 z-30 flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-card)] border border-amber-300 bg-amber-50 p-4 text-amber-950 shadow-md",
      )}
    >
      <div>
        <p className={getTypographyClassName("bodyMd")}>
          Báo giá #{quotationId} đã được tạo nhưng chưa gắn bảng dự toán này.
        </p>
        {error ? (
          <p className={cn(getTypographyClassName("caption"), "mt-1 text-amber-900")}>
            {error}
          </p>
        ) : null}
      </div>
      <button
        type="button"
        disabled={pending}
        onClick={() => void retry()}
        className={cn(
          getTypographyClassName("buttonPrimary"),
          "inline-flex min-h-11 items-center gap-2 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-4 !text-white shadow-sm transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60 cursor-pointer",
        )}
      >
        <RefreshCw size={16} className={pending ? "animate-spin" : ""} aria-hidden="true" />
        <span>{pending ? "Đang thử gắn lại…" : "Thử gắn lại (Retry Attach)"}</span>
      </button>
    </section>
  );
}
