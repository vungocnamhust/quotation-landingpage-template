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
} from "./FactsNavigator";
import type {
  HotelFact,
  ItineraryDayFact,
  QuotationFacts,
  PricingOptionFact,
} from "./factsTypes";
import {
  createPricingOption,
  dateForItineraryDay,
  ensureFactsDefaults,
  MAX_COMMERCIAL_OPTIONS,
  routeDestinationRefsFromItinerary,
} from "./factsTypes";
import type { FactsDeepLink } from "./editableHandoff";
import {
  createItineraryDayWithDefaults,
  syncHotelsFromItineraryOvernights,
} from "../../lib/prefillEngine";
import {
  consolidateStaysFromDayItems,
  hydrateDayAccommodationsFromHotels,
} from "../../lib/rules/staysRules";

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
  const facts = useMemo(() => {
    const safe = ensureFactsDefaults(inputFacts);
    const hydratedItinerary = hydrateDayAccommodationsFromHotels(
      safe.trip_facts.itinerary,
      safe.service_facts.hotels,
      safe.trip_facts.start_date
    );
    return {
      ...safe,
      trip_facts: {
        ...safe.trip_facts,
        itinerary: hydratedItinerary,
      },
    };
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
      onChange((current) => {
        const safe = ensureFactsDefaults(current);
        const itinerary = safe.trip_facts.itinerary.map((item, itemIndex) =>
          itemIndex === index ? { ...item, ...patch } : item
        );
        const destination_refs = routeDestinationRefsFromItinerary(itinerary);

        let hotels = safe.service_facts.hotels;
        if (
          patch.accommodation_id !== undefined ||
          patch.accommodation_name !== undefined ||
          patch.room_type !== undefined
        ) {
          const consolidated = consolidateStaysFromDayItems(
            itinerary,
            safe.trip_facts.start_date
          );
          if (consolidated.length > 0) {
            hotels = consolidated;
          }
        }

        return {
          ...safe,
          trip_facts: {
            ...safe.trip_facts,
            itinerary,
            destination_refs,
            destinations: destination_refs.map((ref) => ref.name),
          },
          service_facts: {
            ...safe.service_facts,
            hotels,
          },
        };
      }),
    [onChange]
  );

  const patchHotel = useCallback(
    (index: number, patch: Partial<HotelFact>) =>
      onChange((current) => {
        const safe = ensureFactsDefaults(current);
        const hotels = safe.service_facts.hotels.map((item, itemIndex) =>
          itemIndex === index ? { ...item, ...patch } : item
        );
        const itinerary = hydrateDayAccommodationsFromHotels(
          safe.trip_facts.itinerary,
          hotels,
          safe.trip_facts.start_date
        );
        return {
          ...safe,
          trip_facts: {
            ...safe.trip_facts,
            itinerary,
          },
          service_facts: {
            ...safe.service_facts,
            hotels,
          },
        };
      }),
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
        const safe = ensureFactsDefaults(current);
        return {
          ...safe,
          trip_facts: {
            ...safe.trip_facts,
            itinerary: safe.trip_facts.itinerary.filter(
              (_, itemIndex) => itemIndex !== index
            ),
          },
        };
      });
      setActiveDay(null);
      onDayRemoved?.(index);
    },
    [onChange, onDayRemoved]
  );

  const removeHotel = useCallback(
    (index: number) => {
      onChange((current) => {
        const safe = ensureFactsDefaults(current);
        return {
          ...safe,
          service_facts: {
            ...safe.service_facts,
            hotels: safe.service_facts.hotels.filter(
              (_, itemIndex) => itemIndex !== index
            ),
          },
        };
      });
      setActiveHotel(null);
      onHotelRemoved?.(index);
    },
    [onChange, onHotelRemoved]
  );

  const addDay = useCallback(() => {
    const index = trip.itinerary.length;
    onChange((current) => {
      const safe = ensureFactsDefaults(current);
      return {
        ...safe,
        trip_facts: {
          ...safe.trip_facts,
          itinerary: [
            ...safe.trip_facts.itinerary,
            createItineraryDayWithDefaults({
              index,
              startDate: safe.trip_facts.start_date,
              lang: safe.lang,
            }),
          ],
        },
      };
    });
    setActiveDay(index);
    focusTarget.current = { kind: "day", index };
  }, [onChange, trip.itinerary.length]);

  const patchTripStartDate = useCallback(
    (value: string) => {
      onChange((current) => {
        const safe = ensureFactsDefaults(current);
        const startDate = value || null;
        return {
          ...safe,
          trip_facts: {
            ...safe.trip_facts,
            start_date: startDate,
            itinerary: safe.trip_facts.itinerary.map((day, index) => ({
              ...day,
              display_date: dateForItineraryDay(
                startDate,
                day.day_number ?? index + 1
              ),
            })),
          },
        };
      });
    },
    [onChange]
  );

  const syncHotelsFromItinerary = useCallback(() => {
    onChange((current) => syncHotelsFromItineraryOvernights(current));
  }, [onChange]);

  const addPricingOption = useCallback(() => {
    onChange((current) => {
      const safe = ensureFactsDefaults(current);
      return safe.pricing_facts.options.length >= MAX_COMMERCIAL_OPTIONS
        ? safe
        : {
            ...safe,
            pricing_facts: {
              ...safe.pricing_facts,
              options: [
                ...safe.pricing_facts.options,
                createPricingOption(safe.pricing_facts.options.length + 1),
              ],
            },
          };
    });
  }, [onChange]);

  const patchPricingOption = useCallback(
    (index: number, patch: Partial<PricingOptionFact>) => {
      onChange((current) => {
        const safe = ensureFactsDefaults(current);
        return {
          ...safe,
          pricing_facts: {
            ...safe.pricing_facts,
            options: safe.pricing_facts.options.map((item, itemIndex) =>
              itemIndex === index ? { ...item, ...patch } : item
            ),
          },
        };
      });
    },
    [onChange]
  );

  const removePricingOption = useCallback(
    (index: number) => {
      onChange((current) => {
        const safe = ensureFactsDefaults(current);
        return {
          ...safe,
          pricing_facts: {
            ...safe.pricing_facts,
            options: safe.pricing_facts.options.filter(
              (_, itemIndex) => itemIndex !== index
            ),
          },
        };
      });
    },
    [onChange]
  );

  const addHotel = useCallback(() => {
    const index = services.hotels.length;
    onChange((current) => {
      const safe = ensureFactsDefaults(current);
      return {
        ...safe,
        service_facts: {
          ...safe.service_facts,
          hotels: [...safe.service_facts.hotels, newHotelFact()],
        },
      };
    });
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
    syncHotelsFromItinerary,
    addPricingOption,
    patchPricingOption,
    removePricingOption,
    sections,
    status,
  };
}
