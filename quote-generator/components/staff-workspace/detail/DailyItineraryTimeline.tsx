"use client";

import { Calendar, Bed, MapPin } from "lucide-react";
import DetailSectionCard from "./DetailSectionCard";
import { getTypographyClassName } from "../../../config/typography";
import { cn } from "../../../utils/cn";

type ItineraryDayItem = {
  day_number?: number | null;
  destination?: string | null;
  display_date?: string | null;
  summary?: string | null;
  overnight?: string | null;
  meals?: string[];
  highlights?: string[];
  notes?: string[];
};

type Props = {
  days?: Array<Record<string, unknown>>;
};

export default function DailyItineraryTimeline({ days = [] }: Props) {
  const dayItems = days as ItineraryDayItem[];

  return (
    <DetailSectionCard
      title="Basic Daily Itinerary"
      subtitle="Day-by-day outline, destinations & overnight accommodations"
      icon={<Calendar size={18} aria-hidden="true" />}
      headerBadge={
        <span
          className={cn(
            getTypographyClassName("caption"),
            "rounded-full px-2.5 py-0.5 border bg-[var(--color-surface-muted)] text-[var(--color-muted)] border-[var(--color-border)]"
          )}
        >
          {dayItems.length} {dayItems.length === 1 ? "Day" : "Days"}
        </span>
      }
    >
      {dayItems.length === 0 ? (
        <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)] p-2")}>
          No day-by-day itinerary outline was included in this intake request.
        </p>
      ) : (
        <div className="flex flex-col gap-3">
          {dayItems.map((day, idx) => {
            const dayNum = day.day_number || idx + 1;
            return (
              <div
                key={idx}
                className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3.5 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3.5 transition-all hover:border-[var(--color-accent)]"
              >
                <div className="flex items-start gap-3 min-w-0 flex-1">
                  <span className={cn(getTypographyClassName("caption"), "flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--color-accent)] text-white shadow-xs")}>
                    D{dayNum}
                  </span>

                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h4 className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-on-surface)] flex items-center gap-1.5")}>
                        <MapPin size={13} className="text-[var(--color-accent)] shrink-0" aria-hidden="true" />
                        <span>{day.destination || `Day ${dayNum} Exploration`}</span>
                      </h4>
                      {day.display_date ? (
                        <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)] font-mono")}>
                          ({day.display_date})
                        </span>
                      ) : null}
                    </div>

                    <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)] mt-1 whitespace-pre-wrap")}>
                      {day.summary || "Exploration, private transfers and curated experiences."}
                    </p>
                  </div>
                </div>

                {day.overnight ? (
                  <div className={cn(getTypographyClassName("caption"), "flex items-center gap-1.5 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1 text-[var(--color-on-surface)] shrink-0 self-start sm:self-center shadow-2xs")}>
                    <Bed size={13} className="text-[var(--color-accent)] shrink-0" aria-hidden="true" />
                    <span>Overnight: {day.overnight}</span>
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      )}
    </DetailSectionCard>
  );
}
