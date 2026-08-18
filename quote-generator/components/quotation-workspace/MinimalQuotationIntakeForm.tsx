"use client";

import { type Dispatch, type ReactNode, type SetStateAction } from "react";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";
import CustomSelect from "../ui/CustomSelect";
import { TravelDesignerSelect } from "../travel-designer/TravelDesignerSelect";
import KidAgesInput from "./KidAgesInput";
import DayEmbeddedRouteTable from "./DayEmbeddedRouteTable";
import TriPricingSection from "./TriPricingSection";
import { updateCustomerCounts, updateCustomerName } from "../../lib/prefillEngine";
import {
  type QuotationFacts,
  type QuotationOptions,
} from "./factsTypes";
import { useQuotationIntake } from "./useQuotationIntake";
import { useRouteTableSync } from "./useRouteTableSync";

type Props = {
  facts: QuotationFacts;
  options: QuotationOptions;
  pending?: boolean;
  onChange: Dispatch<SetStateAction<QuotationFacts>>;
  onSubmit: () => void;
};

const inputClass = cn(
  getTypographyClassName("bodyMd"),
  "min-h-11 w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
);

function SectionCard({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <section className="flex flex-col gap-4 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] sm:p-6">
      <div>
        <h2 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
          {title}
        </h2>
        {description ? (
          <p className={cn(getTypographyClassName("caption"), "mt-1 text-[var(--color-muted)]")}>
            {description}
          </p>
        ) : null}
      </div>
      {children}
    </section>
  );
}

