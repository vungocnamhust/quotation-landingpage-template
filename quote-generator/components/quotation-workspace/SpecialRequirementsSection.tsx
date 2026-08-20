"use client";

import { useState } from "react";
import { HeartPulse, ChevronDown, ChevronUp } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";

export type SpecialRequirementsState = {
  dietary: string;
  halal: string;
  mobility: string;
  health_considerations: string;
};

type Props = {
  state: SpecialRequirementsState;
  onChange: (updater: (prev: SpecialRequirementsState) => SpecialRequirementsState) => void;
  disabled?: boolean;
};

export default function SpecialRequirementsSection({
  state,
  onChange,
  disabled = false,
}: Props) {
  const [isOpen, setIsOpen] = useState(false);

  const hasData =
    Boolean(state.dietary) ||
    Boolean(state.halal) ||
    Boolean(state.mobility) ||
    Boolean(state.health_considerations);

  return (
    <div className="flex flex-col rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] shadow-[var(--elevation-card)] transition-all">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between gap-3 p-5 text-left transition-colors hover:bg-[var(--color-surface-muted)] cursor-pointer disabled:cursor-not-allowed"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--color-surface-muted)] text-[var(--color-accent)]">
            <HeartPulse size={18} aria-hidden="true" />
          </div>
          <div>
            <h3 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)] flex items-center gap-2")}>
              <span>Special, Dietary & Health Requirements</span>
              <span
                className={cn(
                  getTypographyClassName("caption"),
                  "rounded-full px-2 py-0.5 border",
                  hasData
                    ? "bg-[var(--color-accent-wash)] text-[var(--color-accent)] border-[var(--color-accent)]"
                    : "bg-[var(--color-surface-muted)] text-[var(--color-muted)] border-[var(--color-border)]"
                )}
              >
                {hasData ? "Specified" : "Optional"}
              </span>
            </h3>
            <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>
              Dietary restrictions, halal requirements, mobility needs & health considerations.
            </p>
          </div>
        </div>
        <div className="text-[var(--color-muted)]">
          {isOpen ? <ChevronUp size={20} aria-hidden="true" /> : <ChevronDown size={20} aria-hidden="true" />}
        </div>
      </button>

      {isOpen ? (
        <div className="flex flex-col gap-4 border-t border-[var(--color-border)] p-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="flex flex-col gap-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Dietary Requirements & Allergies
              </span>
              <textarea
                rows={2}
                disabled={disabled}
                placeholder="Severe nut allergy, vegetarian, gluten-free, seafood-free..."
                value={state.dietary}
                onChange={(e) => onChange((prev) => ({ ...prev, dietary: e.target.value }))}
                className={cn(
                  getTypographyClassName("bodyMd"),
                  "w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-3 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
                )}
              />
            </label>

            <label className="flex flex-col gap-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Halal & Religious Requirements
              </span>
              <textarea
                rows={2}
                disabled={disabled}
                placeholder="Halal food only, pork-free, alcohol-free, Qibla/prayer room access..."
                value={state.halal}
                onChange={(e) => onChange((prev) => ({ ...prev, halal: e.target.value }))}
                className={cn(
                  getTypographyClassName("bodyMd"),
                  "w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-3 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
                )}
              />
            </label>

            <label className="flex flex-col gap-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Mobility & Accessibility Needs
              </span>
              <textarea
                rows={2}
                disabled={disabled}
                placeholder="Ground floor rooms, wheelchair assistance, low-stair walking tours..."
                value={state.mobility}
                onChange={(e) => onChange((prev) => ({ ...prev, mobility: e.target.value }))}
                className={cn(
                  getTypographyClassName("bodyMd"),
                  "w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-3 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
                )}
              />
            </label>

            <label className="flex flex-col gap-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Medical & Health Considerations
              </span>
              <textarea
                rows={2}
                disabled={disabled}
                placeholder="Relevant medical conditions for planning safely (e.g. motion sickness, altitude sensitivity)..."
                value={state.health_considerations}
                onChange={(e) => onChange((prev) => ({ ...prev, health_considerations: e.target.value }))}
                className={cn(
                  getTypographyClassName("bodyMd"),
                  "w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-3 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
                )}
              />
            </label>
          </div>
        </div>
      ) : null}
    </div>
  );
}
