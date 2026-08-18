"use client";

import { DollarSign, Users } from "lucide-react";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";
import CustomSelect from "../ui/CustomSelect";
import {
  applyChildPresetRatio,
  calculateTriPricing,
  inferRatesFromGroupTotal,
} from "../../lib/rules/pricingRules";
import {
  CURRENCY_OPTIONS,
  formatMinorAmount,
  minorAmountFromInput,
  minorAmountToInput,
} from "./factsTypes";

type Props = {
  label: string;
  currency: string;
  perAdultMinor: number | null;
  perChildMinor: number | null;
  groupTotalMinor: number | null;
  adults: number;
  childrenCount: number;
  lang?: string;
  onChange: (patch: {
    label?: string;
    currency?: string;
    perAdultMinor?: number | null;
    perChildMinor?: number | null;
    groupTotalMinor?: number | null;
  }) => void;
};

const inputClass = cn(
  getTypographyClassName("bodyMd"),
  "min-h-11 w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
);

export default function TriPricingSection({
  label,
  currency,
  perAdultMinor,
  perChildMinor,
  groupTotalMinor,
  adults,
  childrenCount,
  lang = "en",
  onChange,
}: Props) {
  const safeAdults = Math.max(adults || 2, 1);
  const safeChildren = Math.max(childrenCount || 0, 0);

  const handleAdultChange = (valStr: string) => {
    const minor = minorAmountFromInput(valStr, currency);
    const newTotal = calculateTriPricing(minor, perChildMinor, safeAdults, safeChildren);
    onChange({
      perAdultMinor: minor,
      groupTotalMinor: newTotal,
    });
  };

  const handleChildChange = (valStr: string) => {
    const minor = minorAmountFromInput(valStr, currency);
    const newTotal = calculateTriPricing(perAdultMinor, minor, safeAdults, safeChildren);
    onChange({
      perChildMinor: minor,
      groupTotalMinor: newTotal,
    });
  };

  const handleChildPreset = (ratio: number) => {
    const childMinor = applyChildPresetRatio(perAdultMinor, ratio);
    const newTotal = calculateTriPricing(perAdultMinor, childMinor, safeAdults, safeChildren);
    onChange({
      perChildMinor: childMinor,
      groupTotalMinor: newTotal,
    });
  };

  const handleTotalChange = (valStr: string) => {
    const totalMinor = minorAmountFromInput(valStr, currency);
    if (totalMinor === null) {
      onChange({ groupTotalMinor: null });
      return;
    }
    const currentChildRatio =
      perAdultMinor && perChildMinor !== null ? perChildMinor / perAdultMinor : 0.75;
    const { perAdultMinor: adultMinor, perChildMinor: childMinor } = inferRatesFromGroupTotal(
      totalMinor,
      safeAdults,
      safeChildren,
      currentChildRatio
    );
    onChange({
      perAdultMinor: adultMinor,
      perChildMinor: childMinor,
      groupTotalMinor: totalMinor,
    });
  };

  const adultDisplay = minorAmountToInput(perAdultMinor, currency);
  const childDisplay = minorAmountToInput(perChildMinor, currency);
  const totalDisplay = minorAmountToInput(groupTotalMinor, currency);

  return (
    <div className="flex flex-col gap-4 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] p-4 shadow-2xs">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border)] pb-2.5">
        <div className="flex items-center gap-2">
          <DollarSign size={16} className="text-[var(--color-accent)]" aria-hidden="true" />
          <h3 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
            Commercial Pricing (3 Parameters)
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
            Party: {safeAdults} Adults{safeChildren > 0 ? `, ${safeChildren} Children` : ""}
          </span>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {/* Option Label */}
        <label className="flex flex-col gap-1.5 sm:col-span-2">
          <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
            Package Label
          </span>
          <input
            className={inputClass}
            value={label}
            placeholder="e.g. Standard Luxury Option"
            onChange={(e) => onChange({ label: e.target.value })}
          />
        </label>

        {/* Currency */}
        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
            Currency
          </span>
          <CustomSelect
            value={currency}
            placeholder="Select currency"
            options={CURRENCY_OPTIONS}
            onChange={(curr) => onChange({ currency: curr })}
          />
        </div>

        {/* Price Per Adult */}
        <label className="flex flex-col gap-1.5">
          <span className={cn(getTypographyClassName("label"), "flex justify-between text-[var(--color-muted)]")}>
            <span>Price / Adult</span>
            <span className={cn(getTypographyClassName("caption"), "text-[var(--color-accent)]")}>
              Required
            </span>
          </span>
          <div className="relative">
            <input
              type="number"
              min={0}
              className={inputClass}
              value={adultDisplay}
              placeholder="e.g. 4000"
              onChange={(e) => handleAdultChange(e.target.value)}
            />
          </div>
        </label>

        {/* Price Per Child */}
        <div className={cn("flex flex-col gap-1.5", safeChildren === 0 ? "opacity-40" : "")}>
          <span className={cn(getTypographyClassName("label"), "flex justify-between text-[var(--color-muted)]")}>
            <span>Price / Child</span>
            <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
              {safeChildren > 0 ? "Optional" : "No kids"}
            </span>
          </span>
          <input
            type="number"
            min={0}
            disabled={safeChildren === 0}
            className={inputClass}
            value={safeChildren > 0 ? childDisplay : ""}
            placeholder={safeChildren > 0 ? "e.g. 2500" : "N/A"}
            onChange={(e) => handleChildChange(e.target.value)}
          />
          {safeChildren > 0 ? (
            <div className="flex flex-wrap gap-1 mt-0.5">
              <button
                type="button"
                onClick={() => handleChildPreset(0.5)}
                className={cn(
                  getTypographyClassName("caption"),
                  "rounded px-1.5 py-0.5 border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-muted)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] transition-colors"
                )}
              >
                50%
              </button>
              <button
                type="button"
                onClick={() => handleChildPreset(0.75)}
                className={cn(
                  getTypographyClassName("caption"),
                  "rounded px-1.5 py-0.5 border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-muted)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] transition-colors"
                )}
              >
                75% (Std)
              </button>
              <button
                type="button"
                onClick={() => handleChildPreset(1.0)}
                className={cn(
                  getTypographyClassName("caption"),
                  "rounded px-1.5 py-0.5 border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-muted)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] transition-colors"
                )}
              >
                100%
              </button>
              <button
                type="button"
                onClick={() => handleChildPreset(0)}
                className={cn(
                  getTypographyClassName("caption"),
                  "rounded px-1.5 py-0.5 border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-muted)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] transition-colors"
                )}
              >
                0$ (Free)
              </button>
            </div>
          ) : null}
        </div>

        {/* Group Total */}
        <label className="flex flex-col gap-1.5 sm:col-span-2">
          <span className={cn(getTypographyClassName("label"), "flex justify-between text-[var(--color-muted)]")}>
            <span className="text-[var(--color-on-surface)]">Group Total Price</span>
            <span className={cn(getTypographyClassName("caption"), "text-[var(--color-accent)]")}>
              Auto-Calculated
            </span>
          </span>
          <input
            type="number"
            min={0}
            className={cn(
              inputClass,
              "bg-[var(--color-surface)] text-[var(--color-on-surface)] border-[var(--color-accent)]"
            )}
            value={totalDisplay}
            placeholder="e.g. 10500"
            onChange={(e) => handleTotalChange(e.target.value)}
          />
        </label>
      </div>

      {/* Breakdown Explanation */}
      <div className="flex items-center gap-2 rounded-[var(--radius-button)] bg-[var(--color-surface)] p-2.5 text-[var(--color-muted)] border border-[var(--color-border)]">
        <Users size={14} className="shrink-0 text-[var(--color-accent)]" aria-hidden="true" />
        <p className={cn(getTypographyClassName("caption"), "text-[var(--color-on-surface)]")}>
          {safeChildren > 0 ? (
            <>
              Breakdown:{" "}
              <strong>
                {safeAdults} Adults x {formatMinorAmount(perAdultMinor, currency, lang)}
              </strong>{" "}
              +{" "}
              <strong>
                {safeChildren} Children x {formatMinorAmount(perChildMinor, currency, lang)}
              </strong>{" "}
              ={" "}
              <strong className="text-emerald-700">
                {formatMinorAmount(groupTotalMinor, currency, lang)} Total
              </strong>
            </>
          ) : (
            <>
              Breakdown:{" "}
              <strong>
                {safeAdults} Adults x {formatMinorAmount(perAdultMinor, currency, lang)}
              </strong>{" "}
              ={" "}
              <strong className="text-emerald-700">
                {formatMinorAmount(groupTotalMinor, currency, lang)} Total
              </strong>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
