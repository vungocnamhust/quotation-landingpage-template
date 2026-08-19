"use client";

import { memo } from "react";
import { getTypographyClassName } from "../../../config/typography";
import { cn } from "../../../utils/cn";
import { DestinationSelect } from "../../destination/DestinationSelect";
import { AccommodationSelect } from "../../accommodation/AccommodationSelect";
import type { AccommodationProfile } from "../../accommodation/types";
import type { ItineraryDayFact } from "../factsTypes";
import { dateForItineraryDay } from "../factsTypes";
import { MediaSlotRenderer, type MediaWorkspace } from "../MediaSlotRenderer";
import { inferOvernightDestination } from "../../../lib/prefillRules";

const lines = (values: string[]) => values.join("\n");
const toLines = (value: string) => value.split("\n");

const inputClass = cn(
  getTypographyClassName("bodyMd"),
  "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] transition-shadow duration-200 focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
);

function Field({
  id,
  label,
  value,
  placeholder,
  onChange,
  type = "text",
  disabled,
  required,
}: {
  id?: string;
  label: string;
  value: string | number | null;
  placeholder?: string;
  onChange: (value: string) => void;
  type?: string;
  disabled?: boolean;
  required?: boolean;
}) {
  return (
    <label className="flex flex-col gap-2">
      <span
        className={cn(
          getTypographyClassName("label"),
          "flex justify-between gap-3 text-[var(--color-muted)]"
        )}
      >
        <span>{label}</span>
        <span
          className={cn(
            getTypographyClassName("caption"),
            required ? "text-[var(--color-accent)]" : "text-[var(--color-muted)]"
          )}
        >
          {required ? "Required" : "Optional"}
        </span>
      </span>
      <input
        id={id}
        aria-required={required}
        placeholder={placeholder}
        className={inputClass}
        type={type}
        disabled={disabled}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );

}

function Area({
  label,
  value,
  onChange,
  hint,
  disabled,
}: {
  label: string;
  value: string | null;
  onChange: (value: string) => void;
  hint?: string;
  disabled?: boolean;
}) {
  return (
    <label className="flex flex-col gap-2">
      <span
        className={cn(
          getTypographyClassName("label"),
          "flex justify-between gap-3 text-[var(--color-muted)]"
        )}
      >
        <span>{label}</span>
        {hint ? (
          <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
            {hint}
          </span>
        ) : null}
      </span>
      <textarea
        rows={4}
        disabled={disabled}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        className={cn(
          getTypographyClassName("bodyMd"),
          "rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-3 text-[var(--color-on-surface)] transition-shadow duration-200 focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
        )}
      />
    </label>
  );
}

export type DayEditorCardProps = {
  day: ItineraryDayFact;
  index: number;
  startDate: string | null;
  open: boolean;
  readOnly: boolean;
  onToggle: (index: number) => void;
  onPatch: (index: number, patch: Partial<ItineraryDayFact>) => void;
  onRemove: (index: number) => void;
  mediaWorkspace?: MediaWorkspace;
};

