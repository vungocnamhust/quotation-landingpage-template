"use client";

import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";
import CustomSelect from "../../ui/CustomSelect.tsx";
import type {
  PricingFact,
  PricingOptionFact,
  QuotationFacts,
} from "../factsTypes.ts";
import {
  CURRENCY_OPTIONS,
  formatMinorAmount,
  isRenderablePricingOption,
  MAX_COMMERCIAL_OPTIONS,
  minorAmountFromInput,
  minorAmountToInput,
} from "../factsTypes.ts";
import { inferDefaultCurrency } from "../../../lib/prefillRules.ts";
import { pricingReconciler } from "../../../lib/rules/pricingReconciler.ts";

const lines = (values: string[]) => values.join("\n");
const toLines = (value: string) => value.split("\n");

const inputClass = cn(
  getTypographyClassName("bodyMd"),
  "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] transition-shadow duration-200 focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
);

function Field({
  id,
  label,
  value,
  onChange,
  type = "text",
  disabled,
  required,
}: {
  id?: string;
  label: string;
  value: string | number | null;
  onChange: (value: string) => void;
  type?: string;
  disabled?: boolean;
  required?: boolean;
}) {
  return (
    <label className="flex flex-col gap-2">
      <span className={cn(getTypographyClassName("label"), "flex justify-between gap-3 text-[var(--color-muted)]")}>
        <span>{label}</span>
        <span className={cn(getTypographyClassName("caption"), required ? "text-[var(--color-accent)]" : "text-[var(--color-muted)]")}>
          {required ? "Required" : "Optional"}
        </span>
      </span>
      <input
        id={id}
        aria-required={required}
        className={inputClass}
        type={type}
        disabled={disabled}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}

function Area({
  label,
  value,
  onChange,
  hint,
  disabled,
}: {
  label: string;
  value: string | null;
  onChange: (value: string) => void;
  hint?: string;
  disabled?: boolean;
}) {
  return (
    <label className="flex flex-col gap-2">
      <span className={cn(getTypographyClassName("label"), "flex justify-between gap-3 text-[var(--color-muted)]")}>
        <span>{label}</span>
        {hint ? (
          <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
            {hint}
          </span>
        ) : null}
      </span>
      <textarea
        rows={4}
        disabled={disabled}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        className={cn(
          getTypographyClassName("bodyMd"),
          "rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-3 text-[var(--color-on-surface)] transition-shadow duration-200 focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
        )}
      />
    </label>
  );
}

type Props = {
  pricing: PricingFact;
  brandId: string | null;
  market: string | null;
  adults: number | null;
  childrenCount?: number | null;
  lang?: string;
  readOnly?: boolean;
  onAddPricingOption: () => void;
  onPatchPricingOption: (index: number, patch: Partial<PricingOptionFact>) => void;
  onRemovePricingOption: (index: number) => void;
  onUpdate: <K extends keyof QuotationFacts>(key: K, value: QuotationFacts[K]) => void;
};

export function FactCommercialSection({
  pricing,
  brandId,
  market,
  adults,
  childrenCount,
  lang = "en",
  readOnly = false,
  onAddPricingOption,
  onPatchPricingOption,
  onRemovePricingOption,
  onUpdate,
}: Props) {
  const safeAdults = Math.max(1, adults ?? 2);
  const safeChildren = Math.max(0, childrenCount ?? 0);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
          Pricing options ({pricing.options.length}/{MAX_COMMERCIAL_OPTIONS})
        </span>
        <button
          type="button"
          disabled={readOnly || pricing.options.length >= MAX_COMMERCIAL_OPTIONS}
          onClick={onAddPricingOption}
          className={cn(
            getTypographyClassName("buttonSecondary"),
            "min-h-10 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-3.5 shadow-2xs border border-transparent transition-all disabled:opacity-50 cursor-pointer"
          )}
        >
          Add option
        </button>
      </div>

      {pricing.options.map((option, index) => {
        const defaultCurr =
          option.currency || inferDefaultCurrency(brandId, market);
        const curr = option.currency || defaultCurr;
        const perAdultVal = option.per_adult_amount_minor ?? option.per_traveler_amount_minor;
        const perChildVal = option.per_child_amount_minor ?? null;

        const currentOption = {
          id: option.id || `opt_${index + 1}`,
          label: option.label || `Option ${index + 1}`,
          currency: curr,
          perAdultMinor: perAdultVal ?? null,
          perChildMinor: safeChildren > 0 ? perChildVal : null,
          groupTotalMinor: option.group_total_amount_minor ?? null,
          perTravelerMinor: perAdultVal ?? null,
          childRatio:
            (perAdultVal && perAdultVal > 0 && perChildVal !== null && perChildVal !== undefined)
              ? perChildVal / perAdultVal
              : 0.75,
        };

        const handleAdultChange = (valStr: string) => {
          const minor = minorAmountFromInput(valStr, curr);
          const updated = pricingReconciler.updateOptionPerAdult(
            currentOption,
            minor,
            safeAdults,
            safeChildren
          );
          onPatchPricingOption(index, {
            currency: curr,
            per_adult_amount_minor: updated.perAdultMinor,
            per_traveler_amount_minor: updated.perAdultMinor,
            per_child_amount_minor: updated.perChildMinor,
            group_total_amount_minor: updated.groupTotalMinor,
          });
        };

        const handleChildChange = (valStr: string) => {
          const minor = minorAmountFromInput(valStr, curr);
          const updated = pricingReconciler.updateOptionPerChild(
            currentOption,
            minor,
            safeAdults,
            safeChildren
          );
          onPatchPricingOption(index, {
            currency: curr,
            per_adult_amount_minor: updated.perAdultMinor,
            per_traveler_amount_minor: updated.perAdultMinor,
            per_child_amount_minor: updated.perChildMinor,
            group_total_amount_minor: updated.groupTotalMinor,
          });
        };

        const handleChildPreset = (ratio: number) => {
          const updated = pricingReconciler.applyChildPreset(
            currentOption,
            ratio,
            safeAdults,
            safeChildren
          );
          onPatchPricingOption(index, {
            currency: curr,
            per_adult_amount_minor: updated.perAdultMinor,
            per_traveler_amount_minor: updated.perAdultMinor,
            per_child_amount_minor: updated.perChildMinor,
            group_total_amount_minor: updated.groupTotalMinor,
          });
        };

        const handleTotalChange = (valStr: string) => {
          const totalMinor = minorAmountFromInput(valStr, curr);
          const updated = pricingReconciler.updateOptionTotal(
            currentOption,
            totalMinor,
            safeAdults,
            safeChildren
          );
          onPatchPricingOption(index, {
            currency: curr,
            per_adult_amount_minor: updated.perAdultMinor,
            per_traveler_amount_minor: updated.perAdultMinor,
            per_child_amount_minor: updated.perChildMinor,
            group_total_amount_minor: updated.groupTotalMinor,
          });
        };

        const handleCurrencyChange = (nextCurrency: string) => {
          const hasAmount = Boolean(perAdultVal || option.group_total_amount_minor);
          const updated = pricingReconciler.convertOptionCurrency(
            currentOption,
            nextCurrency,
            {
              convertAmounts: hasAmount,
              adults: safeAdults,
              children: safeChildren,
            }
          );
          onPatchPricingOption(index, {
            currency: updated.currency,
            per_adult_amount_minor: updated.perAdultMinor,
            per_traveler_amount_minor: updated.perAdultMinor,
            per_child_amount_minor: updated.perChildMinor,
            group_total_amount_minor: updated.groupTotalMinor,
          });
        };

        const expectedTotal =
          perAdultVal !== null && perAdultVal !== undefined
            ? pricingReconciler.calculateOptionTotal(
                perAdultVal,
                safeChildren > 0 ? perChildVal : null,
                safeAdults,
                safeChildren
              )
            : null;

        const inconsistent =
          expectedTotal !== null &&
          option.group_total_amount_minor !== null &&
          expectedTotal !== option.group_total_amount_minor;

        return (
          <div
            id={`pricing-option-${index}`}
            key={option.id}
            className="flex flex-col gap-3 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface-white)] p-4 shadow-2xs"
          >
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Field
                id={`pricing-${index}-label`}
                label="Option label"
                required
                disabled={readOnly}
                value={option.label}
                onChange={(value) =>
                  onPatchPricingOption(index, { label: value })
                }
              />

              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  Currency
                </span>
                <CustomSelect
                  options={CURRENCY_OPTIONS}
                  value={curr}
                  disabled={readOnly}
                  onChange={handleCurrencyChange}
                />
              </label>

              {/* Price / Adult */}
              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "flex justify-between text-[var(--color-muted)]")}>
                  <span>Price / Adult</span>
                  <span className={cn(getTypographyClassName("caption"), "text-[var(--color-accent)]")}>
                    Required
                  </span>
                </span>
                <input
                  type="number"
                  min={0}
                  disabled={readOnly}
                  placeholder="e.g. 4000"
                  className={inputClass}
                  value={minorAmountToInput(perAdultVal, curr)}
                  onChange={(e) => handleAdultChange(e.target.value)}
                />
              </label>

              {/* Price / Child */}
              <div className={cn("flex flex-col gap-2", safeChildren === 0 ? "opacity-40" : "")}>
                <span className={cn(getTypographyClassName("label"), "flex justify-between text-[var(--color-muted)]")}>
                  <span>Price / Child</span>
                  <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
                    {safeChildren > 0 ? "Optional" : "No kids"}
                  </span>
                </span>
                <input
                  type="number"
                  min={0}
                  disabled={readOnly || safeChildren === 0}
                  className={inputClass}
                  value={safeChildren > 0 ? minorAmountToInput(perChildVal, curr) : ""}
                  placeholder={safeChildren > 0 ? "e.g. 2500" : "N/A"}
                  onChange={(e) => handleChildChange(e.target.value)}
                />
                {safeChildren > 0 && !readOnly ? (
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
                      75%
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
                      Free
                    </button>
                  </div>
                ) : null}
              </div>

              {/* Group Total */}
              <label className="flex flex-col gap-2 sm:col-span-2">
                <span className={cn(getTypographyClassName("label"), "flex justify-between text-[var(--color-muted)]")}>
                  <span className="text-[var(--color-on-surface)]">Group Total Price</span>
                  <span className={cn(getTypographyClassName("caption"), "text-[var(--color-accent)]")}>
                    Auto-Calculated
                  </span>
                </span>
                <input
                  type="number"
                  min={0}
                  disabled={readOnly}
                  className={cn(inputClass, "border-[var(--color-accent)]")}
                  value={minorAmountToInput(option.group_total_amount_minor, curr)}
                  placeholder="e.g. 10500"
                  onChange={(e) => handleTotalChange(e.target.value)}
                />
              </label>

              {/* Breakdown Badge */}
              <div className="sm:col-span-2 flex items-center gap-2 rounded-[var(--radius-button)] bg-[var(--color-surface-muted)] p-2.5 text-[var(--color-muted)] border border-[var(--color-border)]">
                <p className={cn(getTypographyClassName("caption"), "text-[var(--color-on-surface)]")}>
                  {safeChildren > 0 ? (
                    <>
                      Breakdown:{" "}
                      <strong>
                        {safeAdults} Adults x {formatMinorAmount(perAdultVal, curr, lang)}
                      </strong>{" "}
                      +{" "}
                      <strong>
                        {safeChildren} Children x {formatMinorAmount(perChildVal, curr, lang)}
                      </strong>{" "}
                      ={" "}
                      <strong className="text-emerald-700">
                        {formatMinorAmount(option.group_total_amount_minor, curr, lang)} Total
                      </strong>
                    </>
                  ) : (
                    <>
                      Breakdown:{" "}
                      <strong>
                        {safeAdults} Adults x {formatMinorAmount(perAdultVal, curr, lang)}
                      </strong>{" "}
                      ={" "}
                      <strong className="text-emerald-700">
                        {formatMinorAmount(option.group_total_amount_minor, curr, lang)} Total
                      </strong>
                    </>
                  )}
                </p>
              </div>
            </div>

            {inconsistent ? (
              <div className="flex flex-col gap-2 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] p-3 text-[var(--color-muted)]">
                <p className={cn(getTypographyClassName("caption"))}>
                  {`For ${partyLabel(safeAdults, safeChildren)}, the calculated total equals ${formatMinorAmount(
                    expectedTotal,
                    curr,
                    lang
                  )}; the entered group total is ${formatMinorAmount(
                    option.group_total_amount_minor,
                    curr,
                    lang
                  )}.`}
                </p>
                {!readOnly ? (
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() =>
                        onPatchPricingOption(index, {
                          group_total_amount_minor: expectedTotal,
                        })
                      }
                      className={cn(
                        getTypographyClassName("caption"),
                        "px-2 py-1 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] cursor-pointer"
                      )}
                    >
                      Apply calculated total (
                      {formatMinorAmount(expectedTotal, curr, lang)}
                      )
                    </button>
                  </div>
                ) : null}
              </div>
            ) : null}

            <div className="flex items-center justify-between pt-1">
              <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
                {isRenderablePricingOption(option)
                  ? "Will appear in the brochure."
                  : "Complete the option before it can be saved."}
              </p>

              {!readOnly ? (
                <button
                  type="button"
                  onClick={() => onRemovePricingOption(index)}
                  className={cn(
                    getTypographyClassName("buttonSecondary"),
                    "min-h-9 w-fit rounded-[var(--radius-button)] bg-rose-700 !text-white hover:bg-rose-800 px-3 shadow-2xs border border-transparent transition-all cursor-pointer"
                  )}
                >
                  Remove option
                </button>
              ) : null}
            </div>
          </div>
        );
      })}

      <Area
        label="Pricing note"
        disabled={readOnly}
        value={lines(pricing.conditions)}
        onChange={(value) =>
          onUpdate("pricing_facts", {
            ...pricing,
            conditions: toLines(value),
          })
        }
        hint="Optional. One factual note per line; the brochure hides this block when empty."
      />
    </div>
  );
}

function partyLabel(adults: number, children: number): string {
  return children > 0 ? `${adults} adults, ${children} children` : `${adults} adults`;
}
