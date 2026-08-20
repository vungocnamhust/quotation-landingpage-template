"use client";

import { useCallback } from "react";
import { Sparkles, Bed } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import { DestinationSelect } from "../destination/DestinationSelect.tsx";
import type { DestinationRef } from "../destination/types.ts";
import { AccommodationSelect } from "../accommodation/AccommodationSelect.tsx";
import type { AccommodationProfile } from "../accommodation/types.ts";
import { dateForItineraryDay } from "./factsTypes.ts";
import { inferOvernightDestination } from "../../lib/prefillRules.ts";

export type DayWithStayItem = {
  day_number: number;
  destination: string | null;
  destination_ref?: DestinationRef | null;
  overnight?: string | null;
  overnight_ref?: DestinationRef | null;
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

      // If destination changed, check if overnight was in sync with destination
      if (patch.destination !== undefined && patch.destination !== currentDay.destination) {
        const newDest = patch.destination;
        if (!currentDay.overnight || currentDay.overnight === currentDay.destination) {
          updatedItem.overnight = inferOvernightDestination(newDest, currentDay.overnight ?? null);
          updatedItem.overnight_ref = patch.destination_ref ?? null;
        }

        // Auto-inherit accommodation from previous day if same destination or overnight
        if (
          prevDay &&
          (prevDay.destination === newDest || prevDay.overnight === newDest) &&
          prevDay.accommodation_id &&
          !patch.accommodation_id
        ) {
          updatedItem = {
            ...updatedItem,
            accommodation_id: prevDay.accommodation_id,
            accommodation_name: prevDay.accommodation_name,
            room_type: prevDay.room_type,
          };
        }
      }

      next[index] = updatedItem;

      // Smart Cascade: If this day's hotel changed, cascade down if subsequent contiguous days share the same destination/overnight
      if (patch.accommodation_id !== undefined || patch.room_type !== undefined) {
        for (let i = index + 1; i < next.length; i++) {
          const isSameTarget =
            next[i].destination === updatedItem.destination ||
            next[i].overnight === updatedItem.overnight;
          if (isSameTarget) {
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
            Map out daytime destinations, overnight sleeping locations, and hotel stays day by day.
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
            prevDay.accommodation_id === day.accommodation_id;

          const effectiveOvernight = day.overnight || day.destination || null;

          return (
            <div
              key={index}
              className="grid gap-3 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] p-4 shadow-2xs sm:grid-cols-12 items-start"
            >
              {/* Day Header & Badges */}
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

                <div className="flex flex-wrap items-center gap-2">
                  {effectiveOvernight ? (
                    <span className={cn(getTypographyClassName("caption"), "flex items-center gap-1 rounded-full bg-[var(--color-surface)] px-2.5 py-0.5 border border-[var(--color-border)] text-[var(--color-muted)]")}>
                      <Bed size={12} className="text-[var(--color-accent)] shrink-0" aria-hidden="true" />
                      <span>Overnight: <strong className="text-[var(--color-on-surface)]">{effectiveOvernight}</strong></span>
                    </span>
                  ) : null}

                  {isSameHotelAsPrev ? (
                    <span className={cn(getTypographyClassName("caption"), "rounded-full bg-emerald-50 text-emerald-700 px-2 py-0.5 border border-emerald-200")}>
                      🔁 Continuing stay: {day.accommodation_name || "Same hotel"}
                    </span>
                  ) : null}
                </div>
              </div>

              {/* 1. Day Destination Column */}
              <div className="sm:col-span-4">
                <DestinationSelect
                  label="Day Destination"
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

              {/* 2. Overnight Destination / Sleeping Point Column */}
              <div className="sm:col-span-4">
                <DestinationSelect
                  label="Overnight Location"
                  value={day.overnight || day.destination}
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
                      overnight: destName,
                      overnight_ref: ref ?? null,
                    });
                  }}
                />
              </div>

              {/* 3. Overnight Accommodation Column */}
              <div className="sm:col-span-4 flex flex-col gap-2">
                <AccommodationSelect
                  label="Overnight Accommodation"
                  value={day.accommodation_id}
                  name={day.accommodation_name}
                  destination={day.overnight || day.destination}
                  destinationId={day.overnight_ref?.id || day.destination_ref?.id}
                  variant="compact"
                  size="md"
                  onChange={(profile: AccommodationProfile | null, id, customName) => {
                    const accName = profile?.name ?? customName ?? null;
                    const patch: Partial<DayWithStayItem> = {
                      accommodation_id: profile?.id ?? id ?? null,
                      accommodation_name: accName,
                      room_type: profile?.room_type ?? day.room_type ?? null,
                    };
                    if (profile?.destination) {
                      patch.overnight = profile.destination;
                      patch.overnight_ref = profile.destination_ref ?? null;
                    }
                    updateDay(index, patch);
                  }}
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