export const DayEditorCard = memo(function DayEditorCard({
  day,
  index,
  startDate,
  open,
  readOnly,
  onToggle,
  onPatch,
  onRemove,
  mediaWorkspace,
}: DayEditorCardProps) {
  const patch = <K extends keyof ItineraryDayFact>(
    key: K,
    value: ItineraryDayFact[K]
  ) => onPatch(index, { [key]: value } as Partial<ItineraryDayFact>);

  const complete = Boolean(
    day.destination && (day.summary || day.highlights.length)
  );
  const derivedDate =
    day.display_date ||
    dateForItineraryDay(startDate, day.day_number ?? index + 1);

  return (
    <article
      id={`facts-day-${index}`}
      className={cn(
        "facts-repeatable content-visibility-auto rounded-[var(--radius-card)] transition-all duration-200",
        open
          ? "border-2 border-[var(--color-accent)] border-l-4 border-l-[var(--color-accent)] bg-[var(--color-surface-white)] shadow-md"
          : "border border-[var(--color-border-strong)] bg-[var(--color-surface-white)] hover:border-[var(--color-accent)] shadow-2xs"
      )}
    >
      <button
        type="button"
        onClick={() => onToggle(index)}
        aria-expanded={open}
        className={cn(
          "flex min-h-14 w-full items-center justify-between gap-3 px-4 text-left transition-colors focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[var(--color-focus)]",
          open
            ? "rounded-t-[calc(var(--radius-card)-2px)] bg-[color-mix(in_srgb,var(--color-accent-wash)_45%,var(--color-surface-white))]"
            : "rounded-[var(--radius-card)] hover:bg-[var(--color-surface-hover)]"
        )}
      >
        <span className="min-w-0">
          <span
            className={cn(
              getTypographyClassName("cardTitle"),
              "block text-[var(--color-on-surface)]"
            )}
          >
            Day {day.day_number ?? index + 1}
            {derivedDate ? ` · ${derivedDate}` : ""}
          </span>
          <span
            className={cn(
              getTypographyClassName("caption"),
              "block truncate text-[var(--color-muted)]"
            )}
          >
            {day.destination || "Destination needed"}
            {day.accommodation_name ? ` · 🏨 ${day.accommodation_name}` : ""}
          </span>
        </span>
        <span
          className={cn(
            getTypographyClassName("caption"),
            "rounded-full px-2.5 py-0.5 shrink-0",
            complete
              ? "bg-[var(--color-accent-wash)] text-[var(--color-accent)]"
              : "bg-[var(--color-surface-muted)] text-[var(--color-muted)]"
          )}
        >
          {complete ? "Ready" : "Needs facts"}
        </span>
      </button>

      {open ? (
        <div className="facts-accordion-body grid gap-4 border-t border-[var(--color-border-strong)] bg-[var(--color-surface-white)] p-4 sm:grid-cols-2">
          {/* ESSENTIAL FIELDS */}
          <Field
            id={`day-${index}-number`}
            label="Day"
            required
            type="number"
            disabled={readOnly}
            value={day.day_number}
            onChange={(value) => {
              const dayNumber = Number(value) || null;
              onPatch(index, {
                day_number: dayNumber,
                display_date: dateForItineraryDay(startDate, dayNumber),
              });
            }}
          />
          <DestinationSelect
            label={`Day ${day.day_number ?? index + 1} destination`}
            disabled={readOnly}
            value={day.destination}
            onChange={(name, ref) => {
              const destName =
                typeof name === "string"
                  ? name
                  : Array.isArray(name)
                    ? name[0]?.name ?? null
                    : null;
              onPatch(index, {
                destination: destName,
                destination_ref: ref ?? null,
                overnight: inferOvernightDestination(destName, day.overnight),
              });
            }}
          />
          <DestinationSelect
            label="Overnight"
            disabled={readOnly}
            value={day.overnight}
            onChange={(name) => {
              const overnightName =
                typeof name === "string"
                  ? name
                  : Array.isArray(name)
                    ? name[0]?.name ?? null
                    : null;
              patch("overnight", overnightName);
            }}
          />

          {/* OVERNIGHT ACCOMMODATION / HOTEL */}
          <div className="sm:col-span-2 flex flex-col gap-2 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] p-3.5">
            <div className="flex items-center justify-between gap-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-on-surface)]")}>
                Overnight Accommodation
              </span>
              {day.accommodation_name ? (
                <span className={cn(getTypographyClassName("caption"), "rounded-full bg-emerald-50 text-emerald-700 px-2.5 py-0.5 border border-emerald-200")}>
                  🏨 {day.accommodation_name} {day.room_type ? `(${day.room_type})` : ""}
                </span>
              ) : (
                <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
                  Optional overnight stay
                </span>
              )}
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <AccommodationSelect
                label="Select Hotel"
                value={day.accommodation_id ?? null}
                name={day.accommodation_name ?? null}
                destination={day.destination || day.overnight}
                destinationId={day.destination_ref?.id}
                disabled={readOnly}
                variant="compact"
                size="md"
                onChange={(profile: AccommodationProfile | null) => {
                  onPatch(index, {
                    accommodation_id: profile?.id ?? null,
                    accommodation_name: profile?.name ?? null,
                    room_type: profile?.room_type ?? day.room_type ?? null,
                  });
                }}
              />

              <Field
                label="Room type"
                placeholder="e.g. Deluxe Heritage Room"
                disabled={readOnly}
                value={day.room_type ?? ""}
                onChange={(value) => patch("room_type", value || null)}
              />
            </div>
          </div>
          <div className="sm:col-span-2 grid gap-4 sm:grid-cols-2">
            <Area
              label="Programme summary"
              disabled={readOnly}
              value={day.summary}
              onChange={(value) => patch("summary", value || null)}
              hint="Required for an AI day narrative when no highlights are supplied."
            />
            <Area
              label="Highlights"
              disabled={readOnly}
              value={lines(day.highlights)}
              onChange={(value) => patch("highlights", toLines(value))}
              hint="One factual item per line."
            />
          </div>

          <Field
            label="Sense of pace"
            disabled={readOnly}
            value={day.sense_of_pace}
            onChange={(value) =>
              patch(
                "sense_of_pace",
                (value || null) as ItineraryDayFact["sense_of_pace"]
              )
            }
          />
          <Field
            label="Display date"
            placeholder="e.g. Day 1 · 09 Nov 2026"
            disabled={readOnly}
            value={day.display_date}
            onChange={(value) => patch("display_date", value || null)}
          />

          <div className="sm:col-span-2">
            <Area
              label="Meals"
              disabled={readOnly}
              value={lines(day.meals)}
              onChange={(value) => patch("meals", toLines(value))}
              hint="One meal item per line (e.g. Breakfast, Lunch)."
            />
          </div>
          <div className="sm:col-span-2">
            <Area
              label="Notes"
              disabled={readOnly}
              value={lines(day.notes)}
              onChange={(value) => patch("notes", toLines(value))}
              hint="One operational note per line."
            />
          </div>
          {mediaWorkspace ? (
            <MediaSlotRenderer
              workspace={mediaWorkspace}
              editorRoute="facts.programme.day"
              readOnly={readOnly}
              context={{
                index,
                destinationId: day.destination_ref?.id,
              }}
            />
          ) : null}
          {!readOnly ? (
            <button
              type="button"
              onClick={() => onRemove(index)}
              className={cn(
                getTypographyClassName("buttonSecondary"),
                "min-h-10 w-fit rounded-[var(--radius-button)] bg-rose-700 !text-white hover:bg-rose-800 px-4 shadow-2xs border border-transparent transition-all cursor-pointer"
              )}
            >
              Remove day
            </button>
          ) : null}
        </div>
      ) : null}
    </article>
  );
});
