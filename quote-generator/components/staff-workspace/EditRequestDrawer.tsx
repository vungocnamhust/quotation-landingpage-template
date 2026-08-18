"use client";

import { useEffect } from "react";
import { X, Save, Sparkles, AlertCircle } from "lucide-react";
import QuoteRequestForm from "../quotation-workspace/QuoteRequestForm";
import BasicItineraryDayGrid from "../quotation-workspace/BasicItineraryDayGrid";
import { useQuoteRequestForm } from "../quotation-workspace/useQuoteRequestForm";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";
import type { QuoteRequestItem } from "../quotation-workspace/factsTypes";

type Props = {
  request: QuoteRequestItem;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (updated: QuoteRequestItem) => void;
};

function EditRequestDrawerContent({
  request,
  onClose,
  onSuccess,
}: {
  request: QuoteRequestItem;
  onClose: () => void;
  onSuccess: (updated: QuoteRequestItem) => void;
}) {
  const {
    formState,
    setFormState,
    itineraryDays,
    setItineraryDays,
    changeSummary,
    setChangeSummary,
    submitting,
    errorMsg,
    handleSubmit,
    nextRevision,
  } = useQuoteRequestForm({
    initialRequest: request,
    onSuccess: (updated) => {
      onSuccess(updated);
      onClose();
    },
  });

  // Lock body scroll when drawer is mounted
  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "unset";
    };
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs transition-opacity duration-300">
      <div
        className="relative flex h-full w-full max-w-4xl flex-col bg-[var(--color-surface)] shadow-2xl transition-transform duration-300"
        role="dialog"
        aria-modal="true"
        aria-labelledby="edit-request-heading"
      >
        {/* Header Bar */}
        <div className="sticky top-0 z-20 flex items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-surface)]/95 px-6 py-4 backdrop-blur-md">
          <div className="flex flex-col gap-0.5">
            <div className="flex items-center gap-2">
              <h2
                id="edit-request-heading"
                className={cn(getTypographyClassName("pageTitle"), "text-[var(--color-on-surface)]")}
              >
                Edit Request
              </h2>
              <span className={cn(getTypographyClassName("caption"), "rounded-full bg-amber-50 px-2.5 py-0.5 text-amber-700 border border-amber-200")}>
                Saving will create Revision #{nextRevision}
              </span>
            </div>
            <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
              Request ID: {request.id} • Current Revision: v{request.current_revision || 1}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="rounded-full p-2 text-[var(--color-muted)] hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-on-surface)] transition-colors cursor-pointer"
              aria-label="Close edit drawer"
            >
              <X size={20} aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* Scrollable Form Content */}
        <form onSubmit={handleSubmit} className="flex flex-1 flex-col overflow-y-auto p-6 gap-6">
          {errorMsg ? (
            <div className="flex items-center gap-2 rounded-[var(--radius-card)] border border-rose-200 bg-rose-50 p-4 text-rose-700">
              <AlertCircle size={18} className="shrink-0" aria-hidden="true" />
              <span className={cn(getTypographyClassName("bodySm"))}>{errorMsg}</span>
            </div>
          ) : null}

          {/* Revision Note / Change Reason Box */}
          <section className="flex flex-col gap-2 rounded-[var(--radius-card)] border border-amber-200 bg-amber-50/50 p-4">
            <label htmlFor="change-summary-input" className="flex flex-col gap-1.5">
              <span className={cn(getTypographyClassName("label"), "text-amber-900")}>
                Revision Note / Lý do thay đổi (Optional)
              </span>
              <input
                id="change-summary-input"
                type="text"
                disabled={submitting}
                placeholder="e.g. Dời ngày khởi hành sang tháng 11, thêm 2 người lớn, đổi sang khách sạn 5 sao..."
                value={changeSummary}
                onChange={(e) => setChangeSummary(e.target.value)}
                className={cn(
                  getTypographyClassName("bodyMd"),
                  "min-h-10 w-full rounded-[var(--radius-button)] border border-amber-300 bg-white px-3 text-[var(--color-on-surface)] placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-amber-500"
                )}
              />
            </label>
            <p className={cn(getTypographyClassName("caption"), "text-amber-700")}>
              Ghi chú này sẽ được lưu vào timeline lịch sử version để đối chiếu sau này.
            </p>
          </section>

          {/* 1. Request Details Form */}
          <QuoteRequestForm state={formState} onChange={setFormState} disabled={submitting} />

          {/* 2. Basic Daily Itinerary Schedule */}
          <BasicItineraryDayGrid
            days={itineraryDays}
            startDate={formState.arrival_date}
            onChange={setItineraryDays}
          />


          {/* Bottom Action Bar */}
          <div className="sticky bottom-0 -mx-6 -mb-6 mt-4 flex items-center justify-between border-t border-[var(--color-border)] bg-[var(--color-surface)]/95 px-6 py-4 backdrop-blur-md">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className={cn(
                getTypographyClassName("buttonSecondary"),
                "rounded-[var(--radius-button)] border border-[var(--color-border)] px-4 py-2.5 text-[var(--color-on-surface)] hover:bg-[var(--color-surface-muted)] cursor-pointer"
              )}
            >
              Cancel
            </button>

            <button
              type="submit"
              disabled={submitting}
              className={cn(
                getTypographyClassName("buttonPrimary"),
                "flex items-center gap-2 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-6 py-2.5 text-white shadow-md transition-all hover:opacity-90 disabled:opacity-50 cursor-pointer"
              )}
            >
              {submitting ? (
                <>
                  <Sparkles size={16} className="animate-spin" aria-hidden="true" />
                  <span>Saving Revision #{nextRevision}...</span>
                </>
              ) : (
                <>
                  <Save size={16} aria-hidden="true" />
                  <span>Save Changes (Create v{nextRevision})</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function EditRequestDrawer({
  request,
  isOpen,
  onClose,
  onSuccess,
}: Props) {
  if (!isOpen) return null;

  return (
    <EditRequestDrawerContent
      key={`${request.id}-${request.current_revision || 1}`}
      request={request}
      onClose={onClose}
      onSuccess={onSuccess}
    />
  );
}
