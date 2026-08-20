"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";
import type {
  FactSectionId,
  FactSectionStatus,
} from "./FactsNavigator.tsx";
import type {
  HotelFact,
  ItineraryDayFact,
  QuotationFacts,
  PricingOptionFact,
} from "./factsTypes.ts";
import {
  ensureFactsDefaults,
} from "./factsTypes.ts";
import type { FactsDeepLink } from "./editableHandoff.ts";
import {
  addHotelToFacts,
  patchHotelInFacts,
  patchItineraryDayInFacts,
  patchPricingOptionWithInference,
  removeHotelFromFacts,
  syncHotelsFromItineraryOvernights,
} from "../../lib/prefillEngine.ts";
import { pricingAdapter } from "../../lib/rules/pricingAdapter.ts";
import { pricingReconciler } from "../../lib/rules/pricingReconciler.ts";
import { staysAdapter } from "../../lib/rules/staysAdapter.ts";
import { staysReconciler } from "../../lib/rules/staysReconciler.ts";
import { tripAdapter } from "../../lib/rules/tripAdapter.ts";
import { tripReconciler } from "../../lib/rules/tripReconciler.ts";

export const newHotelFact = (): HotelFact => ({
  accommodation_id: null,
  destination: null,
  destination_ref: null,
  name: null,
  room_type: null,
  check_in: null,
  check_out: null,
  intro: null,
  phone: null,
  display_city: null,
  display_date: null,
  hotel_asset: null,
  room_asset: null,
});

export type UseFactsFormStateOptions = {
  facts: QuotationFacts;
  onChange: Dispatch<SetStateAction<QuotationFacts>>;
  deepLink?: FactsDeepLink;
  onDayRemoved?: (index: number) => void;
  onHotelRemoved?: (index: number) => void;
};

