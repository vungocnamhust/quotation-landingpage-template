"use client";

import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";
import { DestinationSelect } from "../../destination/DestinationSelect.tsx";
import { TravelDesignerSelect } from "../../travel-designer/TravelDesignerSelect.tsx";
import { DateInput } from "../../date/index.ts";
import type { TravelDesignerProfile } from "../../../lib/quotationApi.ts";
import type {
  QuotationFacts,
  QuotationOptions,
  ResolvedFacts,
} from "../factsTypes.ts";
import CustomSelect from "../../ui/CustomSelect.tsx";

const lines = (values: string[]) => values.join("\n");
const toLines = (value: string) => value.split("\n");

const inputClass = cn(
  getTypographyClassName("bodyMd"),
  "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] transition-shadow duration-200 focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
);

function Field({
  label,
  value,
  onChange,
  type = "text",
  disabled,
  required,
}: {
  label: string;
  value: string | number | null;
  onChange: (value: string) => void;
  type?: string;
  disabled?: boolean;
  required?: boolean;
}) {
  return (
    <label className="flex flex-col gap-2">
      <span className={cn(getTypographyClassName("label"), "flex justify-between gap-3 text-[var(--color-muted)]")}>
        <span>{label}</span>
        <span className={cn(getTypographyClassName("caption"), required ? "text-[var(--color-accent)]" : "text-[var(--color-muted)]")}>
          {required ? "Required" : "Optional"}
        </span>
      </span>
      <input
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
  facts: QuotationFacts;
  options?: QuotationOptions;
  resolvedFacts?: ResolvedFacts;
  readOnly?: boolean;
  allowPresentationEdits?: boolean;
  templateLocked?: boolean;
  selectedDesigner: TravelDesignerProfile | null;
  onDesignerChange: (designerId: string | null, profile?: TravelDesignerProfile | null) => void;
  onTripStartDateChange: (value: string) => void;
  onTripEndDateChange?: (value: string) => void;
  onUpdate: <K extends keyof QuotationFacts>(key: K, value: QuotationFacts[K]) => void;
};

export function FactTripSection({
  facts,
  options,
  resolvedFacts,
  readOnly = false,
  allowPresentationEdits = true,
  templateLocked = false,
  selectedDesigner,
  onDesignerChange,
  onTripStartDateChange,
  onTripEndDateChange,
  onUpdate,
}: Props) {
  const trip = facts.trip_facts;

  const storedDesigner = facts.presentation_options;
  const designerIdentity = selectedDesigner ?? (storedDesigner?.travel_designer_id ? {
    id: storedDesigner.travel_designer_id,
    name: "",
    email: "",
    phone: "",
    isActive: true,
  } : null);

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {options?.brands ? (
        <label className="flex flex-col gap-2">
          <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
            Brand <span className="text-[var(--color-accent)]">*</span>
          </span>
          <CustomSelect
            options={options.brands}
            value={facts.brand_id}
            disabled={readOnly}
            onChange={(value) => onUpdate("brand_id", value)}
            placeholder="Select brand"
          />
        </label>
      ) : (
        <Field
          label="Brand"
          required
          disabled={readOnly}
          value={facts.brand_id}
          onChange={(value) => onUpdate("brand_id", value || null)}
        />
      )}

      {options?.languages ? (
        <label className="flex flex-col gap-2">
          <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
            Language <span className="text-[var(--color-accent)]">*</span>
          </span>
          <CustomSelect
            options={options.languages}
            value={facts.lang}
            disabled={readOnly}
            onChange={(value) => onUpdate("lang", value as QuotationFacts["lang"])}
            placeholder="Select language"
          />
        </label>
      ) : null}

      {options?.templates ? (
        <label className="flex flex-col gap-2">
          <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
            Template
          </span>
          <CustomSelect
            options={(options.templates ?? []).filter(
              (item) =>
                !facts.brand_id ||
                (item.brandIds ?? []).includes(facts.brand_id)
            )}
            value={facts.presentation_options.template_id}
            disabled={readOnly || templateLocked}
            onChange={(value) =>
              onUpdate("presentation_options", {
                ...facts.presentation_options,
                template_id: value,
              })
            }
            placeholder="Select template"
          />
          {templateLocked ? <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>Template changes are unavailable until the V2 template migration is supported.</span> : null}
        </label>
      ) : null}

      <TravelDesignerSelect
        label="Travel Designer"
        value={facts.presentation_options.travel_designer_id}
        brandId={facts.brand_id}
        disabled={readOnly && !allowPresentationEdits}
        onChange={onDesignerChange}
      />

      {designerIdentity?.name ? (
        <div className="sm:col-span-2 grid gap-3 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3 sm:grid-cols-3">
          <Field label="Designer name" disabled value={designerIdentity.name} onChange={() => undefined} />
          <Field label="Designer email" disabled value={designerIdentity.email} onChange={() => undefined} />
          <Field label="Designer phone" disabled value={designerIdentity.phone} onChange={() => undefined} />
        </div>
      ) : null}

      <p className={cn(getTypographyClassName("bodySm"), "sm:col-span-2 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3 text-[var(--color-muted)]")}>
        Trip title and brochure narrative are created and reviewed in Content Studio after these route facts are saved.
      </p>

      <DateInput
        label="Start date"
        mode="iso"
        disabled={readOnly}
        value={trip.start_date}
        onChange={(val) => onTripStartDateChange(val ?? "")}
      />

      <DateInput
        label="End date"
        mode="iso"
        min={trip.start_date ?? undefined}
        disabled={readOnly}
        value={trip.end_date}
        onChange={(value) => {
          if (onTripEndDateChange) {
            onTripEndDateChange(value ?? "");
          } else {
            onUpdate("trip_facts", { ...trip, end_date: value || null });
          }
        }}
      />

      <div className="sm:col-span-2">
        <DestinationSelect
          mode="multiple"
          label="Destinations"
          disabled={readOnly}
          values={trip.destination_refs ?? []}
          onChange={(refs) => {
            const nextRefs = Array.isArray(refs) ? refs : [];
            onUpdate("trip_facts", {
              ...trip,
              destination_refs: nextRefs,
              destinations: nextRefs.map((ref) => ref.name),
            });
          }}
        />
      </div>

      <div className="sm:col-span-2 grid gap-3 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3 sm:grid-cols-2">
        <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
          Derived route · {resolvedFacts?.routeLabel || "Add itinerary destinations"}
        </p>
        <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
          Derived dates · {resolvedFacts?.travelDatesLabel || "Add start and end dates"}
        </p>
        <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
          Derived duration · {resolvedFacts?.durationDays ?? "—"} days / {resolvedFacts?.durationNights ?? "—"} nights
        </p>
        <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
          Derived party · {resolvedFacts?.partyLabel || "Add traveller counts"}
        </p>
      </div>

      <div className="sm:col-span-2">
        <Area
          label="Special requirements"
          disabled={readOnly}
          value={lines(trip.special_requirements)}
          onChange={(value) =>
            onUpdate("trip_facts", {
              ...trip,
              special_requirements: toLines(value),
            })
          }
          hint="One factual requirement per line."
        />
      </div>

      <p className={cn(getTypographyClassName("bodySm"), "sm:col-span-2 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3 text-[var(--color-muted)]")}>
        Brochure narrative is owned by Content Studio. Save factual route and programme details here, then review copy in Content.
      </p>
    </div>
  );
}
