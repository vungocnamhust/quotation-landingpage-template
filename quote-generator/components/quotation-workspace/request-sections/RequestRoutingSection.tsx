"use client";

import { getTypographyClassName } from "../../../config/typography";
import { cn } from "../../../utils/cn";
import CustomSelect from "../../ui/CustomSelect";
import { DestinationSelect } from "../../destination/DestinationSelect";
import KidAgesInput from "../KidAgesInput";
import RoomConfigInput from "../RoomConfigInput";
import type { QuoteRequestFormState } from "../../../lib/quoteRequestPayload";

type Props = {
  state: QuoteRequestFormState;
  onChange: (updater: (prev: QuoteRequestFormState) => QuoteRequestFormState) => void;
  disabled?: boolean;
};

const TIMINGS = [
  "Exact dates",
  "Flexible +/- 3 days",
  "Specific month",
  "Specific season",
  "Undecided / Early stage",
];

function Field({
  label,
  value,
  type = "text",
  placeholder,
  required = false,
  disabled = false,
  min,
  onChange,
}: {
  label: string;
  value: string | number;
  type?: string;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  min?: number;
  onChange: (val: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
        {label}
        {required ? <span className="text-[var(--color-accent)] ml-0.5">*</span> : null}
      </span>
      <input
        type={type}
        disabled={disabled}
        required={required}
        placeholder={placeholder}
        min={min}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={cn(
          getTypographyClassName("bodyMd"),
          "min-h-11 w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
        )}
      />
    </label>
  );
}

export function RequestRoutingSection({ state, onChange, disabled = false }: Props) {
  const isTraveller = state.role === "traveller";

  return (
    <section className="flex flex-col gap-5 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] sm:p-6">
      <div className="flex flex-col gap-1">
        <h2 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
          Journey Essentials & Routing
        </h2>
        <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>
          Specify travel destinations, dates, guest party numbers and room configuration.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div className="flex flex-col">
          <DestinationSelect
            label="Destination"
            required
            placeholder="Select or search destination"
            value={state.destination}
            onChange={(val) => {
              const strVal = typeof val === "string" ? val : Array.isArray(val) ? val[0]?.name ?? "" : "";
              onChange((prev) => ({ ...prev, destination: strVal }));
            }}
          />
        </div>

        <label className="flex flex-col gap-2">
          <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
            Date Flexibility
          </span>
          <CustomSelect
            options={TIMINGS.map((t) => ({ id: t, label: t }))}
            value={state.travel_timing}
            onChange={(val) => onChange((prev) => ({ ...prev, travel_timing: val }))}
            placeholder="Select timing flexibility"
          />
        </label>

        {isTraveller ? (
          <>
            <Field
              label="Arrival date"
              type="date"
              disabled={disabled}
              value={state.arrival_date}
              onChange={(val) => onChange((prev) => ({ ...prev, arrival_date: val }))}
            />
            <Field
              label="Departure date"
              type="date"
              disabled={disabled}
              value={state.departure_date}
              onChange={(val) => onChange((prev) => ({ ...prev, departure_date: val }))}
            />
          </>
        ) : (
          <Field
            label="Travel dates / month"
            placeholder="e.g. 09–20 Nov 2026"
            disabled={disabled}
            value={state.raw_dates_text}
            onChange={(val) => onChange((prev) => ({ ...prev, raw_dates_text: val }))}
          />
        )}

        <DestinationSelect
          label="Arrival City"
          placeholder="e.g. Hanoi (HAN)"
          disabled={disabled}
          value={state.arrival_city}
          onChange={(val) => {
            const strVal = typeof val === "string" ? val : Array.isArray(val) ? val[0]?.name ?? "" : "";
            onChange((prev) => ({ ...prev, arrival_city: strVal }));
          }}
        />

        <DestinationSelect
          label="Departure City"
          placeholder="e.g. Ho Chi Minh City (SGN)"
          disabled={disabled}
          value={state.departure_city}
          onChange={(val) => {
            const strVal = typeof val === "string" ? val : Array.isArray(val) ? val[0]?.name ?? "" : "";
            onChange((prev) => ({ ...prev, departure_city: strVal }));
          }}
        />
      </div>

      {/* Routing Constraints Field */}
      <label className="flex flex-col gap-2 border-t border-[var(--color-border)] pt-4">
        <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
          Routing Constraints / Fixed Flights & Dates
        </span>
        <textarea
          rows={2}
          disabled={disabled}
          placeholder="International flights already booked, must be in Hanoi on a specific date, fixed hotel nights, cruise departure..."
          value={state.routing_constraints}
          onChange={(e) => onChange((prev) => ({ ...prev, routing_constraints: e.target.value }))}
          className={cn(
            getTypographyClassName("bodyMd"),
            "w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-3 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
          )}
        />
      </label>

      {/* Pax counters */}
      <div className="grid gap-4 sm:grid-cols-3 border-t border-[var(--color-border)] pt-4">
        <Field
          label="Adults"
          type="number"
          min={1}
          required
          disabled={disabled}
          value={state.adults}
          onChange={(val) =>
            onChange((prev) => ({ ...prev, adults: Math.max(1, parseInt(val, 10) || 1) }))
          }
        />

        <Field
          label="Children (ages 2–11)"
          type="number"
          min={0}
          disabled={disabled}
          value={state.children}
          onChange={(val) => {
            const count = Math.max(0, parseInt(val, 10) || 0);
            onChange((prev) => {
              const currentAges = [...prev.kid_ages];
              while (currentAges.length < count) currentAges.push(6);
              return { ...prev, children: count, kid_ages: currentAges.slice(0, count) };
            });
          }}
        />

        <Field
          label="Infants (under 2)"
          type="number"
          min={0}
          disabled={disabled}
          value={state.infants}
          onChange={(val) =>
            onChange((prev) => ({ ...prev, infants: Math.max(0, parseInt(val, 10) || 0) }))
          }
        />
      </div>

      {/* Dynamic Kid Ages Array Inputs */}
      <KidAgesInput
        childrenCount={state.children}
        kidAges={state.kid_ages}
        onChange={(ages) => onChange((prev) => ({ ...prev, kid_ages: ages }))}
      />

      {/* Smart Room Configuration Input with Presets */}
      <div className="border-t border-[var(--color-border)] pt-4">
        <RoomConfigInput
          value={state.room_configuration}
          adults={state.adults}
          childrenCount={state.children}
          disabled={disabled}
          onChange={(val) => onChange((prev) => ({ ...prev, room_configuration: val }))}
        />
      </div>
    </section>
  );
}
