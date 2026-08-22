"use client";

import { useState } from "react";
import { Compass, ChevronDown, ChevronUp } from "lucide-react";
import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";
import CustomSelect from "../../ui/CustomSelect.tsx";
import type { QuoteRequestFormState } from "../../../lib/quoteRequestPayload.ts";

type Props = {
  state: QuoteRequestFormState;
  onChange: (updater: (prev: QuoteRequestFormState) => QuoteRequestFormState) => void;
  disabled?: boolean;
};

const THEMES = [
  "Living Heritage",
  "Culinary & Craft",
  "Wild & Secluded",
  "Active Exploration",
  "Art, Architecture & Design",
  "Wellness & Restoration",
];

const TRAVEL_PACES = [
  "Relaxed (More leisure time)",
  "Balanced (Standard immersive pace)",
  "Active / Intensive (High engagement)",
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

export function RequestTravelStyleSection({ state, onChange, disabled = false }: Props) {
  const [isOpen, setIsOpen] = useState(true);

  const hasData =
    Boolean(state.primary_theme) ||
    Boolean(state.travel_pace) ||
    Boolean(state.occasion) ||
    Boolean(state.priority_1) ||
    Boolean(state.priority_2) ||
    Boolean(state.priority_3) ||
    Boolean(state.must_have) ||
    Boolean(state.avoid) ||
    Boolean(state.message);

  return (
    <div className="flex flex-col rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] shadow-[var(--elevation-card)] transition-all">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between gap-3 p-5 text-left transition-colors hover:bg-[var(--color-surface-muted)] cursor-pointer disabled:cursor-not-allowed"
      >
        <div className="flex items-center gap-3">
          <div
            className={cn(
              "flex h-9 w-9 items-center justify-center rounded-full transition-colors",
              hasData
                ? "bg-[var(--color-accent-wash)] text-[var(--color-accent)]"
                : "bg-[var(--color-surface-muted)] text-[var(--color-muted)]"
            )}
          >
            <Compass size={18} aria-hidden="true" />
          </div>
          <div>
            <h3 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)] flex items-center gap-2")}>
              <span>Travel Style & Journey Vision</span>
              <span
                className={cn(
                  getTypographyClassName("caption"),
                  "rounded-full px-2 py-0.5 border transition-colors",
                  hasData
                    ? "bg-[var(--color-accent-wash)] text-[var(--color-accent)] border-[var(--color-accent)]"
                    : "bg-[var(--color-surface-muted)] text-[var(--color-muted)] border-[var(--color-border)]"
                )}
              >
                {hasData ? "Specified" : "Optional"}
              </span>
            </h3>
            <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>
              Select the overarching aesthetic, priorities and experience pace for this journey.
            </p>
          </div>
        </div>
        <div className="text-[var(--color-muted)]">
          {isOpen ? <ChevronUp size={20} aria-hidden="true" /> : <ChevronDown size={20} aria-hidden="true" />}
        </div>
      </button>

      {isOpen ? (
        <div className="flex flex-col gap-4 border-t border-[var(--color-border)] p-5">
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {THEMES.map((theme) => {
              const isSelected = state.primary_theme === theme;
              return (
                <button
                  key={theme}
                  type="button"
                  disabled={disabled}
                  onClick={() => onChange((prev) => ({ ...prev, primary_theme: theme }))}
                  className={cn(
                    "flex items-center justify-center rounded-[var(--radius-button)] border px-3 py-2.5 text-center transition-all cursor-pointer",
                    isSelected
                      ? "border-[var(--color-accent)] bg-[var(--color-accent-wash)] text-[var(--color-accent)] shadow-xs"
                      : "border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-surface-muted)]"
                  )}
                >
                  <span className={cn(getTypographyClassName("bodySm"))}>{theme}</span>
                </button>
              );
            })}
          </div>

          <div className="grid gap-4 sm:grid-cols-2 pt-2">
            <label className="flex flex-col gap-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Travel Pace
              </span>
              <CustomSelect
                options={TRAVEL_PACES.map((p) => ({ id: p, label: p }))}
                value={state.travel_pace}
                onChange={(val) => onChange((prev) => ({ ...prev, travel_pace: val }))}
                placeholder="Select pace"
              />
            </label>

            <Field
              label="Special Occasion"
              placeholder="Birthday, honeymoon, anniversary, family reunion..."
              disabled={disabled}
              value={state.occasion}
              onChange={(val) => onChange((prev) => ({ ...prev, occasion: val }))}
            />
          </div>

          {/* Top Priorities #1, #2, #3 */}
          <div className="grid gap-4 sm:grid-cols-3 pt-2">
            <Field
              label="Top Priority #1"
              placeholder="e.g. Authentic culinary encounters"
              disabled={disabled}
              value={state.priority_1}
              onChange={(val) => onChange((prev) => ({ ...prev, priority_1: val }))}
            />
            <Field
              label="Top Priority #2"
              placeholder="e.g. Crowd-avoidance & seclusion"
              disabled={disabled}
              value={state.priority_2}
              onChange={(val) => onChange((prev) => ({ ...prev, priority_2: val }))}
            />
            <Field
              label="Top Priority #3"
              placeholder="e.g. Deep heritage storytelling"
              disabled={disabled}
              value={state.priority_3}
              onChange={(val) => onChange((prev) => ({ ...prev, priority_3: val }))}
            />
          </div>

          {/* Must-have & Avoid */}
          <div className="grid gap-4 sm:grid-cols-2 pt-2">
            <label className="flex flex-col gap-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Must-have Experiences
              </span>
              <textarea
                rows={2}
                disabled={disabled}
                placeholder="Exclusive artisan access, private Halong cruise, Michelin dining..."
                value={state.must_have}
                onChange={(e) => onChange((prev) => ({ ...prev, must_have: e.target.value }))}
                className={cn(
                  getTypographyClassName("bodyMd"),
                  "w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-3 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
                )}
              />
            </label>

            <label className="flex flex-col gap-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Must Avoid / Deal Breakers
              </span>
              <textarea
                rows={2}
                disabled={disabled}
                placeholder="Mass tourism sites, long van drives, large hotel buffets..."
                value={state.avoid}
                onChange={(e) => onChange((prev) => ({ ...prev, avoid: e.target.value }))}
                className={cn(
                  getTypographyClassName("bodyMd"),
                  "w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-3 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
                )}
              />
            </label>
          </div>

          <label className="flex flex-col gap-2 pt-2">
            <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
              Special Requests & Journey Vision
            </span>
            <textarea
              rows={3}
              disabled={disabled}
              value={state.message}
              onChange={(e) => onChange((prev) => ({ ...prev, message: e.target.value }))}
              placeholder="Share the overarching journey vision, specific highlights, or how you would like the trip to feel…"
              className={cn(
                getTypographyClassName("bodyMd"),
                "w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-3 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
              )}
            />
          </label>
        </div>
      ) : null}
    </div>
  );
}
