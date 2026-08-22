"use client";

import { type Dispatch, type ReactNode, type SetStateAction } from "react";
import { Plus, Trash2, Sparkles } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import CustomSelect from "../ui/CustomSelect.tsx";
import { TravelDesignerSelect } from "../travel-designer/TravelDesignerSelect.tsx";
import { DateInput } from "../date/index.ts";
import KidAgesInput from "./KidAgesInput.tsx";
import DayEmbeddedRouteTable from "./DayEmbeddedRouteTable.tsx";
import TriPricingSection from "./TriPricingSection.tsx";
import {
  updateCustomerCounts,
  updateCustomerKidAges,
  updateCustomerName,
} from "../../lib/prefillEngine.ts";
import {
  MAX_COMMERCIAL_OPTIONS,
  type QuotationFacts,
  type QuotationOptions,
} from "./factsTypes.ts";
import { useQuotationIntake } from "./useQuotationIntake.ts";
import { useRouteTableSync } from "./useRouteTableSync.ts";
import { evaluateQuotationDraftReadiness } from "../../lib/rules/validationGates.ts";
import { toastAdapter } from "../../lib/rules/toastAdapter.ts";
import { useToast } from "../staff-workspace/ToastProvider.tsx";

type Props = {
  facts: QuotationFacts;
  options: QuotationOptions;
  pending?: boolean;
  onChange: Dispatch<SetStateAction<QuotationFacts>>;
  onSubmit: (targetStage: "facts" | "design") => void;
};

const inputClass = cn(
  getTypographyClassName("bodyMd"),
  "min-h-11 w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
);

