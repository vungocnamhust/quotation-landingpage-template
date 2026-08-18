"use client";

import { useState } from "react";
import { Building2, ChevronDown, ChevronUp } from "lucide-react";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";
import CustomSelect from "../ui/CustomSelect";

export type AccommodationScopeState = {
  hotel_level: string;
  preferred_hotel: string;
  room_type: string;
  bedding: string;
  connecting: string;
  suite_interest: string;
  hotel_style: string;
};

type Props = {
  state: AccommodationScopeState;
  onChange: (updater: (prev: AccommodationScopeState) => AccommodationScopeState) => void;
  disabled?: boolean;
};

const HOTEL_LEVELS = ["4-star", "5-star", "Luxury", "Boutique", "Mixed"];
const CONNECTING_OPTIONS = ["Yes", "No"];
const SUITE_INTEREST_OPTIONS = [
  "No preference",
  "Consider upgrades",
  "Suite preferred",
  "Villa preferred",
];

const inputClass = cn(
  getTypographyClassName("bodyMd"),
  "min-h-11 w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
);

export default function AccommodationScopeSection({
  state,
  onChange,
  disabled = false,
}: Props) {
  const [isOpen, setIsOpen] = useState(false);

  const hasData =
    Boolean(state.hotel_level) ||
    Boolean(state.preferred_hotel) ||
    Boolean(state.room_type) ||
    Boolean(state.bedding) ||
    Boolean(state.connecting) ||
    Boolean(state.suite_interest) ||
    Boolean(state.hotel_style);

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
            <Building2 size={18} aria-hidden="true" />
          </div>
          <div>
            <h3 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)] flex items-center gap-2")}>
              <span>Accommodation & Hotel Requirements</span>
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
              Specify star level, suite preference, room types and hotel style.
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
                Hotel Level
              </span>
              <CustomSelect
                options={HOTEL_LEVELS.map((lvl) => ({ id: lvl, label: lvl }))}
                value={state.hotel_level}
                onChange={(val) => onChange((prev) => ({ ...prev, hotel_level: val }))}
                placeholder="Select hotel tier"
              />
            </label>

            <label className="flex flex-col gap-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Preferred Hotel / Brand
              </span>
              <input
                type="text"
                disabled={disabled}
                placeholder="e.g. Capella, Aman, Six Senses, Sofitel Legend..."
                value={state.preferred_hotel}
                onChange={(e) => onChange((prev) => ({ ...prev, preferred_hotel: e.target.value }))}
                className={inputClass}
              />
            </label>

            <label className="flex flex-col gap-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Room Category / Type
              </span>
              <input
                type="text"
                disabled={disabled}
                placeholder="e.g. Deluxe City View, Premier Oceanfront..."
                value={state.room_type}
                onChange={(e) => onChange((prev) => ({ ...prev, room_type: e.target.value }))}
                className={inputClass}
              />
            </label>

            <label className="flex flex-col gap-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Bedding Preference
              </span>
              <input
                type="text"
                disabled={disabled}
                placeholder="King / Twin / Double..."
                value={state.bedding}
                onChange={(e) => onChange((prev) => ({ ...prev, bedding: e.target.value }))}
                className={inputClass}
              />
            </label>

            <label className="flex flex-col gap-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Connecting / Family Rooms?
              </span>
              <CustomSelect
                options={CONNECTING_OPTIONS.map((c) => ({ id: c, label: c }))}
                value={state.connecting}
                onChange={(val) => onChange((prev) => ({ ...prev, connecting: val }))}
                placeholder="Select option"
              />
            </label>

            <label className="flex flex-col gap-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Upgrade / Suite Interest
              </span>
              <CustomSelect
                options={SUITE_INTEREST_OPTIONS.map((s) => ({ id: s, label: s }))}
                value={state.suite_interest}
                onChange={(val) => onChange((prev) => ({ ...prev, suite_interest: val }))}
                placeholder="Select preference"
              />
            </label>

            <label className="flex flex-col gap-2 sm:col-span-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Hotel Style / Aesthetic
              </span>
              <textarea
                rows={3}
                disabled={disabled}
                placeholder="Heritage, contemporary, resort-led, design-forward, secluded, city-centre, riverfront..."
                value={state.hotel_style}
                onChange={(e) => onChange((prev) => ({ ...prev, hotel_style: e.target.value }))}
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
