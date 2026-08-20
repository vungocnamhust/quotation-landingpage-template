"use client";

import { useState, type Dispatch, type ReactNode, type SetStateAction } from "react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import { CheckCircle2, AlertCircle } from "lucide-react";
import FactsNavigator, { type FactSectionStatus } from "./FactsNavigator.tsx";
import type {
  QuotationFacts,
  QuotationOptions,
  ResolvedFacts,
} from "./factsTypes.ts";
import { BrochureAssetsEditor, type MediaWorkspace } from "./MediaSlotRenderer.tsx";
import type { TravelDesignerProfile } from "../../lib/quotationApi.ts";
import type { FactsDeepLink } from "./editableHandoff.ts";
import {
  updateCustomerCounts,
  updateCustomerKidAges,
  updateCustomerName,
  updateTravelStyle,
} from "../../lib/prefillEngine.ts";
import { useFactsFormState } from "./useFactsFormState.ts";
import { FactTripSection } from "./facts-sections/FactTripSection.tsx";
import { FactTravellersSection } from "./facts-sections/FactTravellersSection.tsx";
import { FactProgrammeSection } from "./facts-sections/FactProgrammeSection.tsx";
import { FactServicesSection } from "./facts-sections/FactServicesSection.tsx";
import { FactCommercialSection } from "./facts-sections/FactCommercialSection.tsx";
import { FactSellerSection } from "./facts-sections/FactSellerSection.tsx";

type Props = {
  facts: QuotationFacts;
  options?: QuotationOptions;
  resolvedFacts?: ResolvedFacts;
  readOnly?: boolean;
  allowPresentationEdits?: boolean;
  allowSubmitWhenReadOnly?: boolean;
  sourceNote?: string;
  onChange: Dispatch<SetStateAction<QuotationFacts>>;
  onSubmit?: () => void;
  submitLabel?: string;
  pending?: boolean;
  mediaWorkspace?: MediaWorkspace;
  onDesignerSelected?: (designerProfileId: string) => Promise<void> | void;
  onDayRemoved?: (index: number) => void;
  onHotelRemoved?: (index: number) => void;
  deepLink?: FactsDeepLink;
};

function FactCard({
  id,
  title,
  subtitle,
  status,
  alternateBg = false,
  children,
}: {
  id: string;
  title: string;
  subtitle: string;
  status: FactSectionStatus;
  alternateBg?: boolean;
  children: ReactNode;
}) {
  return (
    <section
      id={`facts-${id}`}
      data-facts-section
      className={cn(
        "rounded-[var(--radius-card)] border border-[var(--color-border-strong)] p-5 shadow-[var(--elevation-card)] sm:p-6 transition-colors",
        alternateBg
          ? "bg-[color-mix(in_srgb,var(--color-surface-muted)_70%,var(--color-surface))]"
          : "bg-[var(--color-surface)]"
      )}
    >
      <header className="mb-5 flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border-strong)] pb-4">
        <div>
          <h2 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
            {title}
          </h2>
          <p className={cn(getTypographyClassName("bodySm"), "mt-1 text-[var(--color-muted)]")}>
            {subtitle}
          </p>
        </div>
        <span
          className={cn(
            getTypographyClassName("caption"),
            "flex items-center gap-1.5 shrink-0",
            status.complete
              ? "text-[var(--color-accent)]"
              : "text-[var(--color-muted)]"
          )}
        >
          {status.complete ? (
            <CheckCircle2 size={14} aria-hidden="true" />
          ) : (
            <AlertCircle size={14} aria-hidden="true" />
          )}
          <span>{status.complete ? "Complete" : "Needs information"}</span>
        </span>
      </header>
      {children}
    </section>
  );
}

