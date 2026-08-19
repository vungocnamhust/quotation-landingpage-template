"use client";

import { useRouter } from "next/navigation";
import { ArrowLeft, Sparkles } from "lucide-react";
import Link from "next/link";
import QuoteRequestForm from "../../../../components/quotation-workspace/QuoteRequestForm";
import BasicItineraryDayGrid from "../../../../components/quotation-workspace/BasicItineraryDayGrid";
import { useQuoteRequestForm } from "../../../../components/quotation-workspace/useQuoteRequestForm";
import { getTypographyClassName } from "../../../../config/typography";
import { cn } from "../../../../utils/cn";

export default function NewQuoteRequestPage() {
  const router = useRouter();

  const {
    formState,
    setFormState,
    itineraryDays,
    setItineraryDays,
    addItineraryDay,
    removeItineraryDay,
    updateItineraryDay,
    submitting,
    errorMsg,
    handleSubmit,
  } = useQuoteRequestForm({
    initialRole: "traveller",
    onSuccess: (created) => {
      router.push(`/workspace/requests/${encodeURIComponent(created.id)}`);
    },
  });

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-6 pb-16">
      {/* Top Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)]">
        <div className="flex flex-col gap-1.5">
          <Link
            href="/workspace/requests"
            className={cn(
              getTypographyClassName("caption"),
              "flex items-center gap-1.5 text-[var(--color-muted)] hover:text-[var(--color-on-surface)] transition-colors"
            )}
          >
            <ArrowLeft size={14} aria-hidden="true" />
            <span>Back to Requests</span>
          </Link>
          <h1 className={cn(getTypographyClassName("pageTitle"), "text-[var(--color-on-surface)]")}>
            Create New Journey Request
          </h1>
        </div>

        <button
          type="submit"
          disabled={submitting}
          className={cn(
            getTypographyClassName("buttonPrimary"),
            "flex items-center gap-2 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-5 py-3 text-white shadow-md transition-all hover:opacity-90 disabled:opacity-50 cursor-pointer"
          )}
        >
          <Sparkles size={16} aria-hidden="true" />
          <span>{submitting ? "Saving Request..." : "Save Request"}</span>
        </button>
      </div>

      {errorMsg ? (
        <div className={cn(getTypographyClassName("bodySm"), "rounded-[var(--radius-card)] border border-red-200 bg-red-50 p-4 text-red-700")}>
          {errorMsg}
        </div>
      ) : null}

      {/* 1. Primary Request Information Form */}
      <QuoteRequestForm state={formState} onChange={setFormState} disabled={submitting} />

      {/* 2. Optional Basic Daily Itinerary Grid */}
      <BasicItineraryDayGrid
        days={itineraryDays}
        startDate={formState.arrival_date}
        onAddDay={addItineraryDay}
        onRemoveDay={removeItineraryDay}
        onUpdateDay={updateItineraryDay}
        onChange={setItineraryDays}
      />


      {/* Submit Button Bar */}
      <div className="flex items-center justify-end gap-3 border-t border-[var(--color-border)] pt-5">
        <Link
          href="/workspace/requests"
          className={cn(
            getTypographyClassName("buttonSecondary"),
            "rounded-[var(--radius-button)] border border-[var(--color-border)] px-4 py-2.5 text-[var(--color-on-surface)] hover:bg-[var(--color-surface-muted)]"
          )}
        >
          Cancel
        </Link>

        <button
          type="submit"
          disabled={submitting}
          className={cn(
            getTypographyClassName("buttonPrimary"),
            "flex items-center gap-2 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-6 py-2.5 text-white shadow-sm transition-all hover:opacity-90 disabled:opacity-50 cursor-pointer"
          )}
        >
          <Sparkles size={16} aria-hidden="true" />
          <span>{submitting ? "Saving Request..." : "Save Request"}</span>
        </button>
      </div>
    </form>
  );
}
