"use client";

import { use, useMemo } from "react";
import { ArrowLeft, FileOutput } from "lucide-react";
import { useRequestDetail } from "../../../../../components/staff-workspace/useRequestDetail";
import { useWorkspaceNavigation, WorkspaceNavigationLink } from "../../../../../components/staff-workspace/WorkspaceNavigation";
import { CostingWorkbench } from "../../../../../components/quotation-costing/CostingWorkbench.tsx";
import type { DraftDaySpec } from "../../../../../components/quotation-costing/types.ts";
import { dateForItineraryDay } from "../../../../../lib/rules/datesRules.ts";
import { getTypographyClassName } from "../../../../../config/typography";
import { cn } from "../../../../../utils/cn";
import { HelpTooltip } from "../../../../../components/ui/tooltip/index.ts";

type Props = {
  params: Promise<{ id: string }>;
};

// Mirrors schemas/v2/quote_request.py BasicItineraryDayInputSchema — the request payload's
// raw itinerary shape, before it is hydrated into a QuotationFacts trip.
type RequestItineraryDay = {
  day_number?: number | null;
  destination_ref_id?: string | null;
};

/** Day -> destination/date anchors for the AI Service Drafter (15.7) — derived from the same
 * request payload this page already recaps above, not rebuilt server-side (routers/v2/ai_drafter.py
 * deliberately stays out of the facts/itinerary pipeline). */
function deriveAiDrafterDays(
  startDate: string | null | undefined,
  itineraryDays: unknown
): DraftDaySpec[] | undefined {
  if (!Array.isArray(itineraryDays)) return undefined;
  const days = (itineraryDays as RequestItineraryDay[]).reduce<DraftDaySpec[]>((acc, day, index) => {
    const dayNumber = day.day_number ?? index + 1;
    const destinationId = day.destination_ref_id;
    const serviceDate = dateForItineraryDay(startDate, dayNumber);
    if (destinationId && serviceDate) {
      acc.push({ dayNumber, destinationId, serviceDate });
    }
    return acc;
  }, []);
  return days.length > 0 ? days : undefined;
}

/**
 * Flow 1 (Costing-First) host — request-anchored CostingWorkbench. Read-only
 * recap of the request; all editing happens in the workbench grid below. The
 * "Tạo báo giá từ dự toán" CTA hands the sheet id to the intake screen, which
 * runs the one-shot handoff into facts before generating the quotation (15.4 §3).
 */
export default function RequestCostingPage({ params }: Props) {
  const { id } = use(params);
  const { request, error, isLoading } = useRequestDetail(id);
  const { push } = useWorkspaceNavigation();
  const aiDrafterDays = useMemo(
    () => deriveAiDrafterDays(request?.start_date, request?.payload_json?.itinerary_days),
    [request?.start_date, request?.payload_json]
  );

  return (
    <div className="flex flex-col gap-6 pb-16">
      <WorkspaceNavigationLink
        href={`/workspace/requests/${id}`}
        className={cn(getTypographyClassName("buttonSecondary"), "flex w-fit items-center gap-1.5 text-[var(--color-muted)] hover:text-[var(--color-on-surface)]")}
      >
        <ArrowLeft size={15} aria-hidden="true" />
        <span>Back to request</span>
      </WorkspaceNavigationLink>

      {isLoading ? (
        <div className="h-16 animate-pulse rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)]" />
      ) : error || !request ? (
        <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
          <p className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-accent)]")}>
            {error || `Request ${id} could not be found.`}
          </p>
        </div>
      ) : (
        <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <h1 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
            {request.customer_name || "Costing Workbench"}
          </h1>
          <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
            {(request.destinations ?? []).join(" → ") || "No destinations yet"}
            {request.start_date ? ` · ${request.start_date} → ${request.end_date ?? ""}` : ""}
          </p>
        </div>
      )}

      <CostingWorkbench
        anchor={{ requestId: id }}
        aiDrafterDays={aiDrafterDays}
        headerAction={(sheetId) => (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => push(`/workspace/quotations/new?requestId=${id}&costingSheetId=${sheetId}`)}
              className={cn(
                getTypographyClassName("buttonPrimary"),
                "flex items-center gap-2 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-5 py-2.5 text-white shadow-md transition-all hover:opacity-90 cursor-pointer",
              )}
            >
              <FileOutput size={16} aria-hidden="true" />
              <span>Tạo báo giá từ dự toán</span>
            </button>
            <HelpTooltip conceptKey="CREATE_QUOTATION_CTA" size="md" />
          </div>
        )}
      />
    </div>
  );
}
