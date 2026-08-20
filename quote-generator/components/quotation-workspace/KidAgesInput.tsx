"use client";

import { Baby } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import {
  normalizeKidAges,
  updateKidAgeVector,
} from "../../lib/rules/partyReconciler.ts";

export type KidAgesInputProps = {
  childrenCount: number;
  kidAges: number[];
  onChange: (ages: number[]) => void;
  onAgeChange?: (index: number, age: number) => void;
  disabled?: boolean;
  size?: "sm" | "md" | "lg";
  variant?: "default" | "compact" | "inline";
  className?: string;
};

export default function KidAgesInput({
  childrenCount,
  kidAges,
  onChange,
  onAgeChange,
  disabled = false,
  size = "md",
  variant = "default",
  className,
}: KidAgesInputProps) {
  if (childrenCount <= 0) return null;

  const currentAges = normalizeKidAges(kidAges, childrenCount);

  const handleAgeChange = (index: number, valueStr: string) => {
    const updatedAges = updateKidAgeVector(kidAges, childrenCount, index, valueStr);
    onChange(updatedAges);
    if (onAgeChange) {
      onAgeChange(index, updatedAges[index]);
    }
  };

  const isCompact = variant === "compact";
  const isInline = variant === "inline";

  return (
    <div
      className={cn(
        "flex flex-col gap-2 rounded-[var(--radius-card)] border border-[var(--color-border)] transition-all",
        isCompact
          ? "p-2 bg-[var(--color-surface)]"
          : isInline
          ? "p-2.5 bg-transparent border-dashed"
          : "p-3.5 bg-[var(--color-surface-muted)]",
        className
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span
          className={cn(
            getTypographyClassName("label"),
            "flex items-center gap-1.5 text-[var(--color-on-surface)]"
          )}
        >
          <Baby size={14} className="text-[var(--color-accent)]" aria-hidden="true" />
          <span>
            Children Ages ({childrenCount}{" "}
            {childrenCount === 1 ? "child" : "children"})
          </span>
        </span>
        <span
          className={cn(
            getTypographyClassName("caption"),
            "text-[var(--color-muted)]"
          )}
        >
          0–17 years
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-2.5 pt-0.5">
        {currentAges.map((age, idx) => (
          <label
            key={`kid-age-slot-${idx}`}
            className={cn(
              "flex items-center gap-1.5 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2 py-1 shadow-2xs transition-shadow focus-within:ring-2 focus-within:ring-[var(--color-focus)]",
              disabled && "opacity-60 cursor-not-allowed"
            )}
          >
            <span
              className={cn(
                getTypographyClassName("caption"),
                "text-[var(--color-muted)] select-none"
              )}
            >
              Child {idx + 1}:
            </span>
            <input
              type="number"
              min={0}
              max={17}
              disabled={disabled}
              value={age}
              aria-label={`Age of Child ${idx + 1}`}
              onChange={(e) => handleAgeChange(idx, e.target.value)}
              className={cn(
                getTypographyClassName(size === "sm" ? "caption" : "bodySm"),
                size === "sm" ? "h-6 w-10" : "h-7 w-12",
                "rounded-[var(--radius-button)] border-0 bg-transparent px-1 text-center text-[var(--color-on-surface)] focus:outline-none disabled:cursor-not-allowed"
              )}
            />
            <span
              className={cn(
                getTypographyClassName("caption"),
                "text-[var(--color-muted)] select-none opacity-80"
              )}
            >
              yo
            </span>
          </label>
        ))}
      </div>
    </div>
  );
}
