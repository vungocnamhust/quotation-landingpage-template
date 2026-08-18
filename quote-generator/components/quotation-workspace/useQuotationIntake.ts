"use client";

import { useCallback, useMemo, useState, type Dispatch, type SetStateAction } from "react";
import type { TravelDesignerProfile } from "../../lib/quotationApi";
import { applyRouteDates } from "../../lib/prefillEngine";
import {
  dateForItineraryDay,
  ensureFactsDefaults,
  type QuotationFacts,
  type QuotationOptions,
} from "./factsTypes";

export function daysBetween(
  startDate: string | null,
  endDate: string | null
): number | null {
  if (!startDate || !endDate) return null;
  const start = new Date(`${startDate}T00:00:00.000Z`);
  const end = new Date(`${endDate}T00:00:00.000Z`);
  if (
    Number.isNaN(start.getTime()) ||
    Number.isNaN(end.getTime()) ||
    end < start
  )
    return null;
  return Math.floor((end.getTime() - start.getTime()) / 86_400_000) + 1;
}

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

  const durationDays = daysBetween(trip.start_date, trip.end_date);

  const patchFacts = useCallback(
    (updater: (current: QuotationFacts) => QuotationFacts) =>
      onChange((current) => updater(ensureFactsDefaults(current))),
    [onChange]
  );

  const handleStartDateChange = useCallback(
    (value: string) => {
      const nextStart = value || null;
      const nextLength = daysBetween(nextStart, trip.end_date);
      if (nextLength === null) {
        patchFacts((current) => ({
          ...current,
          trip_facts: {
            ...current.trip_facts,
            start_date: nextStart,
            itinerary: current.trip_facts.itinerary.map((day, idx) => ({
              ...day,
              display_date: dateForItineraryDay(nextStart, day.day_number ?? idx + 1),
            })),
          },
        }));
        return;
      }
      patchFacts((current) => applyRouteDates(current, nextStart, current.trip_facts.end_date, nextLength));
    },
    [patchFacts, trip.end_date]
  );

  const handleEndDateChange = useCallback(
    (value: string) => {
      const nextEnd = value || null;
      const nextLength = daysBetween(trip.start_date, nextEnd);
      if (nextLength === null) {
        patchFacts((current) => ({
          ...current,
          trip_facts: {
            ...current.trip_facts,
            end_date: nextEnd,
          },
        }));
        return;
      }
      patchFacts((current) => applyRouteDates(current, current.trip_facts.start_date, nextEnd, nextLength));
    },
    [patchFacts, trip.start_date]
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
    handleDesignerChange,
  };
}