export default function FactsForm({
  facts: inputFacts,
  options,
  resolvedFacts,
  readOnly = false,
  allowPresentationEdits = true,
  allowSubmitWhenReadOnly = false,
  sourceNote,
  onChange,
  onSubmit,
  submitLabel = "Confirm facts & prepare content",
  pending = false,
  mediaWorkspace,
  onDesignerSelected,
  onDayRemoved,
  onHotelRemoved,
  deepLink,
}: Props) {
  const [selectedDesigner, setSelectedDesigner] = useState<TravelDesignerProfile | null>(null);

  const {
    facts,
    trip,
    customer,
    services,
    pricing,
    booking,
    presentation,
    activeDay,
    activeHotel,
    toggleDay,
    toggleHotel,
    update,
    patchDay,
    patchHotel,
    addDay,
    removeDay,
    addHotel,
    removeHotel,
    patchTripStartDate,
    syncHotelsFromItinerary,
    addPricingOption,
    patchPricingOption,
    removePricingOption,
    sections,
    status,
  } = useFactsFormState({
    facts: inputFacts,
    onChange,
    deepLink,
    onDayRemoved,
    onHotelRemoved,
  });

  const canSubmit = Boolean(onSubmit && (!readOnly || allowSubmitWhenReadOnly));

  return (
    <div className="grid min-w-0 gap-5 lg:grid-cols-[17rem_minmax(0,1fr)]">
      {/* Sidebar Navigator */}
      <div className="order-1 lg:order-1">
        <FactsNavigator
          sections={sections}
          activeSection={deepLink?.section}
          onSubmit={canSubmit ? onSubmit : undefined}
          submitLabel={submitLabel}
          pending={pending}
        />
      </div>

      {/* Main Content Form Cards */}
      <div className="order-2 flex min-w-0 flex-col gap-5 lg:order-2">
        {sourceNote ? (
          <p
            className={cn(
              getTypographyClassName("caption"),
              "rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3 text-[var(--color-muted)]"
            )}
          >
            {sourceNote}
          </p>
        ) : null}

        {mediaWorkspace ? (
          <section className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] sm:p-6">
            <h2 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
              Brochure assets
            </h2>
            <p className={cn(getTypographyClassName("bodySm"), "mt-1 text-[var(--color-muted)]")}>
              Quote-specific images are canonical Facts.
            </p>
            <div className="mt-4">
              <BrochureAssetsEditor
                workspace={mediaWorkspace}
                readOnly={readOnly}
                context={{
                  travelDesignerId:
                    presentation.travel_designer_id ?? selectedDesigner?.id,
                }}
              />
            </div>
          </section>
        ) : null}

        {/* 1. Trip Section */}
        <FactCard
          id="trip"
          title="Trip"
          subtitle="Essential trip details. AI will write the brochure narrative from these facts."
          status={status("trip")}
          alternateBg={true}
        >
          <FactTripSection
            facts={facts}
            options={options}
            resolvedFacts={resolvedFacts}
            readOnly={readOnly}
            allowPresentationEdits={allowPresentationEdits}
            selectedDesigner={selectedDesigner}
            onDesignerChange={(value, profile) => {
              setSelectedDesigner(profile ?? null);
              if (value && onDesignerSelected) {
                void onDesignerSelected(value);
                return;
              }
              onChange((current) => ({
                ...current,
                presentation_options: {
                  ...current.presentation_options,
                  travel_designer_id: value,
                },
              }));
            }}
            onTripStartDateChange={patchTripStartDate}
            onUpdate={update}
          />
        </FactCard>

        {/* 2. Travellers Section */}
        <FactCard
          id="travellers"
          title="Travellers"
          subtitle="Essential guest details — AI uses these to personalize greeting and story tone."
          status={status("travellers")}
        >
          <FactTravellersSection
            customer={customer}
            readOnly={readOnly}
            onCustomerNameChange={(value) =>
              onChange((current) => updateCustomerName(current, value))
            }
            onCustomerCountsChange={(counts) =>
              onChange((current) => updateCustomerCounts(current, counts))
            }
            onCustomerKidAgesChange={(ages) =>
              onChange((current) => updateCustomerKidAges(current, ages))
            }
            onTravelStyleChange={(style) =>
              onChange((current) => updateTravelStyle(current, style))
            }
            onUpdate={update}
          />
        </FactCard>

        {/* 3. Daily Programme Section */}
        <FactCard
          id="programme"
          title="Daily programme"
          subtitle="Provide day destinations and highlights so AI can generate the daily itinerary story."
          status={status("programme")}
          alternateBg={true}
        >
          <FactProgrammeSection
            trip={trip}
            activeDay={activeDay}
            readOnly={readOnly}
            onToggleDay={toggleDay}
            onPatchDay={patchDay}
            onRemoveDay={removeDay}
            onAddDay={addDay}
            mediaWorkspace={mediaWorkspace}
          />
        </FactCard>

        {/* 4. Hotels & Services Section */}
        <FactCard
          id="services"
          title="Hotels & services"
          subtitle="Accommodations and factual inclusions/exclusions."
          status={status("services")}
        >
          <FactServicesSection
            services={services}
            tripStartDate={trip.start_date}
            tripEndDate={trip.end_date}
            activeHotel={activeHotel}
            readOnly={readOnly}
            onSyncHotelsFromItinerary={syncHotelsFromItinerary}
            onToggleHotel={toggleHotel}
            onPatchHotel={patchHotel}
            onRemoveHotel={removeHotel}
            onAddHotel={addHotel}
            onUpdate={update}
            mediaWorkspace={mediaWorkspace}
          />
        </FactCard>

        {/* 5. Commercial Section */}
        <FactCard
          id="commercial"
          title="Commercial"
          subtitle="Each option carries its own currency, per traveler price, and group total."
          status={status("commercial")}
          alternateBg={true}
        >
          <FactCommercialSection
            pricing={pricing}
            brandId={facts.brand_id}
            market={customer.market}
            adults={customer.adults}
            childrenCount={customer.children}
            lang={facts.lang ?? "en"}
            readOnly={readOnly}
            onAddPricingOption={addPricingOption}
            onPatchPricingOption={patchPricingOption}
            onRemovePricingOption={removePricingOption}
            onUpdate={update}
          />
        </FactCard>

        {/* 6. Booking & Payment Terms Section */}
        <FactCard
          id="seller"
          title="BOOKING & PAYMENT TERMS"
          subtitle="Booking terms, confirmation checklist, and travel designer profile copy."
          status={status("seller")}
        >
          <FactSellerSection
            booking={booking}
            readOnly={readOnly}
            onUpdate={update}
          />
        </FactCard>

        {/* Mobile Submit Button */}
        {canSubmit ? (
          <div className="flex justify-end lg:hidden">
            <button
              type="button"
              onClick={onSubmit}
              disabled={pending}
              className={cn(
                getTypographyClassName("buttonPrimary"),
                "min-h-11 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-6 shadow-md border border-transparent transition-all disabled:opacity-50 cursor-pointer"
              )}
            >
              {pending ? "Saving facts…" : submitLabel}
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
