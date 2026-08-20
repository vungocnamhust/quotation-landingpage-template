"use client";

import { DollarSign, RefreshCw, Users } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import CustomSelect from "../ui/CustomSelect.tsx";
import {
  pricingReconciler,
  type CanonicalPricingOption,
} from "../../lib/rules/pricingReconciler.ts";
import { pricingAdapter } from "../../lib/rules/pricingAdapter.ts";
import {
  CURRENCY_OPTIONS,
  formatMinorAmount,
  minorAmountFromInput,
  minorAmountToInput,
} from "./factsTypes.ts";

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

  const currentOption: CanonicalPricingOption = pricingAdapter.fromTriPricing(
    { label, currency, perAdultMinor, perChildMinor, groupTotalMinor },
    safeAdults,
    safeChildren
  );

  const handleAdultChange = (valStr: string) => {
    const minor = minorAmountFromInput(valStr, currency);
    const updated = pricingReconciler.updateOptionPerAdult(
      currentOption,
      minor,
      safeAdults,
      safeChildren
    );
    onChange(pricingAdapter.toTriPricing(updated));
  };

  const handleChildChange = (valStr: string) => {
    const minor = minorAmountFromInput(valStr, currency);
    const updated = pricingReconciler.updateOptionPerChild(
      currentOption,
      minor,
      safeAdults,
      safeChildren
    );
    onChange(pricingAdapter.toTriPricing(updated));
  };

  const handleChildPreset = (ratio: number) => {
    const updated = pricingReconciler.applyChildPreset(
      currentOption,
      ratio,
      safeAdults,
      safeChildren
    );
    onChange(pricingAdapter.toTriPricing(updated));
  };

  const handleTotalChange = (valStr: string) => {
    const totalMinor = minorAmountFromInput(valStr, currency);
    const updated = pricingReconciler.updateOptionTotal(
      currentOption,
      totalMinor,
      safeAdults,
      safeChildren
    );
    onChange(pricingAdapter.toTriPricing(updated));
  };

  const handleCurrencyChange = (nextCurrency: string) => {
    // If the option already had numbers, convert amounts automatically using the exchange rate table
    const hasAmount = Boolean(perAdultMinor || groupTotalMinor);
    const updated = pricingReconciler.convertOptionCurrency(
      currentOption,
      nextCurrency,
      {
        convertAmounts: hasAmount,
        adults: safeAdults,
        children: safeChildren,
      }
    );
    onChange(pricingAdapter.toTriPricing(updated));
  };

  const adultDisplay = minorAmountToInput(perAdultMinor, currency);
  const childDisplay = minorAmountToInput(perChildMinor, currency);
  const totalDisplay = minorAmountToInput(groupTotalMinor, currency);

  // Exchange rate badge against USD
  const rateToUsd = pricingReconciler.getExchangeRate(currency, "USD");
  const rateFromUsd = pricingReconciler.getExchangeRate("USD", currency);
  const showRoeBadge = currency !== "USD";

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
          {showRoeBadge ? (
            <span
              className={cn(
                getTypographyClassName("caption"),
                "rounded bg-[var(--color-accent-wash)] px-2 py-0.5 text-[var(--color-accent)] border border-[var(--color-border)]"
              )}
              title="Reference exchange rate"
            >
              1 USD ≈ {rateFromUsd.toLocaleString()} {currency}
            </span>
          ) : null}
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
          <span className={cn(getTypographyClassName("label"), "flex justify-between text-[var(--color-muted)]")}>
            <span>Currency</span>
            {showRoeBadge ? (
              <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
                Auto-converts amounts
              </span>
            ) : null}
          </span>
          <CustomSelect
            value={currency}
            placeholder="Select currency"
            options={CURRENCY_OPTIONS}
            onChange={handleCurrencyChange}
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
                  "rounded px-1.5 py-0.5 border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-muted)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] transition-colors cursor-pointer"
                )}
              >
                50%
              </button>
              <button
                type="button"
                onClick={() => handleChildPreset(0.75)}
                className={cn(
                  getTypographyClassName("caption"),
                  "rounded px-1.5 py-0.5 border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-muted)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] transition-colors cursor-pointer"
                )}
              >
                75% (Std)
              </button>
              <button
                type="button"
                onClick={() => handleChildPreset(1.0)}
                className={cn(
                  getTypographyClassName("caption"),
                  "rounded px-1.5 py-0.5 border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-muted)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] transition-colors cursor-pointer"
                )}
              >
                100%
              </button>
              <button
                type="button"
                onClick={() => handleChildPreset(0)}
                className={cn(
                  getTypographyClassName("caption"),
                  "rounded px-1.5 py-0.5 border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-muted)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] transition-colors cursor-pointer"
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
