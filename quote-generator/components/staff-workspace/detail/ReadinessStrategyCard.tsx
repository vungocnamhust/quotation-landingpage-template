"use client";

import { Target, AlertTriangle, Lightbulb, FileText, CheckCircle2, ShieldAlert } from "lucide-react";
import DetailSectionCard from "./DetailSectionCard";
import DetailField from "./DetailField";
import { getTypographyClassName } from "../../../config/typography";
import { cn } from "../../../utils/cn";

type Props = {
  existingTemplate?: string | null;
  ratesAvailable?: string | null;
  rfqRequired?: string | null;
  rateRisk?: string | null;
  preferredSuppliers?: string | null;
  missingInfo?: string | null;
  journeyDirection?: string | null;
  sellingAngle?: string | null;
  competitor?: string | null;
  internalNotes?: string | null;
};

export default function ReadinessStrategyCard({
  existingTemplate,
  ratesAvailable,
  rfqRequired,
  rateRisk,
  preferredSuppliers,
  missingInfo,
  journeyDirection,
  sellingAngle,
  competitor,
  internalNotes,
}: Props) {
  return (
    <DetailSectionCard
      title="Quotation Readiness & Sales Strategy"
      subtitle="Operational feasibility, supplier RFQs, selling angle & internal strategy notes"
      icon={<Target size={18} aria-hidden="true" />}
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <DetailField
          label="Base Route / Master Template"
          value={existingTemplate}
          emptyFallback="Custom tailor-made itinerary"
          icon={<CheckCircle2 size={13} aria-hidden="true" />}
        />

        <DetailField
          label="Supplier Rates Availability"
          value={ratesAvailable || "Live contract rates available"}
        />

        <DetailField
          label="Custom RFQ Required?"
          value={rfqRequired || "No (Standard catalog rates)"}
          badge={Boolean(rfqRequired && rfqRequired !== "No")}
          badgeVariant="warning"
        />

        <DetailField
          label="Rate & Season Risk"
          value={rateRisk}
          icon={<ShieldAlert size={13} aria-hidden="true" />}
          emptyFallback="Standard contract rates apply"
        />

        <DetailField
          label="Preferred Supplier / DMC"
          value={preferredSuppliers}
          emptyFallback="Direct contracted properties"
        />

        <DetailField
          label="Competitor Information"
          value={competitor}
          emptyFallback="None identified"
        />
      </div>

      {missingInfo ? (
        <div className="rounded-[var(--radius-card)] border border-rose-300 bg-rose-50 p-3.5">
          <span className={cn(getTypographyClassName("label"), "text-rose-800 flex items-center gap-1.5 mb-1")}>
            <AlertTriangle size={14} className="text-rose-600" aria-hidden="true" />
            <span>Missing Information / Quotation Blockers</span>
          </span>
          <p className={cn(getTypographyClassName("bodySm"), "text-rose-950 whitespace-pre-wrap")}>{missingInfo}</p>
        </div>
      ) : null}

      {journeyDirection ? (
        <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3">
          <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)] block mb-1")}>
            Journey Concept & Architectural Direction
          </span>
          <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>{journeyDirection}</p>
        </div>
      ) : null}

      {sellingAngle ? (
        <div className="rounded-[var(--radius-card)] border border-emerald-200 bg-emerald-50/60 p-3">
          <span className={cn(getTypographyClassName("label"), "text-emerald-800 flex items-center gap-1.5 mb-1")}>
            <Lightbulb size={14} className="text-emerald-600" aria-hidden="true" />
            <span>Selling Angle & Unique Value Proposition (USP)</span>
          </span>
          <p className={cn(getTypographyClassName("bodySm"), "text-emerald-950")}>{sellingAngle}</p>
        </div>
      ) : null}

      {internalNotes ? (
        <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3.5">
          <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)] flex items-center gap-1.5 mb-1.5")}>
            <FileText size={13} aria-hidden="true" />
            <span>Confidential Internal Strategy Notes</span>
          </span>
          <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)] whitespace-pre-wrap")}>{internalNotes}</p>
        </div>
      ) : null}
    </DetailSectionCard>
  );
}
