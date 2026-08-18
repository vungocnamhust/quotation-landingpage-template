"use client";

import { useState } from "react";
import { CircleDollarSign, ChevronDown, ChevronUp } from "lucide-react";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";
import CustomSelect from "../ui/CustomSelect";
import { CURRENCY_OPTIONS } from "./factsTypes";

export type CommercialPricingState = {
  budget: number | "";
  budget_basis: string;
  currency: string;
  pricing_type: string;
  commission: number | "";
  show_commission: string;
  price_display: string;
  target_gp: number | "";
  minimum_gp: number | "";
  contingency: number | "";
  payment_fee: number | "";
  tax_treatment: string;
  discount_cap: string;
  quote_validity: string;
  payment_terms: string;
};

type Props = {
  state: CommercialPricingState;
  isB2B: boolean;
  onChange: (updater: (prev: CommercialPricingState) => CommercialPricingState) => void;
  disabled?: boolean;
};

const BUDGET_BASIS_OPTIONS = [
  "Total trip",
  "Per person",
  "Per person / day",
  "Per room",
  "Target selling price",
  "Net budget",
];

const PRICING_TYPES = ["Gross", "Net", "Commissionable"];

const VALIDITY_PRESETS = [
  "7 days from issue",
  "14 days from issue",
  "30 days from issue",
  "Subject to hotel availability",
];


const SHOW_COMMISSION_OPTIONS = [
  "No",
  "Yes — separate line",
  "Yes — embedded in gross price",
];

const PRICE_DISPLAY_OPTIONS = [
  "Total journey price",
  "Per person",
  "Per person sharing",
  "By room category",
  "Multiple options / tiers",
];

const inputClass = cn(
  getTypographyClassName("bodyMd"),
  "min-h-11 w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
);

