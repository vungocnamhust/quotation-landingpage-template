"use client";

import { Plus, Trash2 } from "lucide-react";
import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";
import { currencyDivisor, minorToMajor, majorToMinor } from "../../../lib/rules/pricingReconciler.ts";
import { blankPriceLine, OCCUPANCY_BASIS_OPTIONS, PRICE_FOR_OPTIONS, type RatePriceLine } from "./types.ts";

const UNIT_OPTIONS = ["room", "person", "vehicle", "group", "ticket", "flight_seat", "visa_case", "set"];

type Props = {
  lines: RatePriceLine[];
  currency: string;
  showOccupancy: boolean;
  disabled?: boolean;
  onChange: (next: RatePriceLine[]) => void;
};

const cellClass = cn(
  getTypographyClassName("bodySm"),
  "min-h-9 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-2"
);

export function PriceLinesEditor({ lines, currency, showOccupancy, disabled, onChange }: Props) {
  const updateLine = (index: number, patch: Partial<RatePriceLine>) => {
    onChange(lines.map((line, i) => (i === index ? { ...line, ...patch } : line)));
  };
  const removeLine = (index: number) => onChange(lines.filter((_, i) => i !== index));
  const addLine = () => onChange([...lines, { ...blankPriceLine(), sort_order: lines.length }]);

  const divisor = currencyDivisor(currency);

  return (
    <fieldset className="rounded-[var(--radius-card)] border border-[var(--color-border)] p-3">
      <legend className={cn(getTypographyClassName("label"), "px-1 text-[var(--color-muted)]")}>Price lines</legend>
      <div className="flex flex-col gap-2">
        {lines.map((line, index) => (
          <div key={index} className="grid grid-cols-12 items-center gap-2">
            <select
              className={cn(cellClass, "col-span-2")}
              value={line.price_for}
              disabled={disabled}
              onChange={(e) => updateLine(index, { price_for: e.target.value as RatePriceLine["price_for"] })}
            >
              {PRICE_FOR_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
            {showOccupancy ? (
              <select
                className={cn(cellClass, "col-span-2")}
                value={line.occupancy_basis}
                disabled={disabled}
                onChange={(e) => updateLine(index, { occupancy_basis: e.target.value as RatePriceLine["occupancy_basis"] })}
              >
                {OCCUPANCY_BASIS_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            ) : null}
            <select
              className={cn(cellClass, showOccupancy ? "col-span-2" : "col-span-2")}
              value={line.unit}
              disabled={disabled}
              onChange={(e) => updateLine(index, { unit: e.target.value as RatePriceLine["unit"] })}
            >
              {UNIT_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option.replace(/_/g, " ")}
                </option>
              ))}
            </select>
            <input
              type="number"
              placeholder="tier min"
              className={cn(cellClass, "col-span-1")}
              value={line.tier_min_pax ?? ""}
              disabled={disabled}
              onChange={(e) => updateLine(index, { tier_min_pax: e.target.value === "" ? null : Number(e.target.value) })}
            />
            <input
              type="number"
              placeholder="tier max"
              className={cn(cellClass, "col-span-1")}
              value={line.tier_max_pax ?? ""}
              disabled={disabled}
              onChange={(e) => updateLine(index, { tier_max_pax: e.target.value === "" ? null : Number(e.target.value) })}
            />
            <input
              type="number"
              step={divisor === 1 ? 1 : 0.01}
              placeholder={`amount (${currency})`}
              className={cn(cellClass, "col-span-2")}
              value={minorToMajor(line.amount_minor, currency) ?? 0}
              disabled={disabled}
              onChange={(e) => updateLine(index, { amount_minor: majorToMinor(Number(e.target.value || 0), currency) ?? 0 })}
            />
            <input
              type="text"
              placeholder="note"
              className={cn(cellClass, "col-span-1")}
              value={line.note ?? ""}
              disabled={disabled}
              onChange={(e) => updateLine(index, { note: e.target.value || null })}
            />
            <button
              type="button"
              disabled={disabled}
              onClick={() => removeLine(index)}
              className="col-span-1 flex justify-center text-[var(--color-muted)] hover:text-rose-600 cursor-pointer"
              aria-label="Remove price line"
            >
              <Trash2 size={14} aria-hidden="true" />
            </button>
          </div>
        ))}
        <button
          type="button"
          disabled={disabled}
          onClick={addLine}
          className={cn(
            getTypographyClassName("caption"),
            "flex w-fit items-center gap-1 text-[var(--color-accent)] hover:underline cursor-pointer disabled:opacity-50"
          )}
        >
          <Plus size={12} aria-hidden="true" />
          <span>Add price line</span>
        </button>
      </div>
    </fieldset>
  );
}

export default PriceLinesEditor;