export default function MinimalQuotationIntakeForm({
  facts: inputFacts,
  options,
  pending = false,
  onChange,
  onSubmit,
}: Props) {
  const {
    facts,
    trip,
    customer,
    pricing,
    durationDays,
    compatibleTemplates,
    patchFacts,
    handleStartDateChange,
    handleEndDateChange,
    handleDesignerChange,
  } = useQuotationIntake({
    facts: inputFacts,
    options,
    onChange,
  });

  const { dayWithStays, handleRouteTableChange } = useRouteTableSync(facts, patchFacts);

  const pricingOption = pricing.options[0] || {
    id: "opt-standard",
    label: "Standard Luxury Option",
    currency: "USD",
    per_traveler_amount_minor: 350000,
    group_total_amount_minor: 700000,
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
      className="mx-auto flex w-full max-w-4xl flex-col gap-6"
    >
      {/* 1. Identity & Lead Card */}
      <SectionCard
        title="1. Brand & Designer Assignment"
        description="Choose the brand profile and travel designer ownership."
      >
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {options.brands?.length ? (
            <label className="flex flex-col gap-1.5">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Brand
              </span>
              <CustomSelect
                value={facts.brand_id}
                placeholder="Select brand"
                options={options.brands}
                onChange={(brandId) =>
                  patchFacts((current) => ({
                    ...current,
                    brand_id: brandId,
                    presentation_options: {
                      ...current.presentation_options,
                      template_id:
                        options.templates.find((t) => t.brandIds.includes(brandId))?.id ??
                        current.presentation_options.template_id,
                    },
                  }))
                }
              />
            </label>
          ) : null}

          {options.languages?.length ? (
            <label className="flex flex-col gap-1.5">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Language
              </span>
              <CustomSelect
                value={facts.lang}
                placeholder="Select language"
                options={options.languages}
                onChange={(lang) =>
                  patchFacts((current) => ({
                    ...current,
                    lang: lang as QuotationFacts["lang"],
                  }))
                }
              />
            </label>
          ) : null}

          {compatibleTemplates.length ? (
            <label className="flex flex-col gap-1.5">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Template
              </span>
              <CustomSelect
                value={facts.presentation_options.template_id}
                placeholder="Select template"
                options={compatibleTemplates}
                onChange={(templateId) =>
                  patchFacts((current) => ({
                    ...current,
                    presentation_options: {
                      ...current.presentation_options,
                      template_id: templateId,
                    },
                  }))
                }
              />
            </label>
          ) : null}

          <div className="sm:col-span-2 lg:col-span-3">
            <TravelDesignerSelect
              label="Travel Designer Ownership"
              value={facts.presentation_options.travel_designer_id}
              brandId={facts.brand_id}
              onChange={handleDesignerChange}
            />
          </div>
        </div>
      </SectionCard>

      {/* 2. Client & Party Card */}
      <SectionCard
        title="2. Client & Party Composition"
        description="Guest identity, traveller counts, and children ages."
      >
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <label className="flex flex-col gap-1.5 sm:col-span-2 lg:col-span-3">
            <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
              Client / Family Name *
            </span>
            <input
              required
              className={inputClass}
              placeholder="e.g. Mr. Alexander Vance & Family"
              value={customer.customer_name ?? ""}
              onChange={(e) =>
                patchFacts((current) => updateCustomerName(current, e.target.value))
              }
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
              Adults *
            </span>
            <input
              type="number"
              min={1}
              required
              className={inputClass}
              value={customer.adults ?? 2}
              onChange={(e) =>
                patchFacts((current) =>
                  updateCustomerCounts(current, {
                    adults: Math.max(1, parseInt(e.target.value, 10) || 1),
                  })
                )
              }
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
              Children (ages 2–11)
            </span>
            <input
              type="number"
              min={0}
              className={inputClass}
              value={customer.children ?? 0}
              onChange={(e) =>
                patchFacts((current) =>
                  updateCustomerCounts(current, {
                    children: Math.max(0, parseInt(e.target.value, 10) || 0),
                  })
                )
              }
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
              Nationality / Market
            </span>
            <input
              className={inputClass}
              placeholder="e.g. US, UK, Australia"
              value={customer.market ?? customer.nationality ?? ""}
              onChange={(e) =>
                patchFacts((current) => ({
                  ...current,
                  customer_facts: {
                    ...current.customer_facts,
                    market: e.target.value || null,
                    nationality: e.target.value || null,
                  },
                }))
              }
            />
          </label>
        </div>

        {customer.children && customer.children > 0 ? (
          <KidAgesInput
            childrenCount={customer.children}
            kidAges={customer.kid_ages ?? []}
            onChange={(kidAges) =>
              patchFacts((current) => ({
                ...current,
                customer_facts: {
                  ...current.customer_facts,
                  kid_ages: kidAges,
                },
              }))
            }
          />
        ) : null}
      </SectionCard>

      {/* 3. Dates & Embedded Day Table Card */}
      <SectionCard
        title="3. Travel Dates & Daily Stays Blueprint"
        description="Pick dates, then map out destinations and accommodations day by day."
      >
        <div className="grid gap-4 sm:grid-cols-3 border-b border-[var(--color-border)] pb-4">
          <label className="flex flex-col gap-1.5">
            <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
              Start Date *
            </span>
            <input
              type="date"
              required
              className={inputClass}
              value={trip.start_date ?? ""}
              onChange={(e) => handleStartDateChange(e.target.value)}
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
              End Date *
            </span>
            <input
              type="date"
              required
              className={inputClass}
              value={trip.end_date ?? ""}
              onChange={(e) => handleEndDateChange(e.target.value)}
            />
          </label>

          <div className="flex flex-col gap-1.5">
            <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
              Duration
            </span>
            <div className={cn(inputClass, "flex items-center bg-[var(--color-surface-muted)]")}>
              {durationDays === null
                ? "Select dates above"
                : `${durationDays} Days / ${Math.max(0, durationDays - 1)} Nights`}
            </div>
          </div>
        </div>

        <DayEmbeddedRouteTable
          itinerary={dayWithStays}
          startDate={trip.start_date}
          onChange={handleRouteTableChange}
        />
      </SectionCard>

      {/* 4. Commercial Pricing Tier Card */}
      <SectionCard
        title="4. Commercial Pricing Structure"
        description="Optionally configure pricing tiers or per-person amounts."
      >
        <TriPricingSection
          label={pricingOption.label}
          currency={pricingOption.currency || "USD"}
          perAdultMinor={pricingOption.per_adult_amount_minor ?? pricingOption.per_traveler_amount_minor}
          perChildMinor={pricingOption.per_child_amount_minor ?? null}
          groupTotalMinor={pricingOption.group_total_amount_minor}
          adults={customer.adults ?? 2}
          childrenCount={customer.children ?? 0}
          onChange={(patch) =>
            patchFacts((current) => {
              const currentOpt = current.pricing_facts.options[0] || pricingOption;
              return {
                ...current,
                pricing_facts: {
                  ...current.pricing_facts,
                  options: [
                    {
                      ...currentOpt,
                      label: patch.label ?? currentOpt.label,
                      currency: patch.currency ?? currentOpt.currency,
                      per_traveler_amount_minor: patch.perAdultMinor ?? currentOpt.per_traveler_amount_minor,
                      per_adult_amount_minor: patch.perAdultMinor ?? currentOpt.per_adult_amount_minor,
                      per_child_amount_minor: patch.perChildMinor ?? currentOpt.per_child_amount_minor,
                      group_total_amount_minor: patch.groupTotalMinor ?? currentOpt.group_total_amount_minor,
                    },
                  ],
                },
              };
            })
          }
        />
      </SectionCard>

      {/* Submit Button Bar */}
      <div className="flex justify-end gap-3 pt-2">
        <button
          type="submit"
          disabled={pending}
          className={cn(
            getTypographyClassName("buttonPrimary"),
            "min-h-12 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-8 shadow-md border border-transparent transition-all disabled:opacity-50 cursor-pointer"
          )}
        >
          {pending ? "Creating Quotation…" : "Create Quotation & Proceed"}
        </button>
      </div>
    </form>
  );
}
