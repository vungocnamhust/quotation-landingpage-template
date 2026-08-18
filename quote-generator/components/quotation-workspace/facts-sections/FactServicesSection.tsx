"use client";

import { getTypographyClassName } from "../../../config/typography";
import { cn } from "../../../utils/cn";
import { HotelEditorCard } from "./HotelEditorCard";
import type { HotelFact, QuotationFacts, ServiceFact } from "../factsTypes";
import type { MediaWorkspace } from "../MediaSlotRenderer";

const lines = (values: string[]) => values.join("\n");
const toLines = (value: string) => value.split("\n");

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
      <span className={cn(getTypographyClassName("label"), "flex justify-between gap-3 text-[var(--color-muted)]")}>
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

type Props = {
  services: ServiceFact;
  tripStartDate: string | null;
  tripEndDate: string | null;
  activeHotel: number | null;
  readOnly?: boolean;
  onSyncHotelsFromItinerary: () => void;
  onToggleHotel: (index: number) => void;
  onPatchHotel: (index: number, patch: Partial<HotelFact>) => void;
  onRemoveHotel: (index: number) => void;
  onAddHotel: () => void;
  onUpdate: <K extends keyof QuotationFacts>(key: K, value: QuotationFacts[K]) => void;
  mediaWorkspace?: MediaWorkspace;
};

export function FactServicesSection({
  services,
  tripStartDate,
  tripEndDate,
  activeHotel,
  readOnly = false,
  onSyncHotelsFromItinerary,
  onToggleHotel,
  onPatchHotel,
  onRemoveHotel,
  onAddHotel,
  onUpdate,
  mediaWorkspace,
}: Props) {
  return (
    <div className="flex flex-col gap-4">
      {!readOnly ? (
        <div className="flex justify-end mb-1">
          <button
            type="button"
            onClick={onSyncHotelsFromItinerary}
            className={cn(
              getTypographyClassName("buttonSecondary"),
              "min-h-9 rounded-[var(--radius-button)] border border-[var(--color-border)] px-3 py-1 text-[var(--color-accent)] hover:bg-[var(--color-accent-wash)] transition-colors cursor-pointer"
            )}
          >
            ✨ Sync Accommodations from Itinerary Overnights
          </button>
        </div>
      ) : null}

      {services.hotels.map((hotel, index) => (
        <HotelEditorCard
          key={index}
          hotel={hotel}
          index={index}
          startDate={tripStartDate}
          endDate={tripEndDate}
          open={activeHotel === index}
          readOnly={readOnly}
          onToggle={onToggleHotel}
          onPatch={onPatchHotel}
          onRemove={onRemoveHotel}
          mediaWorkspace={mediaWorkspace}
        />
      ))}

      {!readOnly ? (
        <button
          type="button"
          onClick={onAddHotel}
          className={cn(
            getTypographyClassName("buttonSecondary"),
            "min-h-14 rounded-[var(--radius-button)] border-2 border-dashed border-[var(--color-accent)] bg-[color-mix(in_srgb,var(--color-accent-wash)_60%,white)] px-4 text-[var(--color-accent)] transition-all duration-200 hover:bg-[var(--color-accent)] hover:text-white hover:shadow-xs cursor-pointer"
          )}
        >
          + Add hotel
        </button>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2">
        <Area
          label="Inclusions"
          disabled={readOnly}
          value={lines(services.inclusions)}
          onChange={(value) =>
            onUpdate("service_facts", {
              ...services,
              inclusions: toLines(value),
            })
          }
          hint="One factual item per line."
        />
        <Area
          label="Exclusions"
          disabled={readOnly}
          value={lines(services.exclusions)}
          onChange={(value) =>
            onUpdate("service_facts", {
              ...services,
              exclusions: toLines(value),
            })
          }
          hint="One factual item per line."
        />
      </div>

      <Area
        label="Room Notes & Special Requests"
        disabled={readOnly}
        value={services.room_notes}
        onChange={(value) =>
          onUpdate("service_facts", {
            ...services,
            room_notes: value || null,
          })
        }
      />
    </div>
  );
}
