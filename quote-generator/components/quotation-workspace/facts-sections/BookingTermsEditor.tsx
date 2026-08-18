"use client";

import { getTypographyClassName } from "../../../config/typography";
import { cn } from "../../../utils/cn";
import type { BookingFact, BookingItemFact } from "../factsTypes";

const inputClass = cn(
  getTypographyClassName("bodyMd"),
  "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] transition-shadow duration-200 focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
);

function Field({
  id,
  label,
  value,
  onChange,
  type = "text",
  disabled,
}: {
  id?: string;
  label: string;
  value: string | number | null;
  onChange: (value: string) => void;
  type?: string;
  disabled?: boolean;
}) {
  return (
    <label className="flex flex-col gap-2">
      <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
        {label}
      </span>
      <input
        id={id}
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
      <span className={cn(getTypographyClassName("label"), "flex justify-between gap-3 text-[var(--color-muted)]")}>
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

type Props = {
  booking: BookingFact;
  readOnly?: boolean;
  onChange: (next: BookingFact) => void;
};

export function BookingTermsEditor({ booking, readOnly = false, onChange }: Props) {
  const handleAddTerm = () => {
    onChange({
      ...booking,
      items: [...booking.items, { key: null, label: "Deposit", body: null }],
    });
  };

  const handleRemoveTerm = (index: number) => {
    onChange({
      ...booking,
      items: booking.items.filter((_: BookingItemFact, i: number) => i !== index),
    });
  };

  const handleUpdateLabel = (index: number, label: string) => {
    onChange({
      ...booking,
      items: booking.items.map((item: BookingItemFact, i: number) =>
        i === index ? { ...item, label: label || null } : item
      ),
    });
  };

  const handleUpdateBody = (index: number, body: string) => {
    onChange({
      ...booking,
      items: booking.items.map((item: BookingItemFact, i: number) =>
        i === index ? { ...item, body: body || null } : item
      ),
    });
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <p className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
          Booking term details (Key & Value)
        </p>
        {!readOnly ? (
          <button
            type="button"
            onClick={handleAddTerm}
            className={cn(
              getTypographyClassName("buttonSecondary"),
              "min-h-8 rounded-[var(--radius-button)] border border-[var(--color-border)] px-3 py-1 text-[var(--color-on-surface)] hover:bg-[var(--color-surface-muted)] transition-colors cursor-pointer"
            )}
          >
            + Add term
          </button>
        ) : null}
      </div>

      {booking.items.map((item: BookingItemFact, index: number) => (
        <div
          id={`booking-term-${index}`}
          key={item.key ?? index}
          className="grid gap-3 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-white)] p-4 shadow-2xs sm:grid-cols-12 items-start"
        >
          <div className="sm:col-span-4 flex flex-col gap-2">
            <Field
              id={`booking-term-${index}-label`}
              label="Term label (Key)"
              disabled={readOnly}
              value={item.label}
              onChange={(value) => handleUpdateLabel(index, value)}
            />
            {!readOnly ? (
              <div className="flex flex-wrap gap-1 mt-1">
                <button
                  type="button"
                  onClick={() => handleUpdateLabel(index, "Deposit")}
                  className={cn(
                    getTypographyClassName("caption"),
                    "px-2 py-0.5 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-muted)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-on-surface)] transition-colors cursor-pointer"
                  )}
                >
                  + Deposit
                </button>
                <button
                  type="button"
                  onClick={() => handleUpdateLabel(index, "Balance")}
                  className={cn(
                    getTypographyClassName("caption"),
                    "px-2 py-0.5 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-muted)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-on-surface)] transition-colors cursor-pointer"
                  )}
                >
                  + Balance
                </button>
                <button
                  type="button"
                  onClick={() => handleUpdateLabel(index, "Cancellation")}
                  className={cn(
                    getTypographyClassName("caption"),
                    "px-2 py-0.5 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-muted)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-on-surface)] transition-colors cursor-pointer"
                  )}
                >
                  + Cancellation
                </button>
              </div>
            ) : null}
          </div>

          <div className="sm:col-span-8 flex flex-col gap-2">
            <Area
              label="Term body (plain text)"
              hint="HTML is not supported."
              disabled={readOnly}
              value={item.body}
              onChange={(value) => handleUpdateBody(index, value)}
            />
            {!readOnly ? (
              <div className="flex justify-end mt-1">
                <button
                  type="button"
                  onClick={() => handleRemoveTerm(index)}
                  className={cn(getTypographyClassName("caption"), "text-rose-600 hover:underline cursor-pointer")}
                >
                  Remove term
                </button>
              </div>
            ) : null}
          </div>
        </div>
      ))}
    </div>
  );
}