export function useFactsFormState({
  facts: inputFacts,
  onChange,
  deepLink,
  onDayRemoved,
  onHotelRemoved,
}: UseFactsFormStateOptions) {
  const facts: QuotationFacts = useMemo(() => {
    const safe = ensureFactsDefaults(inputFacts);
    const canonical = staysAdapter.fromQuotationFacts(safe);
    const hydratedItinerary = staysReconciler.syncItineraryFromStays(
      canonical.itinerary,
      safe.service_facts.hotels,
      safe.trip_facts.start_date
    );
    return staysAdapter.syncToQuotationFacts(
      { ...canonical, itinerary: hydratedItinerary },
      safe
    );
  }, [inputFacts]);

  const trip = facts.trip_facts;
  const customer = facts.customer_facts;
  const services = facts.service_facts;
  const pricing = facts.pricing_facts;
  const booking = facts.booking_facts;
  const presentation = facts.presentation_options;

  const [activeDay, setActiveDay] = useState<number | null>(
    trip.itinerary.length ? 0 : null
  );
  const [activeHotel, setActiveHotel] = useState<number | null>(
    services.hotels.length ? 0 : null
  );

  const focusTarget = useRef<{
    kind: "day" | "hotel" | "pricingOption" | "bookingTerm";
    index: number;
  } | null>(null);

  const update = useCallback(
    <K extends keyof QuotationFacts>(key: K, value: QuotationFacts[K]) =>
      onChange((current) => ({ ...ensureFactsDefaults(current), [key]: value })),
    [onChange]
  );

  const patchDay = useCallback(
    (index: number, patch: Partial<ItineraryDayFact>) =>
      onChange((current) => patchItineraryDayInFacts(current, index, patch)),
    [onChange]
  );

  const patchHotel = useCallback(
    (index: number, patch: Partial<HotelFact>) =>
      onChange((current) => patchHotelInFacts(current, index, patch)),
    [onChange]
  );

  const toggleDay = useCallback(
    (index: number) =>
      setActiveDay((current) => (current === index ? null : index)),
    []
  );

  const toggleHotel = useCallback(
    (index: number) =>
      setActiveHotel((current) => (current === index ? null : index)),
    []
  );

  const removeDay = useCallback(
    (index: number) => {
      onChange((current) => {
        const canonical = tripAdapter.fromQuotationFacts(current);
        const reconciled = tripReconciler.removeDay(canonical, index);
        const updatedFacts = tripAdapter.syncToQuotationFacts(reconciled, current);
        return syncHotelsFromItineraryOvernights(updatedFacts);
      });
      setActiveDay(null);
      onDayRemoved?.(index);
    },
    [onChange, onDayRemoved]
  );

  const removeHotel = useCallback(
    (index: number) => {
      onChange((current) => removeHotelFromFacts(current, index));
      setActiveHotel(null);
      onHotelRemoved?.(index);
    },
    [onChange, onHotelRemoved]
  );

  const addDay = useCallback(() => {
    const index = trip.itinerary.length;
    onChange((current) => {
      const canonical = tripAdapter.fromQuotationFacts(current);
      const reconciled = tripReconciler.addDay(canonical);
      const updatedFacts = tripAdapter.syncToQuotationFacts(reconciled, current);
      return syncHotelsFromItineraryOvernights(updatedFacts);
    });
    setActiveDay(index);
    focusTarget.current = { kind: "day", index };
  }, [onChange, trip.itinerary.length]);

  const patchTripStartDate = useCallback(
    (value: string) => {
      onChange((current) => {
        const canonicalTrip = tripAdapter.fromQuotationFacts(current);
        const reconciledTrip = tripReconciler.setStartDate(canonicalTrip, value || null);
        const updatedFacts = tripAdapter.syncToQuotationFacts(reconciledTrip, current);
        const canonicalStays = staysAdapter.fromQuotationFacts(updatedFacts);
        const shiftedStays = staysReconciler.shiftStayDates(
          canonicalStays.stays,
          value || null,
          canonicalStays.itinerary
        );
        return staysAdapter.syncToQuotationFacts(
          { ...canonicalStays, stays: shiftedStays },
          updatedFacts
        );
      });
    },
    [onChange]
  );

  const patchTripEndDate = useCallback(
    (value: string) => {
      onChange((current) => {
        const canonicalTrip = tripAdapter.fromQuotationFacts(current);
        const reconciledTrip = tripReconciler.setEndDate(canonicalTrip, value || null);
        const updatedFacts = tripAdapter.syncToQuotationFacts(reconciledTrip, current);
        const canonicalStays = staysAdapter.fromQuotationFacts(updatedFacts);
        const reconciledStays = staysReconciler.reconcileStaysFromItinerary(
          canonicalStays.itinerary,
          canonicalStays.startDate,
          current.service_facts.hotels
        );
        return staysAdapter.syncToQuotationFacts(
          { ...canonicalStays, stays: reconciledStays },
          updatedFacts
        );
      });
    },
    [onChange]
  );

  const syncHotelsFromItinerary = useCallback(() => {
    onChange((current) => syncHotelsFromItineraryOvernights(current));
  }, [onChange]);

  const addPricingOption = useCallback(() => {
    onChange((current) => {
      const canonical = pricingAdapter.fromQuotationFacts(current);
      const updated = pricingReconciler.addOption(canonical);
      return pricingAdapter.syncToQuotationFacts(updated, current);
    });
  }, [onChange]);

  const patchPricingOption = useCallback(
    (index: number, patch: Partial<PricingOptionFact>) => {
      onChange((current) => patchPricingOptionWithInference(current, index, patch));
    },
    [onChange]
  );

  const removePricingOption = useCallback(
    (index: number) => {
      onChange((current) => {
        const canonical = pricingAdapter.fromQuotationFacts(current);
        const updated = pricingReconciler.removeOption(canonical, index);
        return pricingAdapter.syncToQuotationFacts(updated, current);
      });
    },
    [onChange]
  );

  const addHotel = useCallback(() => {
    const index = services.hotels.length;
    onChange((current) => addHotelToFacts(current));
    setActiveHotel(index);
    focusTarget.current = { kind: "hotel", index };
  }, [onChange, services.hotels.length]);

  // Handle programmatic focus after adding items
  useEffect(() => {
    const target = focusTarget.current;
    if (!target) return;
    document
      .getElementById(
        target.kind === "day"
          ? `day-${target.index}-number`
          : target.kind === "hotel"
          ? `hotel-${target.index}-name`
          : target.kind === "pricingOption"
          ? `pricing-${target.index}-label`
          : `booking-term-${target.index}-label`
      )
      ?.focus();
    focusTarget.current = null;
  }, [facts]);

  // Deep Link scrolling & accordion auto-expansion
  const deepLinkKey = deepLink
    ? `${deepLink.section}:${deepLink.focus?.kind ?? "section"}:${
        deepLink.focus?.index ?? ""
      }`
    : "";

  useEffect(() => {
    if (!deepLink) return;
    document
      .getElementById(`facts-${deepLink.section}`)
      ?.scrollIntoView({ behavior: "auto", block: "start" });

    const focus = deepLink.focus;
    if (!focus) return;
    if (!["day", "hotel", "pricingOption", "bookingTerm"].includes(focus.kind))
      return;

    const controlId =
      focus.kind === "day"
        ? `day-${focus.index}-number`
        : focus.kind === "hotel"
        ? `hotel-${focus.index}-name`
        : focus.kind === "pricingOption"
        ? `pricing-${focus.index}-label`
        : `booking-term-${focus.index}-label`;

    let focusFrame: number | undefined;
    const frame = requestAnimationFrame(() => {
      if (focus.kind === "day" && focus.index < trip.itinerary.length)
        setActiveDay(focus.index);
      if (focus.kind === "hotel" && focus.index < services.hotels.length)
        setActiveHotel(focus.index);
      focusFrame = requestAnimationFrame(() =>
        document.getElementById(controlId)?.focus()
      );
    });

    return () => {
      cancelAnimationFrame(frame);
      if (focusFrame !== undefined) cancelAnimationFrame(focusFrame);
    };
  }, [deepLinkKey, deepLink, services.hotels.length, trip.itinerary.length]);

  // Section completion calculations for FactsNavigator
  const sections = useMemo<FactSectionStatus[]>(
    () => [
      {
        id: "trip",
        label: "Trip",
        detail:
          trip.destinations.length || trip.itinerary.length
            ? "Route ready"
            : "Route needed",
        complete: Boolean(trip.destinations.length || trip.itinerary.length),
      },
      {
        id: "travellers",
        label: "Travellers",
        detail: customer.customer_name
          ? "Guest details added"
          : "Guest details needed",
        complete: Boolean(customer.customer_name),
      },
      {
        id: "programme",
        label: "Programme",
        detail: `${
          trip.itinerary.filter(
            (day) => day.destination && (day.summary || day.highlights.length)
          ).length
        }/${trip.itinerary.length} days ready`,
        complete:
          trip.itinerary.length > 0 &&
          trip.itinerary.every(
            (day) => day.destination && (day.summary || day.highlights.length)
          ),
      },
      {
        id: "services",
        label: "Services",
        detail: services.hotels.length
          ? `${services.hotels.length} hotels added`
          : "Optional",
        complete: services.hotels.length > 0 || services.inclusions.length > 0,
      },
      {
        id: "commercial",
        label: "Commercial",
        detail: pricing.options.length
          ? `${pricing.options.length} option${
              pricing.options.length === 1 ? "" : "s"
            } added`
          : "Optional",
        complete: pricing.options.length > 0,
      },
      {
        id: "seller",
        label: "Booking & payment terms",
        detail:
          presentation.travel_designer_id || booking.description
            ? "Contact details added"
            : "Optional",
        complete: Boolean(
          presentation.travel_designer_id || booking.description
        ),
      },
    ],
    [
      booking.description,
      customer.customer_name,
      presentation.travel_designer_id,
      pricing.options.length,
      services.hotels.length,
      services.inclusions.length,
      trip,
    ]
  );

  const status = useCallback(
    (id: FactSectionId) => sections.find((item) => item.id === id)!,
    [sections]
  );

  return {
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
    patchTripEndDate,
    syncHotelsFromItinerary,
    addPricingOption,
    patchPricingOption,
    removePricingOption,
    sections,
    status,
  };
}
