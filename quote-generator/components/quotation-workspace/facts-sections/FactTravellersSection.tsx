"use client";

import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";
import { TravelStyleSelect } from "../../travel-style/TravelStyleSelect.tsx";
import KidAgesInput from "../KidAgesInput.tsx";
import type { CustomerFact, QuotationFacts } from "../factsTypes.ts";

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

type Props = {
  customer: CustomerFact;
  readOnly?: boolean;
  onCustomerNameChange: (value: string) => void;
  onCustomerCountsChange: (counts: { adults?: number | null; children?: number | null }) => void;
  onCustomerKidAgesChange?: (ages: number[]) => void;
  onTravelStyleChange?: (style: string | null) => void;
  onUpdate: <K extends keyof QuotationFacts>(key: K, value: QuotationFacts[K]) => void;
};

export function FactTravellersSection({
  customer,
  readOnly = false,
  onCustomerNameChange,
  onCustomerCountsChange,
  onCustomerKidAgesChange,
  onTravelStyleChange,
  onUpdate,
}: Props) {
  const handleKidAgesChange = (ages: number[]) => {
    if (onCustomerKidAgesChange) {
      onCustomerKidAgesChange(ages);
    } else {
      onUpdate("customer_facts", {
        ...customer,
        kid_ages: ages,
      });
    }
  };

  const handleTravelStyleChange = (style: string | null) => {
    if (onTravelStyleChange) {
      onTravelStyleChange(style);
    } else {
      onUpdate("customer_facts", {
        ...customer,
        guest_profile: style || null,
        travel_style: style || null,
      });
    }
  };

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <Field
        label="Customer name"
        disabled={readOnly}
        value={customer.customer_name}
        onChange={onCustomerNameChange}
      />
      <Field
        label="Adults"
        type="number"
        disabled={readOnly}
        value={customer.adults}
        onChange={(value) =>
          onCustomerCountsChange({ adults: value ? Number(value) : null })
        }
      />
      <Field
        label="Children"
        type="number"
        disabled={readOnly}
        value={customer.children}
        onChange={(value) =>
          onCustomerCountsChange({ children: value ? Number(value) : null })
        }
      />
      <Field
        label="Nationality"
        disabled={readOnly}
        value={customer.nationality}
        onChange={(value) =>
          onUpdate("customer_facts", {
            ...customer,
            nationality: value || null,
          })
        }
      />

      {/* Dynamic Kid Ages Grid */}
      {customer.children && customer.children > 0 ? (
        <div className="sm:col-span-2">
          <KidAgesInput
            childrenCount={customer.children}
            kidAges={customer.kid_ages ?? []}
            disabled={readOnly}
            onChange={handleKidAgesChange}
          />
        </div>
      ) : null}

      <div className="sm:col-span-2">
        <TravelStyleSelect
          label="Travel Style & Guest Preferences"
          disabled={readOnly}
          value={customer.travel_style ?? customer.guest_profile}
          onChange={handleTravelStyleChange}
        />
      </div>
      <Field
        label="Market"
        disabled={readOnly}
        value={customer.market}
        onChange={(value) =>
          onUpdate("customer_facts", { ...customer, market: value || null })
        }
      />
    </div>
  );
}
