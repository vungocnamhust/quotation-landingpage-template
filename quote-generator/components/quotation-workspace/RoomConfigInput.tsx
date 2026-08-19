"use client";

import { useMemo } from "react";
import { BedDouble, Sparkles } from "lucide-react";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";

type Props = {
  value: string;
  adults: number;
  childrenCount: number;
  onChange: (val: string) => void;
  disabled?: boolean;
  size?: "sm" | "md";
  className?: string;
};

export default function RoomConfigInput({
  value,
  adults,
  childrenCount,
  onChange,
  disabled = false,
  size = "md",
  className,
}: Props) {
  const suggestions = useMemo(() => {
    const list: string[] = [];
    if (adults === 1 && childrenCount === 0) {
      list.push("1 Single Room", "1 Double (Single Occupancy)");
    } else if (adults === 2 && childrenCount === 0) {
      list.push("1 Double (King Bed)", "1 Twin (2 Separate Beds)");
    } else if (adults === 2 && childrenCount > 0) {
      list.push(
        "1 Double + 1 Twin (Connecting)",
        "1 Family Suite / Villa",
        "1 Double Room + Extra Bed"
      );
    } else if (adults === 3 && childrenCount === 0) {
      list.push("1 Double + 1 Single", "1 Triple Room / Suite", "3 Single Rooms");
    } else if (adults >= 4 && childrenCount === 0) {
      const roomCount = Math.ceil(adults / 2);
      list.push(
        `${roomCount} Double Rooms`,
        `${roomCount} Twin Rooms`,
        "Multi-bedroom Private Villa"
      );
    } else {
      const totalPax = adults + childrenCount;
      const estimatedRooms = Math.max(2, Math.ceil(totalPax / 2));
      list.push(
        `${estimatedRooms} Rooms (Connecting/Adjoining)`,
        "Family Suite / Multi-bedroom Villa",
        `${adults} Double + Connecting Kids Room`
      );
    }
    return list;
  }, [adults, childrenCount]);

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <label htmlFor="room-config-input" className="flex flex-col gap-1.5">
        <span className={cn(getTypographyClassName("label"), "flex justify-between items-center text-[var(--color-muted)]")}>
          <span className="flex items-center gap-1.5">
            <BedDouble size={14} className="text-[var(--color-accent)]" aria-hidden="true" />
            <span>Room Configuration</span>
          </span>
          <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
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
      <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
        <span className={cn(getTypographyClassName("caption"), "flex items-center gap-1 text-[var(--color-muted)] mr-1")}>
          <Sparkles size={12} className="text-[var(--color-accent)]" aria-hidden="true" />
          <span>Quick presets:</span>
        </span>
        {suggestions.map((chip) => {
          const isSelected = value === chip;
          return (
            <button
              key={chip}
              type="button"
              disabled={disabled}
              onClick={() => onChange(chip)}
              className={cn(
                getTypographyClassName("caption"),
                "rounded-full px-2.5 py-1 transition-all cursor-pointer border",
                isSelected
                  ? "border-[var(--color-accent)] bg-[var(--color-accent-wash)] text-[var(--color-accent)]"
                  : "border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-on-surface)] hover:border-[var(--color-accent)] hover:text-[var(--color-accent)]"
              )}
            >
              {chip}
            </button>
          );
        })}
      </div>
    </div>
  );
}