function SectionCard({
  title,
  description,
  action,
  children,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="flex flex-col gap-4 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
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
        {action}
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
  const { toast } = useToast();
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
    handleAddPricingOption,
    handleRemovePricingOption,
    handlePatchPricingOption,
  } = useQuotationIntake({
    facts: inputFacts,
    options,
    onChange,
  });

  const {
    dayWithStays,
    handleRouteTableChange,
    handleUpdateDay,
    handleAddDay,
    handleRemoveDay,
  } = useRouteTableSync(facts, patchFacts);

  const handleFormSubmit = (targetStage: "facts" | "design") => {
    const gateResult = evaluateQuotationDraftReadiness(facts, dayWithStays);
    if (!gateResult.passed) {
      const toastPayload = toastAdapter.fromGateResult(gateResult);
      if (toastPayload) {
        toast(toastPayload.message, toastPayload.type);
      }
      return;
    }
    onSubmit(targetStage);
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        handleFormSubmit("facts");
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

          <label className="flex flex-col gap-1.5">
            <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
              Language
            </span>
            <CustomSelect
              value={facts.lang || "en"}
              placeholder="Select language"
              options={
                options.languages?.length
                  ? options.languages
                  : [
                      { id: "en", label: "English (EN)" },
                      { id: "vi", label: "Tiếng Việt (VI)" },
                      { id: "ar", label: "العربية (AR)" },
                    ]
              }
              onChange={(lang) =>
                patchFacts((current) => ({
                  ...current,
                  lang: (lang || "en") as QuotationFacts["lang"],
                }))
              }
            />
          </label>

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
              patchFacts((current) => updateCustomerKidAges(current, kidAges))
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
          <DateInput
            label="Start Date"
            required
            mode="iso"
            value={trip.start_date ?? ""}
            onChange={(val) => handleStartDateChange(val ?? "")}
          />

          <DateInput
            label="End Date"
            required
            mode="iso"
            min={trip.start_date ?? undefined}
            value={trip.end_date ?? ""}
            onChange={(val) => handleEndDateChange(val ?? "")}
          />

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
          onUpdateDay={handleUpdateDay}
          onAddDay={handleAddDay}
          onRemoveDay={handleRemoveDay}
        />
      </SectionCard>

      {/* 4. Commercial Pricing Options Card */}
      <SectionCard
        title="4. Commercial Pricing Options"
        description="Optionally configure up to 3 pricing tiers or packages (e.g. Standard, Premium, Deluxe)."
        action={
          <button
            type="button"
            disabled={pricing.options.length >= MAX_COMMERCIAL_OPTIONS}
            onClick={() => handleAddPricingOption()}
            className={cn(
              getTypographyClassName("buttonSecondary"),
              "flex items-center gap-1.5 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-[var(--color-on-surface)] transition-all hover:border-[var(--color-accent)] hover:text-[var(--color-accent)] disabled:cursor-not-allowed disabled:opacity-40 cursor-pointer"
            )}
          >
            <Plus size={14} aria-hidden="true" />
            <span>Add Option ({pricing.options.length}/{MAX_COMMERCIAL_OPTIONS})</span>
          </button>
        }
      >
        <div className="flex flex-col gap-4">
          {pricing.options.map((opt, index) => (
            <div
              key={opt.id || `pricing-opt-${index}`}
              className="flex flex-col gap-3 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-xs"
            >
              <div className="flex items-center justify-between gap-3 border-b border-[var(--color-border)] pb-2.5">
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      getTypographyClassName("caption"),
                      "rounded-full px-2.5 py-0.5 border",
                      index === 0
                        ? "bg-[var(--color-accent-wash)] text-[var(--color-accent)] border-[var(--color-accent)]"
                        : "bg-[var(--color-surface-muted)] text-[var(--color-muted)] border-[var(--color-border)]"
                    )}
                  >
                    {index === 0 ? "Tier 1 (Primary)" : `Tier ${index + 1}`}
                  </span>
                  <span className={cn(getTypographyClassName("label"), "text-[var(--color-on-surface)]")}>
                    {opt.label || `Option ${index + 1}`}
                  </span>
                </div>

                {pricing.options.length > 1 ? (
                  <button
                    type="button"
                    onClick={() => handleRemovePricingOption(index)}
                    title="Remove this pricing tier"
                    aria-label={`Remove option ${opt.label || index + 1}`}
                    className="flex h-7 w-7 items-center justify-center rounded-[var(--radius-button)] text-[var(--color-muted)] transition-colors hover:bg-rose-50 hover:text-rose-600 cursor-pointer"
                  >
                    <Trash2 size={15} aria-hidden="true" />
                  </button>
                ) : null}
              </div>

              <TriPricingSection
                label={opt.label}
                currency={opt.currency || "USD"}
                perAdultMinor={opt.per_adult_amount_minor ?? opt.per_traveler_amount_minor}
                perChildMinor={opt.per_child_amount_minor ?? null}
                groupTotalMinor={opt.group_total_amount_minor}
                adults={customer.adults ?? 2}
                childrenCount={customer.children ?? 0}
                onChange={(patch) =>
                  handlePatchPricingOption(index, {
                    label: patch.label,
                    currency: patch.currency,
                    per_adult_amount_minor: patch.perAdultMinor,
                    per_child_amount_minor: patch.perChildMinor,
                    per_traveler_amount_minor: patch.perAdultMinor,
                    group_total_amount_minor: patch.groupTotalMinor,
                  })
                }
              />
            </div>
          ))}
        </div>
      </SectionCard>

      {/* Submit Button Bar with Dual Actions */}
      <div className="flex flex-wrap items-center justify-end gap-3 pt-2">
        <button
          type="button"
          disabled={pending}
          onClick={() => handleFormSubmit("facts")}
          className={cn(
            getTypographyClassName("buttonSecondary"),
            "min-h-12 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-6 text-[var(--color-on-surface)] hover:bg-[var(--color-surface-muted)] shadow-xs transition-all disabled:opacity-50 cursor-pointer"
          )}
        >
          {pending ? "Creating Quotation…" : "Tạo Báo Giá & Kiểm Tra Facts"}
        </button>

        <button
          type="button"
          disabled={pending}
          onClick={() => handleFormSubmit("design")}
          className={cn(
            getTypographyClassName("buttonPrimary"),
            "flex items-center gap-2 min-h-12 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-7 shadow-md border border-transparent transition-all disabled:opacity-50 cursor-pointer"
          )}
        >
          <Sparkles size={16} aria-hidden="true" />
          <span>{pending ? "Creating Quotation…" : "Tạo Báo Giá & Mở Trực Tiếp Canvas Thiết Kế"}</span>
        </button>
      </div>
    </form>
  );
}
