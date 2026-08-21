"use client";

import { useState } from "react";
import { Plus, Trash2, ChevronDown, ChevronUp, Calendar } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import { DestinationSelect } from "../destination/DestinationSelect.tsx";
import { DateInput } from "../date/index.ts";
import { dateForItineraryDay, formatDisplayDate } from "../../lib/rules/datesRules.ts";
import { tripReconciler, type CanonicalDay } from "../../lib/rules/tripReconciler.ts";

export type BasicDayItem = {
  id?: string;
  day_number: number;
  title?: string;
  destination: string;
  destination_ref_id?: string | null;
  display_date: string;
  summary: string;
  overnight: string;
  meals?: string[];
  highlights?: string[];
  notes?: string[];
};

type Props = {
  days: BasicDayItem[];
  startDate?: string | null;
  onChange?: (days: BasicDayItem[]) => void;
  onAddDay?: (defaultPayload?: Partial<BasicDayItem>) => void;
  onRemoveDay?: (index: number) => void;
  onUpdateDay?: (index: number, patch: Partial<BasicDayItem>) => void;
};

export default function BasicItineraryDayGrid({
  days,
  startDate,
  onChange,
  onAddDay,
  onRemoveDay,
  onUpdateDay,
}: Props) {
  const [isOpen, setIsOpen] = useState(() => days.length > 0);

  const handleAddDay = () => {
    if (onAddDay) {
      onAddDay();
    } else {
      const canonicalDays: CanonicalDay[] = days.map((d, i) => ({
        ...d,
        day_number: d.day_number || i + 1,
        overnight: d.overnight || d.destination || null,
      }));
      const reconciled = tripReconciler.addDay({
        startDate: startDate || null,
        endDate: null,
        durationDays: days.length,
        durationNights: Math.max(0, days.length - 1),
        itinerary: canonicalDays,
      });
      onChange?.(
        reconciled.itinerary.map((d, i) => ({
          id: d.id || `day_${i + 1}`,
          day_number: d.day_number || i + 1,
          title: (d.title as string) || "",
          destination: d.destination || "",
          display_date: d.display_date || "",
          summary: (d.summary as string) || "",
          overnight: d.overnight || "",
          meals: d.meals || [],
          highlights: d.highlights || [],
          notes: d.notes || [],
        }))
      );
    }
    if (!isOpen) setIsOpen(true);
  };

  const handleRemoveDay = (index: number) => {
    if (onRemoveDay) {
      onRemoveDay(index);
    } else {
      const canonicalDays: CanonicalDay[] = days.map((d, i) => ({
        ...d,
        day_number: d.day_number || i + 1,
        overnight: d.overnight || d.destination || null,
      }));
      const reconciled = tripReconciler.removeDay(
        {
          startDate: startDate || null,
          endDate: null,
          durationDays: days.length,
          durationNights: Math.max(0, days.length - 1),
          itinerary: canonicalDays,
        },
        index
      );
      onChange?.(
        reconciled.itinerary.map((d, i) => ({
          id: d.id || `day_${i + 1}`,
          day_number: d.day_number || i + 1,
          title: (d.title as string) || "",
          destination: d.destination || "",
          display_date: d.display_date || "",
          summary: (d.summary as string) || "",
          overnight: d.overnight || "",
          meals: d.meals || [],
          highlights: d.highlights || [],
          notes: d.notes || [],
        }))
      );
    }
  };

  const handleFieldChange = (index: number, field: keyof BasicDayItem, value: unknown) => {
    if (onUpdateDay) {
      onUpdateDay(index, { [field]: value });
    } else {
      const canonicalDays: CanonicalDay[] = days.map((d, i) => ({
        ...d,
        day_number: d.day_number || i + 1,
        overnight: d.overnight || d.destination || null,
      }));
      const reconciled = tripReconciler.updateDay(
        {
          startDate: startDate || null,
          endDate: null,
          durationDays: days.length,
          durationNights: Math.max(0, days.length - 1),
          itinerary: canonicalDays,
        },
        index,
        { [field]: value }
      );
      onChange?.(
        reconciled.itinerary.map((d, i) => ({
          id: d.id || `day_${i + 1}`,
          day_number: d.day_number || i + 1,
          title: (d.title as string) || "",
          destination: d.destination || "",
          display_date: d.display_date || "",
          summary: (d.summary as string) || "",
          overnight: d.overnight || "",
          meals: d.meals || [],
          highlights: d.highlights || [],
          notes: d.notes || [],
        }))
      );
    }
  };

  return (
    <div className="flex flex-col rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] shadow-[var(--elevation-card)] transition-all">
      {/* Accordion Header */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between gap-3 p-5 text-left transition-colors hover:bg-[var(--color-surface-muted)] cursor-pointer"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--color-surface-muted)] text-[var(--color-muted)]">
            <Calendar size={18} aria-hidden="true" />
          </div>
          <div>
            <h3 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)] flex items-center gap-2")}>
              <span>Basic Daily Itinerary</span>
              <span className={cn(getTypographyClassName("caption"), "rounded-full bg-[var(--color-surface-muted)] px-2 py-0.5 text-[var(--color-muted)]")}>
                Optional ({days.length} {days.length === 1 ? "day" : "days"})
              </span>
            </h3>
            <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>
              Optionally outline basic day-by-day destination stops & highlights now.
            </p>
          </div>
        </div>
        <div className="text-[var(--color-muted)]">
          {isOpen ? <ChevronUp size={20} aria-hidden="true" /> : <ChevronDown size={20} aria-hidden="true" />}
        </div>
      </button>

      {/* Accordion Body */}
      {isOpen ? (
        <div className="flex flex-col gap-4 border-t border-[var(--color-border)] p-5">
          {days.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-[var(--radius-card)] border border-dashed border-[var(--color-border)] p-6 text-center">
              <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)] mb-3")}>
                No daily itinerary items added yet. You can skip this or add days below.
              </p>
              <button
                type="button"
                onClick={handleAddDay}
                className={cn(
                  getTypographyClassName("buttonSecondary"),
                  "flex items-center gap-1.5 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[var(--color-on-surface)] hover:border-[var(--color-accent)] hover:text-[var(--color-accent)]"
                )}
              >
                <Plus size={15} aria-hidden="true" />
                <span>+ Add Day 1</span>
              </button>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {days.map((day, idx) => {
                const projectedIso = dateForItineraryDay(startDate, day.day_number);
                const projectedLabel = projectedIso ? formatDisplayDate(projectedIso) : null;

                return (
                  <div
                    key={day.id || `day-${day.day_number}-${idx}`}
                    className="flex flex-col gap-3 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
                          Day {day.day_number}
                        </span>
                        {projectedLabel ? (
                          <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
                            · {projectedLabel}
                          </span>
                        ) : null}
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemoveDay(idx)}
                        className="text-[var(--color-muted)] hover:text-[var(--color-accent)] transition-colors p-1 cursor-pointer"
                        aria-label={`Remove Day ${day.day_number}`}
                      >
                        <Trash2 size={16} aria-hidden="true" />
                      </button>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-3">
                      <DestinationSelect
                        label="Destination:"
                        placeholder="e.g. Hanoi"
                        size="sm"
                        variant="compact"
                        value={day.destination}
                        onChange={(val) =>
                          handleFieldChange(
                            idx,
                            "destination",
                            typeof val === "string" ? val : Array.isArray(val) ? val[0]?.name ?? "" : ""
                          )
                        }
                      />

                      <DateInput
                        mode="text"
                        label="Date:"
                        size="sm"
                        variant="compact"
                        placeholder={projectedLabel || "e.g. Mon, 09 Nov"}
                        value={day.display_date || projectedLabel || ""}
                        onChange={(val) => handleFieldChange(idx, "display_date", val ?? "")}
                      />

                      <DestinationSelect
                        label="Overnight:"
                        placeholder="e.g. Hanoi"
                        size="sm"
                        variant="compact"
                        value={day.overnight}
                        onChange={(val) =>
                          handleFieldChange(
                            idx,
                            "overnight",
                            typeof val === "string" ? val : Array.isArray(val) ? val[0]?.name ?? "" : ""
                          )
                        }
                      />
                    </div>

                    <div className="grid gap-2">
                      <label className="flex flex-col gap-1">
                        <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
                          Day Title (Optional):
                        </span>
                        <input
                          type="text"
                          placeholder="e.g. Arrival in Hanoi & Old Quarter Walk"
                          value={day.title || ""}
                          onChange={(e) => handleFieldChange(idx, "title", e.target.value)}
                          className={cn(
                            getTypographyClassName("bodySm"),
                            "h-9 w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2.5 text-[var(--color-on-surface)] focus:outline-none focus:ring-1 focus:ring-[var(--color-focus)]"
                          )}
                        />
                      </label>

                      <label className="flex flex-col gap-1">
                        <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
                          Short Summary / Highlights:
                        </span>
                        <input
                          type="text"
                          placeholder="e.g. Arrival in Hanoi, airport transfer & evening food tour"
                          value={day.summary}
                          onChange={(e) => handleFieldChange(idx, "summary", e.target.value)}
                          className={cn(
                            getTypographyClassName("bodySm"),
                            "h-9 w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2.5 text-[var(--color-on-surface)] focus:outline-none focus:ring-1 focus:ring-[var(--color-focus)]"
                          )}
                        />
                      </label>
                    </div>
                  </div>
                );
              })}

              <button
                type="button"
                onClick={handleAddDay}
                className={cn(
                  getTypographyClassName("buttonSecondary"),
                  "mt-2 flex items-center justify-center gap-1.5 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2.5 text-[var(--color-on-surface)] transition-colors hover:border-[var(--color-accent)] hover:text-[var(--color-accent)]"
                )}
              >
                <Plus size={15} aria-hidden="true" />
                <span>+ Add Day {days.length + 1}</span>
              </button>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}

