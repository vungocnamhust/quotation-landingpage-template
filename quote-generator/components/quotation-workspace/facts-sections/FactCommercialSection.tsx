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
        const perTravelerVal = option.per_adult_amount_minor ?? option.per_traveler_amount_minor;

        const expectedTotal =
          perTravelerVal !== null && perTravelerVal !== undefined
            ? pricingReconciler.calculateOptionTotal(
                perTravelerVal,
                option.per_child_amount_minor,
                safeAdults,
                safeChildren
              )
            : null;

        const expectedRates =
          option.group_total_amount_minor !== null && option.group_total_amount_minor !== undefined
            ? pricingReconciler.inferOptionRatesFromTotal(
                option.group_total_amount_minor,
                safeAdults,
                safeChildren
              )
            : null;
        const expectedPerTraveler = expectedRates?.perAdultMinor ?? null;

        const inconsistent =
          expectedTotal !== null &&
          option.group_total_amount_minor !== null &&
          expectedTotal !== option.group_total_amount_minor;

        const partySummary =
          safeChildren > 0
            ? `${safeAdults} adults, ${safeChildren} children`
            : `${safeAdults} adults`;

        return (
          <div
            id={`pricing-option-${index}`}
            key={option.id}
            className="grid gap-3 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface-white)] p-4 shadow-2xs sm:grid-cols-2"
          >
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
                value={option.currency || defaultCurr}
                disabled={readOnly}
                onChange={(value) =>
                  onPatchPricingOption(index, { currency: value })
                }
              />
            </label>

            <Field
              label="Per traveler price"
              required
              type="number"
              disabled={readOnly}
              value={minorAmountToInput(
                perTravelerVal,
                option.currency || defaultCurr
              )}
              onChange={(value) => {
                const perTraveler = minorAmountFromInput(
                  value,
                  option.currency || defaultCurr
                );
                onPatchPricingOption(index, {
                  currency: option.currency || defaultCurr,
                  per_traveler_amount_minor: perTraveler,
                  per_adult_amount_minor: perTraveler,
                });
              }}
            />

            <Field
              label="Group total price"
              required
              type="number"
              disabled={readOnly}
              value={minorAmountToInput(
                option.group_total_amount_minor,
                option.currency || defaultCurr
              )}
              onChange={(value) => {
                const groupTotal = minorAmountFromInput(
                  value,
                  option.currency || defaultCurr
                );
                onPatchPricingOption(index, {
                  currency: option.currency || defaultCurr,
                  group_total_amount_minor: groupTotal,
                });
              }}
            />

            {inconsistent ? (
              <div className="sm:col-span-2 flex flex-col gap-2 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] p-3 text-[var(--color-muted)]">
                <p className={cn(getTypographyClassName("caption"))}>
                  {`For ${partyLabel(safeAdults, safeChildren)}, the per traveler price equals ${formatMinorAmount(
                    expectedTotal,
                    option.currency || defaultCurr,
                    lang
                  )}; the entered group total is ${formatMinorAmount(
                    option.group_total_amount_minor,
                    option.currency || defaultCurr,
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
                      {formatMinorAmount(
                        expectedTotal,
                        option.currency || defaultCurr,
                        lang
                      )}
                      )
                    </button>
                    {expectedPerTraveler !== null ? (
                      <button
                        type="button"
                        onClick={() =>
                          onPatchPricingOption(index, {
                            per_traveler_amount_minor: expectedPerTraveler,
                            per_adult_amount_minor: expectedPerTraveler,
                          })
                        }
                        className={cn(
                          getTypographyClassName("caption"),
                          "px-2 py-1 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] cursor-pointer"
                        )}
                      >
                        Apply calculated per traveler (
                        {formatMinorAmount(
                          expectedPerTraveler,
                          option.currency || defaultCurr,
                          lang
                        )}
                        )
                      </button>
                    ) : null}
                  </div>
                ) : null}
              </div>
            ) : null}

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
                  "min-h-10 w-fit rounded-[var(--radius-button)] bg-rose-700 !text-white hover:bg-rose-800 px-3.5 shadow-2xs border border-transparent transition-all cursor-pointer"
                )}
              >
                Remove option
              </button>
            ) : null}
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