export default function CommercialPricingSection({
  state,
  isB2B,
  onChange,
  disabled = false,
}: Props) {
  const [isOpen, setIsOpen] = useState(false);

  const hasData =
    Boolean(state.budget) ||
    Boolean(state.budget_basis) ||
    Boolean(state.pricing_type) ||
    (isB2B && Boolean(state.commission)) ||
    Boolean(state.target_gp);

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
            <CircleDollarSign size={18} aria-hidden="true" />
          </div>
          <div>
            <h3 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)] flex items-center gap-2")}>
              <span>Commercial & Pricing Parameters</span>
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
              Internal commercial setup: Budget, currency, gross margin % & advisor commission.
            </p>
          </div>
        </div>
        <div className="text-[var(--color-muted)]">
          {isOpen ? <ChevronUp size={20} aria-hidden="true" /> : <ChevronDown size={20} aria-hidden="true" />}
        </div>
      </button>

      {isOpen ? (
        <div className="flex flex-col gap-5 border-t border-[var(--color-border)] p-5">
          <div className="grid gap-4 sm:grid-cols-3">
            <label className="flex flex-col gap-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Budget Amount
              </span>
              <input
                type="number"
                min={0}
                step="any"
                disabled={disabled}
                placeholder="e.g. 8500"
                value={state.budget}
                onChange={(e) =>
                  onChange((prev) => ({
                    ...prev,
                    budget: e.target.value === "" ? "" : Number(e.target.value),
                  }))
                }
                className={inputClass}
              />
            </label>

            <label className="flex flex-col gap-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Budget Basis
              </span>
              <CustomSelect
                options={BUDGET_BASIS_OPTIONS.map((b) => ({ id: b, label: b }))}
                value={state.budget_basis}
                onChange={(val) => onChange((prev) => ({ ...prev, budget_basis: val }))}
                placeholder="Select budget basis"
              />
            </label>

            <label className="flex flex-col gap-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Quote Currency
              </span>
              <CustomSelect
                options={CURRENCY_OPTIONS}
                value={state.currency || "USD"}
                onChange={(val) => onChange((prev) => ({ ...prev, currency: val }))}
                placeholder="Select currency"
              />
            </label>

            <label className="flex flex-col gap-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Pricing Type
              </span>
              <CustomSelect
                options={PRICING_TYPES.map((p) => ({ id: p, label: p }))}
                value={state.pricing_type}
                onChange={(val) => onChange((prev) => ({ ...prev, pricing_type: val }))}
                placeholder="Select pricing type"
              />
            </label>

            <label className="flex flex-col gap-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Price Display Style
              </span>
              <CustomSelect
                options={PRICE_DISPLAY_OPTIONS.map((p) => ({ id: p, label: p }))}
                value={state.price_display || "Total journey price"}
                onChange={(val) => onChange((prev) => ({ ...prev, price_display: val }))}
                placeholder="Select display style"
              />
            </label>

            {isB2B ? (
              <>
                <label className="flex flex-col gap-2 rounded-[var(--radius-button)] border-l-2 border-[var(--color-accent)] pl-2">
                  <span className={cn(getTypographyClassName("label"), "text-[var(--color-accent)]")}>
                    Advisor Commission % (B2B)
                  </span>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    step={0.1}
                    disabled={disabled}
                    placeholder="e.g. 10.0"
                    value={state.commission}
                    onChange={(e) =>
                      onChange((prev) => ({
                        ...prev,
                        commission: e.target.value === "" ? "" : Number(e.target.value),
                      }))
                    }
                    className={inputClass}
                  />
                </label>

                <label className="flex flex-col gap-2 rounded-[var(--radius-button)] border-l-2 border-[var(--color-accent)] pl-2">
                  <span className={cn(getTypographyClassName("label"), "text-[var(--color-accent)]")}>
                    Show Advisor Commission? (B2B)
                  </span>
                  <CustomSelect
                    options={SHOW_COMMISSION_OPTIONS.map((c) => ({ id: c, label: c }))}
                    value={state.show_commission || "No"}
                    onChange={(val) => onChange((prev) => ({ ...prev, show_commission: val }))}
                    placeholder="Show commission in quote"
                  />
                </label>
              </>
            ) : null}

            <label className="flex flex-col gap-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Target GP %
              </span>
              <input
                type="number"
                min={0}
                max={100}
                step={0.1}
                disabled={disabled}
                placeholder="e.g. 25.0"
                value={state.target_gp}
                onChange={(e) =>
                  onChange((prev) => ({
                    ...prev,
                    target_gp: e.target.value === "" ? "" : Number(e.target.value),
                  }))
                }
                className={inputClass}
              />
            </label>

            <label className="flex flex-col gap-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Contingency / Buffer %
              </span>
              <input
                type="number"
                min={0}
                max={100}
                step={0.1}
                disabled={disabled}
                placeholder="e.g. 3.0"
                value={state.contingency}
                onChange={(e) =>
                  onChange((prev) => ({
                    ...prev,
                    contingency: e.target.value === "" ? "" : Number(e.target.value),
                  }))
                }
                className={inputClass}
              />
            </label>

            <div className="flex flex-col gap-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Quote Validity
              </span>
              <div className="flex flex-wrap gap-1">
                {VALIDITY_PRESETS.map((preset) => (
                  <button
                    key={preset}
                    type="button"
                    disabled={disabled}
                    onClick={() => onChange((prev) => ({ ...prev, quote_validity: preset }))}
                    className={cn(
                      getTypographyClassName("caption"),
                      "rounded-md border px-2 py-0.5 transition-all cursor-pointer",
                      state.quote_validity === preset
                        ? "border-[var(--color-accent)] bg-[var(--color-accent-wash)] text-[var(--color-accent)]"
                        : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-muted)] hover:text-[var(--color-on-surface)]"

                    )}
                  >
                    {preset}
                  </button>
                ))}
              </div>
              <input
                type="text"
                disabled={disabled}
                placeholder="e.g. 14 days from issue / 30 Nov 2026..."
                value={state.quote_validity}
                onChange={(e) => onChange((prev) => ({ ...prev, quote_validity: e.target.value }))}
                className={inputClass}
              />
            </div>


            <label className="flex flex-col gap-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Tax / VAT Treatment
              </span>
              <input
                type="text"
                disabled={disabled}
                placeholder="e.g. Included / Excluded / By market"
                value={state.tax_treatment}
                onChange={(e) => onChange((prev) => ({ ...prev, tax_treatment: e.target.value }))}
                className={inputClass}
              />
            </label>

            <label className="flex flex-col gap-2 sm:col-span-3">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Payment & Cancellation Terms to Quote
              </span>
              <textarea
                rows={2}
                disabled={disabled}
                placeholder="Deposit %, balance due date, cancellation schedule, non-refundable suppliers..."
                value={state.payment_terms}
                onChange={(e) => onChange((prev) => ({ ...prev, payment_terms: e.target.value }))}
                className={cn(
                  getTypographyClassName("bodyMd"),
                  "w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-3 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
                )}
              />
            </label>
          </div>
        </div>
      ) : null}
    </div>
  );
}
