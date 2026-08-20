"use client";

import { useState } from "react";
import { Compass, ChevronDown, ChevronUp } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import CustomSelect from "../ui/CustomSelect.tsx";

export type ServiceScopeState = {
  // Transport & Guiding
  private_vehicle: string;
  vehicle_preference: string;
  guide_language: string;
  guide_scope: string;

  // Flights & Rail/Cruise
  domestic_flights: string;
  intl_flights: string;
  rail_cruise: string;
  transport_class: string;

  // Meals & Activities
  meal_plan: string;
  dining_level: string;
  experiences_included: string;
  optional_activities: string;

  // Ancillary
  visa_fasttrack: string;
  meet_assist: string;
  insurance: string;
  other_services: string;
};

type Props = {
  state: ServiceScopeState;
  onChange: (updater: (prev: ServiceScopeState) => ServiceScopeState) => void;
  disabled?: boolean;
};

const YES_NO_PARTIAL = ["Yes", "No", "Partial"];
const YES_NO_SEPARATE = ["Yes", "No", "Quote separately"];
const GUIDE_SCOPES = [
  "Full-trip guide",
  "Local guides by destination",
  "Selected touring days only",
  "No guide",
];
const MEAL_PLANS = [
  "Breakfast only",
  "Half board",
  "Full board",
  "Selected meals only",
  "Flexible / à la carte",
];
const EXPERIENCES_SCOPES = [
  "All planned experiences",
  "Core experiences only",
  "Quote options separately",
];
const MEET_ASSIST_OPTIONS = ["Yes", "No", "VIP if available"];
const INSURANCE_OPTIONS = ["Yes", "No", "Recommend only"];

const inputClass = cn(
  getTypographyClassName("bodyMd"),
  "min-h-11 w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
);

