"use client";

import { useState } from "react";
import { Plus, Trash2, ChevronDown, ChevronUp, Calendar, Sparkles } from "lucide-react";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";
import { DestinationSelect } from "../destination/DestinationSelect";
import { dateForItineraryDay, formatDisplayDate } from "../../lib/rules/datesRules";

export type BasicDayItem = {
  day_number: number;
  destination: string;
  display_date: string;
  summary: string;
  overnight: string;
};

type Props = {
  days: BasicDayItem[];
  startDate?: string | null;
  onChange: (days: BasicDayItem[]) => void;
};

export default function BasicItineraryDayGrid({ days, startDate, onChange }: Props) {
  const [isOpen, setIsOpen] = useState(false);

  const handleAddDay = () => {
    const nextNumber = days.length + 1;
    const projectedIso = dateForItineraryDay(startDate, nextNumber);
    const projectedLabel = projectedIso ? formatDisplayDate(projectedIso) : "";
    const newDay: BasicDayItem = {
      day_number: nextNumber,
      destination: "",
      display_date: projectedLabel,
      summary: "",
      overnight: "",
    };
    onChange([...days, newDay]);
    if (!isOpen) setIsOpen(true);
  };

  const handleRemoveDay = (index: number) => {
    const updated = days.filter((_, i) => i !== index).map((day, i) => {
      const nextNum = i + 1;
      const nextProjectedIso = dateForItineraryDay(startDate, nextNum);
      const nextProjectedLabel = nextProjectedIso ? formatDisplayDate(nextProjectedIso) : "";
      return {
        ...day,
        day_number: nextNum,
        display_date: day.display_date || nextProjectedLabel,
      };
    });
    onChange(updated);
  };

  const handleFieldChange = (index: number, field: keyof BasicDayItem, value: string) => {
    const updated = [...days];
    updated[index] = { ...updated[index], [field]: value };
    onChange(updated);
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
                    key={idx}
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

                      <label className="flex flex-col gap-1.5">
                        <div className="flex items-center justify-between gap-1">
                          <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                            Date:
                          </span>
                          {!day.display_date && projectedLabel ? (
                            <button
                              type="button"
                              onClick={() => handleFieldChange(idx, "display_date", projectedLabel)}
                              className={cn(
                                getTypographyClassName("caption"),
                                "flex items-center gap-1 text-[var(--color-accent)] hover:underline cursor-pointer"
                              )}
                            >
                              <Sparkles size={11} aria-hidden="true" />
                              <span>Auto-fill</span>
                            </button>
                          ) : null}
                        </div>
                        <input
                          type="text"
                          placeholder={projectedLabel || "e.g. Mon, 09 Nov"}
                          value={day.display_date}
                          onChange={(e) => handleFieldChange(idx, "display_date", e.target.value)}
                          className={cn(
                            getTypographyClassName("bodySm"),
                            "h-9 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2.5 text-[var(--color-on-surface)] focus:outline-none focus:ring-1 focus:ring-[var(--color-focus)]"
                          )}
                        />
                      </label>

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
