"use client";

import { useState } from "react";
import { CheckSquare, ChevronDown, ChevronUp } from "lucide-react";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";
import CustomSelect from "../ui/CustomSelect";

export type ReadinessAndStrategyState = {
  // Costing Readiness
  existing_template: string;
  rates_available: string;
  rfq_required: string;
  rate_risk: string;
  preferred_suppliers: string;
  missing_info: string;

  // Sales Strategy
  journey_direction: string;
  selling_angle: string;
  competitor: string;
  internal_notes: string;
};

type Props = {
  state: ReadinessAndStrategyState;
  onChange: (updater: (prev: ReadinessAndStrategyState) => ReadinessAndStrategyState) => void;
  disabled?: boolean;
};

const TEMPLATE_OPTIONS = ["Yes", "No", "Partial"];
const RATES_OPTIONS = ["Yes", "No", "Partial", "Need reconfirmation"];
const RFQ_OPTIONS = [
  "No",
  "Yes — hotel",
  "Yes — experiences",
  "Yes — transport",
  "Yes — multiple services",
];

const inputClass = cn(
  getTypographyClassName("bodyMd"),
  "min-h-11 w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
);

export default function ReadinessAndStrategySection({
  state,
  onChange,
  disabled = false,
}: Props) {
  const [isOpen, setIsOpen] = useState(false);

  const hasData =
    Boolean(state.rfq_required) ||
    Boolean(state.rate_risk) ||
    Boolean(state.preferred_suppliers) ||
    Boolean(state.missing_info) ||
    Boolean(state.selling_angle);

  return (
    <div className="flex flex-col rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] shadow-[var(--elevation-card)] transition-all">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between gap-3 p-5 text-left transition-colors hover:bg-[var(--color-surface-muted)] cursor-pointer disabled:cursor-not-allowed"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--color-surface-muted)] text-[var(--color-accent)]">
            <CheckSquare size={18} aria-hidden="true" />
          </div>
          <div>
            <h3 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)] flex items-center gap-2")}>
              <span>Costing Readiness & Sales Strategy</span>
              <span
                className={cn(
                  getTypographyClassName("caption"),
                  "rounded-full px-2 py-0.5 border",
                  hasData
                    ? "bg-[var(--color-accent-wash)] text-[var(--color-accent)] border-[var(--color-accent)]"
                    : "bg-[var(--color-surface-muted)] text-[var(--color-muted)] border-[var(--color-border)]"
                )}
              >
                {hasData ? "Specified" : "Optional"}
              </span>
            </h3>
            <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>
              Assess supplier RFQs, peak season risks, USP angles and internal strategy notes.
            </p>
          </div>
        </div>
        <div className="text-[var(--color-muted)]">
          {isOpen ? <ChevronUp size={20} aria-hidden="true" /> : <ChevronDown size={20} aria-hidden="true" />}
        </div>
      </button>

      {isOpen ? (
        <div className="flex flex-col gap-6 border-t border-[var(--color-border)] p-5">
          {/* Costing Readiness */}
          <div className="flex flex-col gap-3">
            <h4 className={cn(getTypographyClassName("label"), "text-[var(--color-accent)]")}>
              Costing & Supplier Readiness
            </h4>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  Existing Template Available?
                </span>
                <CustomSelect
                  options={TEMPLATE_OPTIONS.map((t) => ({ id: t, label: t }))}
                  value={state.existing_template}
                  onChange={(val) => onChange((prev) => ({ ...prev, existing_template: val }))}
                  placeholder="Select template status"
                />
              </label>

              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  Supplier Rates Available?
                </span>
                <CustomSelect
                  options={RATES_OPTIONS.map((r) => ({ id: r, label: r }))}
                  value={state.rates_available}
                  onChange={(val) => onChange((prev) => ({ ...prev, rates_available: val }))}
                  placeholder="Select rates availability"
                />
              </label>

              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  Supplier RFQ Required?
                </span>
                <CustomSelect
                  options={RFQ_OPTIONS.map((q) => ({ id: q, label: q }))}
                  value={state.rfq_required}
                  onChange={(val) => onChange((prev) => ({ ...prev, rfq_required: val }))}
                  placeholder="Select RFQ requirement"
                />
              </label>

              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  Rate Season / Blackout Risk
                </span>
                <input
                  type="text"
                  disabled={disabled}
                  placeholder="Peak season, Tet holiday, festival surcharges..."
                  value={state.rate_risk}
                  onChange={(e) => onChange((prev) => ({ ...prev, rate_risk: e.target.value }))}
                  className={inputClass}
                />
              </label>

              <label className="flex flex-col gap-2 sm:col-span-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  Preferred / Required Suppliers
                </span>
                <textarea
                  rows={2}
                  disabled={disabled}
                  placeholder="Hotels, guides, DMC partners, experience providers or transport companies to prioritize or avoid..."
                  value={state.preferred_suppliers}
                  onChange={(e) => onChange((prev) => ({ ...prev, preferred_suppliers: e.target.value }))}
                  className={cn(
                    getTypographyClassName("bodyMd"),
                    "w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-3 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
                  )}
                />
              </label>

              <label className="flex flex-col gap-2 sm:col-span-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-accent)]")}>
                  Missing Information Before Costing (Blockers)
                </span>
                <textarea
                  rows={2}
                  disabled={disabled}
                  placeholder="List any missing inputs that currently prevent accurate pricing calculation..."
                  value={state.missing_info}
                  onChange={(e) => onChange((prev) => ({ ...prev, missing_info: e.target.value }))}
                  className={cn(
                    getTypographyClassName("bodyMd"),
                    "w-full rounded-[var(--radius-button)] border border-dashed border-[var(--color-accent)] bg-[var(--color-accent-wash)]/20 p-3 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
                  )}
                />
              </label>
            </div>
          </div>

          <hr className="border-[var(--color-border)]" />

          {/* Sales Strategy */}
          <div className="flex flex-col gap-3">
            <h4 className={cn(getTypographyClassName("label"), "text-[var(--color-accent)]")}>
              Sales Strategy & USP
            </h4>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="flex flex-col gap-2 sm:col-span-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  Recommended Journey Direction & Concept
                </span>
                <textarea
                  rows={2}
                  disabled={disabled}
                  placeholder="Key itinerary narrative, thematic focus, exclusive access proposals..."
                  value={state.journey_direction}
                  onChange={(e) => onChange((prev) => ({ ...prev, journey_direction: e.target.value }))}
                  className={cn(
                    getTypographyClassName("bodyMd"),
                    "w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-3 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
                  )}
                />
              </label>

              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  Key Selling Angle (USP)
                </span>
                <textarea
                  rows={2}
                  disabled={disabled}
                  placeholder="Unique value proposition that wins this deal..."
                  value={state.selling_angle}
                  onChange={(e) => onChange((prev) => ({ ...prev, selling_angle: e.target.value }))}
                  className={cn(
                    getTypographyClassName("bodyMd"),
                    "w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-3 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
                  )}
                />
              </label>

              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  Competitor / Alternative Quote Notes
                </span>
                <textarea
                  rows={2}
                  disabled={disabled}
                  placeholder="Other competing agencies or routes the client is considering..."
                  value={state.competitor}
                  onChange={(e) => onChange((prev) => ({ ...prev, competitor: e.target.value }))}
                  className={cn(
                    getTypographyClassName("bodyMd"),
                    "w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-3 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
                  )}
                />
              </label>

              <label className="flex flex-col gap-2 sm:col-span-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  Internal Strategy Notes
                </span>
                <textarea
                  rows={2}
                  disabled={disabled}
                  placeholder="Private internal notes for team review..."
                  value={state.internal_notes}
                  onChange={(e) => onChange((prev) => ({ ...prev, internal_notes: e.target.value }))}
                  className={cn(
                    getTypographyClassName("bodyMd"),
                    "w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-3 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
                  )}
                />
              </label>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
