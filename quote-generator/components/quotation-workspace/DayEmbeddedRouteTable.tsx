"use client";

import { useCallback } from "react";
import { Sparkles } from "lucide-react";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";
import { DestinationSelect } from "../destination/DestinationSelect";
import type { DestinationRef } from "../destination/types";
import { AccommodationSelect } from "../accommodation/AccommodationSelect";
import type { AccommodationProfile } from "../accommodation/types";
import { dateForItineraryDay } from "./factsTypes";

export type DayWithStayItem = {
  day_number: number;
  destination: string | null;
  destination_ref?: DestinationRef | null;
  accommodation_id: string | null;
  accommodation_name?: string | null;
  room_type?: string | null;
  summary: string | null;
};

type Props = {
  itinerary: DayWithStayItem[];
  startDate: string | null;
  onChange: (itinerary: DayWithStayItem[]) => void;
  onAutoSuggestStays?: () => void;
};

const inputClass = cn(
  getTypographyClassName("bodyMd"),
  "min-h-11 w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)]"
);

export default function DayEmbeddedRouteTable({
  itinerary,
  startDate,
  onChange,
  onAutoSuggestStays,
}: Props) {
  const updateDay = useCallback(
    (index: number, patch: Partial<DayWithStayItem>) => {
      const next = [...itinerary];
      const prevDay = index > 0 ? next[index - 1] : null;
      const currentDay = next[index];

      let updatedItem = { ...currentDay, ...patch };

      // If destination changed, check if we should auto-inherit from previous day if same destination
      if (patch.destination !== undefined && patch.destination !== currentDay.destination) {
        if (prevDay && prevDay.destination === patch.destination && prevDay.accommodation_id && !patch.accommodation_id) {
          updatedItem = {
            ...updatedItem,
            accommodation_id: prevDay.accommodation_id,
            accommodation_name: prevDay.accommodation_name,
            room_type: prevDay.room_type,
          };
        }
      }

      next[index] = updatedItem;

      // Smart Cascade: If this day's hotel changed, and subsequent contiguous days have the same destination,
      // cascade down if contiguous same destination
      if (patch.accommodation_id !== undefined || patch.room_type !== undefined) {
        for (let i = index + 1; i < next.length; i++) {
          if (next[i].destination === updatedItem.destination) {
            next[i] = {
              ...next[i],
              accommodation_id: updatedItem.accommodation_id,
              accommodation_name: updatedItem.accommodation_name,
              room_type: updatedItem.room_type,
            };
          } else {
            break;
          }
        }
      }

      onChange(next);
    },
    [itinerary, onChange]
  );

  return (
    <div className="flex flex-col gap-4">
      {/* Header bar with Auto-Suggest button */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
            Daily Route & Stays Blueprint
          </h3>
          <p className={cn(getTypographyClassName("caption"), "mt-0.5 text-[var(--color-muted)]")}>
            Each day embeds its destination and overnight stay. Stays are automatically consolidated.
          </p>
        </div>
        {onAutoSuggestStays ? (
          <button
            type="button"
            onClick={onAutoSuggestStays}
            className={cn(
              getTypographyClassName("buttonSecondary"),
              "flex items-center gap-1.5 min-h-9 rounded-[var(--radius-button)] border border-[var(--color-border)] px-3 py-1 text-[var(--color-accent)] hover:bg-[var(--color-accent-wash)] transition-colors cursor-pointer"
            )}
          >
            <Sparkles size={14} aria-hidden="true" />
            <span>✨ Auto-Suggest Stays</span>
          </button>
        ) : null}
      </div>

      {/* Day Cards Grid */}
      <div className="flex flex-col gap-3">
        {itinerary.map((day, index) => {
          const derivedDate = dateForItineraryDay(startDate, day.day_number);
          const prevDay = index > 0 ? itinerary[index - 1] : null;
          const isSameHotelAsPrev =
            prevDay &&
            day.accommodation_id &&
            prevDay.accommodation_id === day.accommodation_id &&
            prevDay.destination === day.destination;

          return (
            <div
              key={index}
              className="grid gap-3 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] p-4 shadow-2xs sm:grid-cols-12 items-start"
            >
              {/* Day Header & Badge */}
              <div className="sm:col-span-12 flex flex-wrap items-center justify-between gap-2 border-b border-[var(--color-border)] pb-2">
                <div className="flex items-center gap-2">
                  <span className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
                    Day {day.day_number}
                  </span>
                  {derivedDate ? (
                    <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
                      · {derivedDate}
                    </span>
                  ) : null}
                </div>

                {isSameHotelAsPrev ? (
                  <span className={cn(getTypographyClassName("caption"), "rounded-full bg-emerald-50 text-emerald-700 px-2 py-0.5 border border-emerald-200")}>
                    🔁 Continuing stay: {day.accommodation_name || "Same hotel"}
                  </span>
                ) : null}
              </div>

              {/* Destination Column */}
              <div className="sm:col-span-5">
                <DestinationSelect
                  label="Destination"
                  value={day.destination}
                  variant="compact"
                  size="md"
                  onChange={(dest, ref) => {
                    const destName =
                      typeof dest === "string"
                        ? dest
                        : Array.isArray(dest)
                          ? dest[0]?.name ?? null
                          : null;
                    updateDay(index, {
                      destination: destName,
                      destination_ref: ref ?? null,
                    });
                  }}
                />
              </div>

              {/* Accommodation Column */}
              <div className="sm:col-span-7 flex flex-col gap-2">
                <AccommodationSelect
                  label="Overnight Accommodation"
                  value={day.accommodation_id}
                  name={day.accommodation_name}
                  destination={day.destination}
                  destinationId={day.destination_ref?.id}
                  variant="compact"
                  size="md"
                  onChange={(profile: AccommodationProfile | null) =>
                    updateDay(index, {
                      accommodation_id: profile?.id ?? null,
                      accommodation_name: profile?.name ?? null,
                      room_type: profile?.room_type ?? day.room_type ?? null,
                    })
                  }
                />
              </div>

              {/* 1-Line Quick Summary Idea */}
              <div className="sm:col-span-12 flex flex-col gap-1.5">
                <label className="flex flex-col gap-1">
                  <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                    1-Line Program Prompt / Idea (Optional)
                  </span>
                  <input
                    className={inputClass}
                    value={day.summary ?? ""}
                    placeholder="e.g. Airport arrival greeting, check-in, evening street food tasting"
                    onChange={(e) => updateDay(index, { summary: e.target.value || null })}
                  />
                </label>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
