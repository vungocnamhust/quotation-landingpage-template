"use client";

import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";

type Props = {
  childrenCount: number;
  kidAges: number[];
  onChange: (ages: number[]) => void;
};

export default function KidAgesInput({ childrenCount, kidAges, onChange }: Props) {
  if (childrenCount <= 0) return null;

  const handleAgeChange = (index: number, valueStr: string) => {
    const ageVal = Math.max(0, Math.min(17, parseInt(valueStr, 10) || 0));
    const next = [...kidAges];
    // Ensure array length matches children count
    while (next.length < childrenCount) {
      next.push(6);
    }
    next[index] = ageVal;
    onChange(next.slice(0, childrenCount));
  };

  const currentAges = Array.from({ length: childrenCount }).map((_, idx) => kidAges[idx] ?? 6);

  return (
    <div className="flex flex-col gap-2 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3">
      <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
        Children Ages ({childrenCount} {childrenCount === 1 ? "child" : "children"})
      </span>
      <div className="flex flex-wrap gap-3">
        {currentAges.map((age, idx) => (
          <label key={idx} className="flex items-center gap-2">
            <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
              Child {idx + 1}:
            </span>
            <input
              type="number"
              min={0}
              max={17}
              value={age}
              onChange={(e) => handleAgeChange(idx, e.target.value)}
              className={cn(
                getTypographyClassName("bodySm"),
                "h-9 w-16 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2 text-center text-[var(--color-on-surface)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)]"
              )}
            />
          </label>
        ))}
      </div>
    </div>
  );
}