export default function ServiceScopeSection({
  state,
  onChange,
  disabled = false,
}: Props) {
  const [isOpen, setIsOpen] = useState(false);

  const hasData =
    Boolean(state.private_vehicle) ||
    Boolean(state.guide_scope) ||
    Boolean(state.domestic_flights) ||
    Boolean(state.intl_flights) ||
    Boolean(state.meal_plan) ||
    Boolean(state.visa_fasttrack) ||
    Boolean(state.meet_assist) ||
    Boolean(state.insurance);

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
            <Compass size={18} aria-hidden="true" />
          </div>
          <div>
            <h3 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)] flex items-center gap-2")}>
              <span>Service Scope for Costing</span>
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
              Define inclusions: private vehicles, guide languages, flights, meals & VIP fast-track.
            </p>
          </div>
        </div>
        <div className="text-[var(--color-muted)]">
          {isOpen ? <ChevronUp size={20} aria-hidden="true" /> : <ChevronDown size={20} aria-hidden="true" />}
        </div>
      </button>

      {isOpen ? (
        <div className="flex flex-col gap-6 border-t border-[var(--color-border)] p-5">
          {/* 1. Transportation & Guiding */}
          <div className="flex flex-col gap-3">
            <h4 className={cn(getTypographyClassName("label"), "text-[var(--color-accent)]")}>
              Transportation & Guiding
            </h4>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  Private Vehicle Required?
                </span>
                <CustomSelect
                  options={YES_NO_PARTIAL.map((v) => ({ id: v, label: v }))}
                  value={state.private_vehicle}
                  onChange={(val) => onChange((prev) => ({ ...prev, private_vehicle: val }))}
                  placeholder="Select vehicle need"
                />
              </label>

              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  Vehicle Preference / Size
                </span>
                <input
                  type="text"
                  disabled={disabled}
                  placeholder="e.g. 7-seat SUV / VIP Van / Luxury Coach"
                  value={state.vehicle_preference}
                  onChange={(e) => onChange((prev) => ({ ...prev, vehicle_preference: e.target.value }))}
                  className={inputClass}
                />
              </label>

              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  Guide Scope
                </span>
                <CustomSelect
                  options={GUIDE_SCOPES.map((g) => ({ id: g, label: g }))}
                  value={state.guide_scope}
                  onChange={(val) => onChange((prev) => ({ ...prev, guide_scope: val }))}
                  placeholder="Select guide scope"
                />
              </label>

              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  Guide Language
                </span>
                <input
                  type="text"
                  disabled={disabled}
                  placeholder="e.g. English, French, Spanish, Arabic..."
                  value={state.guide_language}
                  onChange={(e) => onChange((prev) => ({ ...prev, guide_language: e.target.value }))}
                  className={inputClass}
                />
              </label>
            </div>
          </div>

          <hr className="border-[var(--color-border)]" />

          {/* 2. Flights, Rail & Boats */}
          <div className="flex flex-col gap-3">
            <h4 className={cn(getTypographyClassName("label"), "text-[var(--color-accent)]")}>
              Flights, Rail & Boats
            </h4>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  Domestic Flights Included?
                </span>
                <CustomSelect
                  options={YES_NO_SEPARATE.map((v) => ({ id: v, label: v }))}
                  value={state.domestic_flights}
                  onChange={(val) => onChange((prev) => ({ ...prev, domestic_flights: val }))}
                  placeholder="Select flight policy"
                />
              </label>

              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  International Flights Included?
                </span>
                <CustomSelect
                  options={YES_NO_SEPARATE.map((v) => ({ id: v, label: v }))}
                  value={state.intl_flights}
                  onChange={(val) => onChange((prev) => ({ ...prev, intl_flights: val }))}
                  placeholder="Select intl flight policy"
                />
              </label>

              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  Rail / Cruise / Boat Requirements
                </span>
                <input
                  type="text"
                  disabled={disabled}
                  placeholder="Overnight train, Ha Long cruise, Mekong day boat..."
                  value={state.rail_cruise}
                  onChange={(e) => onChange((prev) => ({ ...prev, rail_cruise: e.target.value }))}
                  className={inputClass}
                />
              </label>

              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  Flight / Rail Class
                </span>
                <input
                  type="text"
                  disabled={disabled}
                  placeholder="Economy / Premium Economy / Business / VIP cabin..."
                  value={state.transport_class}
                  onChange={(e) => onChange((prev) => ({ ...prev, transport_class: e.target.value }))}
                  className={inputClass}
                />
              </label>
            </div>
          </div>

          <hr className="border-[var(--color-border)]" />

          {/* 3. Meals & Experiences */}
          <div className="flex flex-col gap-3">
            <h4 className={cn(getTypographyClassName("label"), "text-[var(--color-accent)]")}>
              Meals & Experiences
            </h4>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  Meal Plan
                </span>
                <CustomSelect
                  options={MEAL_PLANS.map((m) => ({ id: m, label: m }))}
                  value={state.meal_plan}
                  onChange={(val) => onChange((prev) => ({ ...prev, meal_plan: val }))}
                  placeholder="Select meal plan"
                />
              </label>

              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  Dining Standard / Level
                </span>
                <input
                  type="text"
                  disabled={disabled}
                  placeholder="Local curated / Fine dining / Michelin / Dietary mix..."
                  value={state.dining_level}
                  onChange={(e) => onChange((prev) => ({ ...prev, dining_level: e.target.value }))}
                  className={inputClass}
                />
              </label>

              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  Experiences Scope in Quote
                </span>
                <CustomSelect
                  options={EXPERIENCES_SCOPES.map((e) => ({ id: e, label: e }))}
                  value={state.experiences_included}
                  onChange={(val) => onChange((prev) => ({ ...prev, experiences_included: val }))}
                  placeholder="Select experiences inclusion"
                />
              </label>

              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  Optional Activities to Price Separately
                </span>
                <input
                  type="text"
                  disabled={disabled}
                  placeholder="e.g. Seaplane tour, private cooking class with MasterChef..."
                  value={state.optional_activities}
                  onChange={(e) => onChange((prev) => ({ ...prev, optional_activities: e.target.value }))}
                  className={inputClass}
                />
              </label>
            </div>
          </div>

          <hr className="border-[var(--color-border)]" />

          {/* 4. Ancillary Services */}
          <div className="flex flex-col gap-3">
            <h4 className={cn(getTypographyClassName("label"), "text-[var(--color-accent)]")}>
              Ancillary & VIP Services
            </h4>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  Visa / Airport Fast-Track
                </span>
                <CustomSelect
                  options={YES_NO_SEPARATE.map((v) => ({ id: v, label: v }))}
                  value={state.visa_fasttrack}
                  onChange={(val) => onChange((prev) => ({ ...prev, visa_fasttrack: val }))}
                  placeholder="Select fast-track need"
                />
              </label>

              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  Airport Meet & Assist
                </span>
                <CustomSelect
                  options={MEET_ASSIST_OPTIONS.map((m) => ({ id: m, label: m }))}
                  value={state.meet_assist}
                  onChange={(val) => onChange((prev) => ({ ...prev, meet_assist: val }))}
                  placeholder="Select meet & assist"
                />
              </label>

              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  Travel Insurance Included?
                </span>
                <CustomSelect
                  options={INSURANCE_OPTIONS.map((i) => ({ id: i, label: i }))}
                  value={state.insurance}
                  onChange={(val) => onChange((prev) => ({ ...prev, insurance: val }))}
                  placeholder="Select insurance option"
                />
              </label>

              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  Other Services to Cost
                </span>
                <input
                  type="text"
                  disabled={disabled}
                  placeholder="SIM cards, porterage, lounge access, photographer, concierge..."
                  value={state.other_services}
                  onChange={(e) => onChange((prev) => ({ ...prev, other_services: e.target.value }))}
                  className={inputClass}
                />
              </label>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
