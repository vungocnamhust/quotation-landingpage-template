"use client";

import { getTypographyClassName } from "../../../config/typography";
import { cn } from "../../../utils/cn";
import { DayEditorCard } from "./DayEditorCard";
import type { ItineraryDayFact, TripFact } from "../factsTypes";
import type { MediaWorkspace } from "../MediaSlotRenderer";

type Props = {
  trip: TripFact;
  activeDay: number | null;
  readOnly?: boolean;
  onToggleDay: (index: number) => void;
  onPatchDay: (index: number, patch: Partial<ItineraryDayFact>) => void;
  onRemoveDay: (index: number) => void;
  onAddDay: () => void;
  mediaWorkspace?: MediaWorkspace;
};

export function FactProgrammeSection({
  trip,
  activeDay,
  readOnly = false,
  onToggleDay,
  onPatchDay,
  onRemoveDay,
  onAddDay,
  mediaWorkspace,
}: Props) {
  return (
    <div className="flex flex-col gap-3">
      {trip.itinerary.map((day, index) => (
        <DayEditorCard
          key={index}
          day={day}
          index={index}
          startDate={trip.start_date}
          open={activeDay === index}
          readOnly={readOnly}
          onToggle={onToggleDay}
          onPatch={onPatchDay}
          onRemove={onRemoveDay}
          mediaWorkspace={mediaWorkspace}
        />
      ))}
      {!readOnly ? (
        <button
          type="button"
          onClick={onAddDay}
          className={cn(
            getTypographyClassName("buttonSecondary"),
            "min-h-14 rounded-[var(--radius-button)] border-2 border-dashed border-[var(--color-accent)] bg-[color-mix(in_srgb,var(--color-accent-wash)_60%,white)] px-4 text-[var(--color-accent)] transition-all duration-200 hover:bg-[var(--color-accent)] hover:text-white hover:shadow-xs cursor-pointer"
          )}
        >
          + Add itinerary day
        </button>
      ) : null}
    </div>
  );
}
