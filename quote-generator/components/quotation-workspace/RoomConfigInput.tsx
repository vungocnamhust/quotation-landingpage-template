"use client";

import { useMemo } from "react";
import { BedDouble, Sparkles } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import { useRoomingHeuristics } from "../../lib/hooks/useRoomingHeuristics.ts";

export type RoomConfigInputProps = {
  value: string;
  adults: number;
  childrenCount: number;
  kidAges?: number[];
  lang?: string;
  onChange: (val: string) => void;
  disabled?: boolean;
  size?: "sm" | "md" | "lg";
  variant?: "default" | "compact";
  className?: string;
};

export default function RoomConfigInput({
  value,
  adults,
  childrenCount,
  kidAges = [],
  lang = "en",
  onChange,
  disabled = false,
  size = "md",
  variant = "default",
  className,
}: RoomConfigInputProps) {
  const { evaluateSuggestions } = useRoomingHeuristics();

  const suggestionResult = useMemo(() => {
    return evaluateSuggestions(adults, childrenCount, kidAges, lang);
  }, [adults, childrenCount, kidAges, lang, evaluateSuggestions]);

  const suggestions = suggestionResult.suggestions;
  const isCompact = variant === "compact";

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <label htmlFor="room-config-input" className="flex flex-col gap-1.5">
        <span
          className={cn(
            getTypographyClassName("label"),
            "flex justify-between items-center text-[var(--color-muted)]"
          )}
        >
          <span className="flex items-center gap-1.5 text-[var(--color-on-surface)]">
            <BedDouble
              size={14}
              className="text-[var(--color-accent)]"
              aria-hidden="true"
            />
            <span>Room Configuration</span>
          </span>
          <span
            className={cn(
              getTypographyClassName("caption"),
              "text-[var(--color-muted)]"
            )}
          >
            Optional / Flexible
          </span>
        </span>
        <input
          id="room-config-input"
          type="text"
          disabled={disabled}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="e.g. 1 Double (King) + 1 Twin (connecting) — or leave blank if undecided"
          className={cn(
            getTypographyClassName(size === "sm" ? "bodySm" : "bodyMd"),
            size === "sm" ? "min-h-9 px-2.5" : "min-h-11 px-3",
            "w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
          )}
        />
      </label>

      {/* Smart preset suggestion chips */}
      {suggestions.length > 0 ? (
        <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
          <span
            className={cn(
              getTypographyClassName("caption"),
              "flex items-center gap-1 text-[var(--color-muted)] mr-1"
            )}
          >
            <Sparkles
              size={12}
              className="text-[var(--color-accent)]"
              aria-hidden="true"
            />
            <span>Quick presets:</span>
          </span>
          {suggestions.map((chip) => {
            const isSelected = value === chip;
            return (
              <button
                key={chip}
                type="button"
                role="button"
                aria-pressed={isSelected}
                disabled={disabled}
                onClick={() => onChange(chip)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onChange(chip);
                  }
                }}
                className={cn(
                  getTypographyClassName(isCompact ? "caption" : "caption"),
                  "rounded-full px-2.5 py-1 transition-all cursor-pointer border select-none focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)]",
                  isSelected
                    ? "border-[var(--color-accent)] bg-[var(--color-accent-wash)] text-[var(--color-accent)] shadow-2xs"
                    : "border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-on-surface)] hover:border-[var(--color-accent)] hover:text-[var(--color-accent)]"
                )}
              >
                {chip}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
