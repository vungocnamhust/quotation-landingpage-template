"use client";

import { useCallback, useMemo, useState, type Dispatch, type SetStateAction } from "react";
import type { TravelDesignerProfile } from "../../lib/quotationApi.ts";
import { calculateDuration } from "../../lib/rules/datesRules.ts";
import { tripAdapter } from "../../lib/rules/tripAdapter.ts";
import { tripReconciler } from "../../lib/rules/tripReconciler.ts";
import {
  ensureFactsDefaults,
  type ItineraryDayFact,
  type PricingOptionFact,
  type QuotationFacts,
  type QuotationOptions,
} from "./factsTypes.ts";

import { addDayToRouteTable, removeDayFromRouteTable } from "./useRouteTableSync.ts";
import {
  addPricingOptionInFacts,
  patchPricingOptionWithInference,
  removePricingOptionInFacts,
} from "../../lib/prefillEngine.ts";

export type UseQuotationIntakeOptions = {
  facts: QuotationFacts;
  options: QuotationOptions;
  onChange: Dispatch<SetStateAction<QuotationFacts>>;
};

export function useQuotationIntake({
  facts: inputFacts,
  options,
  onChange,
}: UseQuotationIntakeOptions) {
  const facts = useMemo(() => ensureFactsDefaults(inputFacts), [inputFacts]);
  const trip = facts.trip_facts;
  const customer = facts.customer_facts;
  const pricing = facts.pricing_facts;
  const services = facts.service_facts;

  const [selectedDesigner, setSelectedDesigner] =
    useState<TravelDesignerProfile | null>(null);
  const [pendingRouteReduction, setPendingRouteReduction] = useState<{
    startDate: string | null;
    endDate: string | null;
    length: number;
  } | null>(null);

  const compatibleTemplates = useMemo(
    () =>
      (options.templates ?? []).filter(
        (template) =>
          !facts.brand_id || template.brandIds.includes(facts.brand_id)
      ),
    [facts.brand_id, options.templates]
  );

  const duration = calculateDuration(trip.start_date, trip.end_date);
  const durationDays = duration.durationDays;

  const patchFacts = useCallback(
    (updater: (current: QuotationFacts) => QuotationFacts) =>
      onChange((current) => updater(ensureFactsDefaults(current))),
    [onChange]
  );

  const handleStartDateChange = useCallback(
    (value: string) => {
      patchFacts((current) => {
        const canonical = tripAdapter.fromQuotationFacts(current);
        const reconciled = tripReconciler.setStartDate(canonical, value || null);
        return tripAdapter.syncToQuotationFacts(reconciled, current);
      });
    },
    [patchFacts]
  );

  const handleEndDateChange = useCallback(
    (value: string) => {
      patchFacts((current) => {
        const canonical = tripAdapter.fromQuotationFacts(current);
        const reconciled = tripReconciler.setEndDate(canonical, value || null);
        return tripAdapter.syncToQuotationFacts(reconciled, current);
      });
    },
    [patchFacts]
  );

  const addItineraryDay = useCallback(
    (defaultPayload?: Partial<ItineraryDayFact>) => {
      patchFacts((current) => addDayToRouteTable(current, defaultPayload));
    },
    [patchFacts]
  );

  const removeItineraryDay = useCallback(
    (index: number) => {
      patchFacts((current) => removeDayFromRouteTable(current, index));
    },
    [patchFacts]
  );

  const handleDesignerChange = useCallback(
    (designerId: string | null, profile?: TravelDesignerProfile | null) => {
      setSelectedDesigner(profile ?? null);
      patchFacts((current) => ({
        ...current,
        presentation_options: {
          ...current.presentation_options,
          travel_designer_id: designerId,
        },
      }));
    },
    [patchFacts]
  );

  const handleAddPricingOption = useCallback(
    (defaultLabel?: string) => {
      patchFacts((current) => addPricingOptionInFacts(current, defaultLabel));
    },
    [patchFacts]
  );

  const handleRemovePricingOption = useCallback(
    (index: number) => {
      patchFacts((current) => removePricingOptionInFacts(current, index));
    },
    [patchFacts]
  );

  const handlePatchPricingOption = useCallback(
    (index: number, patch: Partial<PricingOptionFact>) => {
      patchFacts((current) => patchPricingOptionWithInference(current, index, patch));
    },
    [patchFacts]
  );

  return {
    facts,
    trip,
    customer,
    pricing,
    services,
    durationDays,
    compatibleTemplates,
    selectedDesigner,
    pendingRouteReduction,
    setPendingRouteReduction,
    patchFacts,
    handleStartDateChange,
    handleEndDateChange,
    addItineraryDay,
    removeItineraryDay,
    handleDesignerChange,
    handleAddPricingOption,
    handleRemovePricingOption,
    handlePatchPricingOption,
  };
}

