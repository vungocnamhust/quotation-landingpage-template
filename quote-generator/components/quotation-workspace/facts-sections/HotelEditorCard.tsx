"use client";

import { memo } from "react";
import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";
import { DestinationSelect } from "../../destination/DestinationSelect.tsx";
import { AccommodationSelect } from "../../accommodation/AccommodationSelect.tsx";
import { DateInput } from "../../date/index.ts";
import type { AccommodationProfile } from "../../accommodation/types.ts";
import type { HotelFact } from "../factsTypes.ts";
import { MediaSlotRenderer, type MediaWorkspace } from "../MediaSlotRenderer.tsx";
import { validateHotelDates } from "../../../lib/prefillRules.ts";

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
  min,
  max,
}: {
  id?: string;
  label: string;
  value: string | number | null;
  placeholder?: string;
  onChange: (value: string) => void;
  type?: string;
  disabled?: boolean;
  required?: boolean;
  min?: string | number;
  max?: string | number;
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
        min={min}
        max={max}
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
        rows={3}
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

export function hotelFromProfile(
  profile: AccommodationProfile,
  existingHotel?: Partial<HotelFact>
): HotelFact {
  return {
    accommodation_id: profile.id,
    destination: profile.destination,
    destination_ref: profile.destination_ref,
    name: profile.name,
    room_type: profile.room_type,
    check_in: existingHotel?.check_in ?? null,
    check_out: existingHotel?.check_out ?? null,
    intro: profile.intro || existingHotel?.intro || "Breakfast included.",
    phone: profile.phone || existingHotel?.phone || null,
    display_city: profile.display_city || existingHotel?.display_city || null,
    display_date: existingHotel?.display_date ?? null,
    hotel_asset: profile.hotel_asset,
    room_asset: profile.room_asset,
  };
}

export type HotelEditorCardProps = {
  hotel: HotelFact;
  index: number;
  startDate: string | null;
  endDate: string | null;
  open: boolean;
  readOnly: boolean;
  onToggle: (index: number) => void;
  onPatch: (index: number, patch: Partial<HotelFact>) => void;
  onRemove: (index: number) => void;
  mediaWorkspace?: MediaWorkspace;
};

export const HotelEditorCard = memo(function HotelEditorCard({
  hotel,
  index,
  startDate,
  endDate,
  open,
  readOnly,
  onToggle,
  onPatch,
  onRemove,
  mediaWorkspace,
}: HotelEditorCardProps) {
  const patch = <K extends keyof HotelFact>(key: K, value: HotelFact[K]) =>
    onPatch(index, { [key]: value } as Partial<HotelFact>);

  const complete = Boolean(hotel.name && hotel.destination);
  const dateValidation = validateHotelDates(
    hotel.check_in,
    hotel.check_out,
    startDate,
    endDate
  );

  return (
    <article
      id={`facts-hotel-${index}`}
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
              "block truncate text-[var(--color-on-surface)]"
            )}
          >
            {hotel.name || `Hotel ${index + 1}`}
          </span>
          <span
            className={cn(
              getTypographyClassName("caption"),
              "block truncate text-[var(--color-muted)]"
            )}
          >
            {hotel.destination || "Destination needed"}
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
          <div className="sm:col-span-2">
            <AccommodationSelect
              label="Select Pre-configured Accommodation"
              value={hotel.accommodation_id}
              name={hotel.name}
              destination={hotel.destination || hotel.display_city}
              destinationId={hotel.destination_ref?.id}
              disabled={readOnly}
              onChange={(profile, id, customName) => {
                if (profile) {
                  onPatch(index, hotelFromProfile(profile, hotel));
                } else if (customName) {
                  onPatch(index, {
                    ...hotel,
                    accommodation_id: null,
                    name: customName,
                  });
                } else {
                  patch("accommodation_id", null);
                }
              }}
            />
          </div>

          {/* ESSENTIAL FIELDS */}
          <DestinationSelect
            label={`Hotel ${index + 1} destination`}
            disabled={readOnly}
            value={hotel.destination}
            onChange={(name, ref) => {
              const destName =
                typeof name === "string"
                  ? name
                  : Array.isArray(name)
                    ? name[0]?.name ?? null
                    : null;
              patch("destination", destName);
              patch("destination_ref", ref ?? null);
            }}
          />
          <Field
            id={`hotel-${index}-name`}
            label="Hotel name"
            disabled={readOnly}
            value={hotel.name}
            onChange={(value) => patch("name", value || null)}
          />
          <Field
            label="Room type"
            disabled={readOnly}
            value={hotel.room_type}
            onChange={(value) => patch("room_type", value || null)}
          />
          <DateInput
            label="Check-in"
            mode="iso"
            min={startDate ?? undefined}
            max={endDate ?? undefined}
            disabled={readOnly}
            value={hotel.check_in}
            onChange={(value) => patch("check_in", value || null)}
          />
          <DateInput
            label="Check-out"
            mode="iso"
            min={hotel.check_in ?? startDate ?? undefined}
            max={endDate ?? undefined}
            disabled={readOnly}
            value={hotel.check_out}
            onChange={(value) => patch("check_out", value || null)}
          />
          {!dateValidation.valid ? (
            <p
              className={cn(
                getTypographyClassName("caption"),
                "sm:col-span-2 rounded-[var(--radius-button)] border border-rose-500/30 bg-rose-500/10 p-2 text-rose-700"
              )}
            >
              {dateValidation.message}
            </p>
          ) : null}
          <div className="sm:col-span-2">
            <Area
              label="Stay notes"
              disabled={readOnly}
              value={hotel.intro}
              onChange={(value) => patch("intro", value || null)}
            />
          </div>

          <Field
            label="Hotel phone"
            disabled={readOnly}
            value={hotel.phone}
            onChange={(value) => patch("phone", value || null)}
          />
          <Field
            label="Display city"
            disabled={readOnly}
            value={hotel.display_city}
            onChange={(value) => patch("display_city", value || null)}
          />
          <Field
            label="Display dates"
            placeholder="e.g. 09 Nov – 12 Nov 2026"
            disabled={readOnly}
            value={hotel.display_date}
            onChange={(value) => patch("display_date", value || null)}
          />

          {mediaWorkspace ? (
            <MediaSlotRenderer
              workspace={mediaWorkspace}
              editorRoute="facts.services.hotel"
              readOnly={readOnly}
              context={{
                index,
                entityId: hotel.id,
                destinationId: hotel.destination_ref?.id,
                accommodationName: hotel.name ?? undefined,
                profileAssetKeys: {
                  [`stays.hotels.${hotel.id ?? index}.hotelImage`]: hotel.hotel_asset,
                  [`stays.hotels.${hotel.id ?? index}.roomImage`]: hotel.room_asset,
                },
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
              Remove hotel
            </button>
          ) : null}
        </div>
      ) : null}
    </article>
  );
});
