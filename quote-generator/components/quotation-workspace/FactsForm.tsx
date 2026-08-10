"use client";

import {
  memo,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type Dispatch,
  type ReactNode,
  type SetStateAction,
} from "react";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";
import { CheckCircle2, AlertCircle, Sparkles } from "lucide-react";
import FactsNavigator, {
  type FactSectionId,
  type FactSectionStatus,
} from "./FactsNavigator";
import { DestinationInput, DestinationMultiSelect } from "./DestinationInputs";
import TravelDesignerPicker from "./TravelDesignerPicker";
import CustomSelect from "../ui/CustomSelect";
import type {
  HotelFact,
  ItineraryDayFact,
  QuotationFacts,
  QuotationOptions,
  ResolvedFacts,
} from "./factsTypes";
import { CURRENCY_OPTIONS, MAX_COMMERCIAL_OPTIONS, createItineraryDay, createPricingOption, dateForItineraryDay, ensureFactsDefaults, formatMinorAmount, isRenderablePricingOption, minorAmountFromInput, minorAmountToInput, routeDestinationRefsFromItinerary } from "./factsTypes";
import { BrochureAssetsEditor, MediaSlotRenderer, type MediaWorkspace } from "./MediaSlotRenderer";
import type { TravelDesignerProfile } from "../../lib/quotationApi";
import type { FactsDeepLink } from "./editableHandoff";

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
const inputClass = cn(
  getTypographyClassName("bodyMd"),
  "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] transition-shadow duration-200 focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60",
);
const lines = (values: string[]) => values.join("\n");
// This is an editor codec, not a persistence normalizer. Trimming here makes a
// controlled textarea erase a just-typed space or newline on the next render.
const toLines = (value: string) => value.split("\n");
const newHotel = (): HotelFact => ({
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

function Field({
  label,
  value,
  onChange,
  type = "text",
  disabled,
  required,
  id,
  aiHint,
}: {
  label: string;
  value: string | number | null;
  onChange: (value: string) => void;
  type?: string;
  disabled?: boolean;
  required?: boolean;
  id?: string;
  aiHint?: string;
}) {
  return (
    <label className="flex flex-col gap-2">
      <span
        className={cn(
          getTypographyClassName("label"),
          "flex justify-between gap-3 text-[var(--color-muted)]",
        )}
      >
        <span className="flex items-center gap-1.5 min-w-0">
          <span className="truncate">{label}</span>
          {aiHint ? (
            <span title={aiHint} className="inline-flex items-center gap-0.5 text-[var(--color-accent)] cursor-help shrink-0" aria-label={aiHint}>
              <Sparkles size={12} />
            </span>
          ) : null}
        </span>
        <span
          className={cn(
            getTypographyClassName("caption"),
            required
              ? "text-[var(--color-accent)]"
              : "text-[var(--color-muted)]",
          )}
        >
          {required ? "Required" : "Optional"}
        </span>
      </span>
      <input
        id={id}
        aria-required={required}
        className={inputClass}
        type={type}
        disabled={disabled}
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}
function Area({
  label,
  value,
  onChange,
  disabled,
  hint,
  aiHint,
}: {
  label: string;
  value: string | null;
  onChange: (value: string) => void;
  disabled?: boolean;
  hint?: string;
  aiHint?: string;
}) {
  return (
    <label className="flex flex-col gap-2">
      <span
        className={cn(
          getTypographyClassName("label"),
          "flex justify-between gap-3 text-[var(--color-muted)]",
        )}
      >
        <span className="flex items-center gap-1.5 min-w-0">
          <span className="truncate">{label}</span>
          {aiHint ? (
            <span title={aiHint} className="inline-flex items-center gap-0.5 text-[var(--color-accent)] cursor-help shrink-0" aria-label={aiHint}>
              <Sparkles size={12} />
            </span>
          ) : null}
        </span>
      </span>
      {hint ? (
        <span
          className={cn(
            getTypographyClassName("caption"),
            "text-[var(--color-muted)]",
          )}
        >
          {hint}
        </span>
      ) : null}
      <textarea
        className={cn(inputClass, "min-h-24 p-3 rounded-[var(--radius-card)]")}
        disabled={disabled}
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function SelectField({
  label,
  value,
  onChange,
  options = [],
  disabled,
  required,
}: {
  label: string;
  value: string | null;
  onChange: (value: string | null) => void;
  options?: Array<{ id: string; label: string }>;
  disabled?: boolean;
  required?: boolean;
}) {
  return (
    <div className="flex flex-col gap-2">
      <span
        className={cn(
          getTypographyClassName("label"),
          "flex justify-between gap-3 text-[var(--color-muted)]",
        )}
      >
        <span>{label}</span>
        <span
          className={cn(
            getTypographyClassName("caption"),
            required
              ? "text-[var(--color-accent)]"
              : "text-[var(--color-muted)]",
          )}
        >
          {required ? "Required" : "Optional"}
        </span>
      </span>
      <CustomSelect
        disabled={disabled}
        value={value}
        placeholder={`Select ${label.toLowerCase()}`}
        options={options}
        onChange={(nextVal) => onChange(nextVal || null)}
      />
    </div>
  );
}

function FactCard({
  id,
  title,
  subtitle,
  status,
  alternateBg = false,
  children,
}: {
  id: FactSectionId;
  title: string;
  subtitle?: string;
  status: FactSectionStatus;
  alternateBg?: boolean;
  children: ReactNode;
}) {
  return (
    <section
      id={`facts-${id}`}
      data-facts-section
      className={cn(
        "scroll-mt-6 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] p-5 shadow-[var(--elevation-card)] sm:p-6 transition-colors",
        alternateBg
          ? "bg-[color-mix(in_srgb,var(--color-surface-muted)_70%,var(--color-surface))]"
          : "bg-[var(--color-surface)]"
      )}
    >
      <header className="mb-5 flex items-start justify-between gap-4 border-b border-[var(--color-border)] pb-4">
        <div>
          <h2
            className={cn(
              getTypographyClassName("cardTitle"),
              "text-[var(--color-on-surface)]",
            )}
          >
            {title}
          </h2>
          <p
            className={cn(
              getTypographyClassName("bodySm"),
              "mt-1 text-[var(--color-muted)]",
            )}
          >
            {subtitle ?? status.detail}
          </p>
        </div>
        <span
          className={cn(
            getTypographyClassName("caption"),
            "flex items-center gap-1.5 shrink-0",
            status.complete
              ? "text-[var(--color-accent)]"
              : "text-[var(--color-muted)]",
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

const DayEditor = memo(function DayEditor({
  day,
  index,
  startDate,
  open,
  readOnly,
  onToggle,
  onPatch,
  onRemove,
  mediaWorkspace,
}: {
  day: ItineraryDayFact;
  index: number;
  startDate: string | null;
  open: boolean;
  readOnly: boolean;
  onToggle: (index: number) => void;
  onPatch: (index: number, patch: Partial<ItineraryDayFact>) => void;
  onRemove: (index: number) => void;
  mediaWorkspace?: MediaWorkspace;
}) {
  const patch = <K extends keyof ItineraryDayFact>(
    key: K,
    value: ItineraryDayFact[K],
  ) => onPatch(index, { [key]: value } as Partial<ItineraryDayFact>);
  const complete = Boolean(
    day.destination && (day.summary || day.highlights.length),
  );
  const derivedDate = day.display_date || dateForItineraryDay(startDate, day.day_number ?? index + 1);
  return (
    <article
      id={`facts-day-${index}`}
      className={cn(
        "facts-repeatable content-visibility-auto rounded-[var(--radius-card)] transition-all duration-200",
        open
          ? "border-2 border-[var(--color-accent)] border-l-4 border-l-[var(--color-accent)] bg-[var(--color-surface-white)] shadow-md"
          : "border border-[var(--color-border-strong)] bg-[var(--color-surface-white)] hover:border-[var(--color-accent)] shadow-2xs",
      )}
    >
      <button
        type="button"
        onClick={() => onToggle(index)}
        aria-expanded={open}
        className={cn(
          "flex min-h-14 w-full items-center justify-between gap-3 px-4 text-left transition-colors focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[var(--color-focus)]",
          open
            ? "rounded-t-[calc(var(--radius-card)-2px)] bg-[color-mix(in_srgb,var(--color-accent-wash)_45%,var(--color-surface-white))]"
            : "rounded-[var(--radius-card)] hover:bg-[var(--color-surface-hover)]",
        )}
      >
        <span className="min-w-0">
          <span
            className={cn(
              getTypographyClassName("cardTitle"),
              "block text-[var(--color-on-surface)]",
            )}
          >
            Day {day.day_number ?? index + 1}{derivedDate ? ` · ${derivedDate}` : ""}
          </span>
          <span
            className={cn(
              getTypographyClassName("caption"),
              "block truncate text-[var(--color-muted)]",
            )}
          >
            {day.destination || "Destination needed"}
          </span>
        </span>
        <span
          className={cn(
            getTypographyClassName("caption"),
            "rounded-full px-2.5 py-0.5 shrink-0",
            complete
              ? "bg-[var(--color-accent-wash)] text-[var(--color-accent)]"
              : "bg-[var(--color-surface-muted)] text-[var(--color-muted)]",
          )}
        >
          {complete ? "Ready" : "Needs facts"}
        </span>
      </button>
      {open ? (
        <div className="facts-accordion-body grid gap-4 border-t border-[var(--color-border-strong)] bg-[var(--color-surface-white)] p-4 sm:grid-cols-2">
          {/* ESSENTIAL FIELDS */}
          <Field
            id={`day-${index}-number`}
            label="Day"
            required
            type="number"
            disabled={readOnly}
            value={day.day_number}
            onChange={(value) => {
              const dayNumber = Number(value) || null;
              onPatch(index, { day_number: dayNumber, display_date: dateForItineraryDay(startDate, dayNumber) });
            }}
          />
          <DestinationInput
            label={`Day ${day.day_number ?? index + 1} destination`}
            disabled={readOnly}
            value={day.destination}
            onChange={(value) => patch("destination", value)}
            onSelect={(ref) => patch("destination_ref", ref)}
          />
          <div className="sm:col-span-2 grid gap-4 sm:grid-cols-2">
            <Area
              label="Programme summary"
              disabled={readOnly}
              value={day.summary}
              onChange={(value) => patch("summary", value || null)}
              hint="Required for an AI day narrative when no highlights are supplied."
            />
            <Area
              label="Highlights"
              disabled={readOnly}
              value={lines(day.highlights)}
              onChange={(value) => patch("highlights", toLines(value))}
              hint="One factual item per line."
            />
          </div>
          <div className="sm:col-span-2">
            <Area
              label="Meals"
              disabled={readOnly}
              value={lines(day.meals)}
              onChange={(value) => patch("meals", toLines(value))}
            />
          </div>

          <Field label="Sense of pace" disabled={readOnly} value={day.sense_of_pace} onChange={(value) => patch("sense_of_pace", value || null)} />
          <Field label="Overnight" disabled={readOnly} value={day.overnight} onChange={(value) => patch("overnight", value || null)} />
          <Field label="Date" disabled value={derivedDate} onChange={() => undefined} />
          <div className="sm:col-span-2">
            <Area label="Notes" disabled={readOnly} value={lines(day.notes)} onChange={(value) => patch("notes", toLines(value))} />
          </div>

          {mediaWorkspace ? <MediaSlotRenderer workspace={mediaWorkspace} editorRoute="facts.programme.day" readOnly={readOnly} context={{ index, destinationId: day.destination_ref?.id }} /> : null}
          {!readOnly ? (
            <button
              type="button"
              onClick={() => onRemove(index)}
              className={cn(
                getTypographyClassName("buttonSecondary"),
                "min-h-10 w-fit rounded-[var(--radius-button)] bg-rose-700 !text-white hover:bg-rose-800 px-4 shadow-2xs border border-transparent transition-all",
              )}
            >
              Remove day
            </button>
          ) : null}
        </div>
      ) : null}
    </article>
  );
});
const HotelEditor = memo(function HotelEditor({
  hotel,
  index,
  open,
  readOnly,
  onToggle,
  onPatch,
  onRemove,
  mediaWorkspace,
}: {
  hotel: HotelFact;
  index: number;
  open: boolean;
  readOnly: boolean;
  onToggle: (index: number) => void;
  onPatch: (index: number, patch: Partial<HotelFact>) => void;
  onRemove: (index: number) => void;
  mediaWorkspace?: MediaWorkspace;
}) {
  const patch = <K extends keyof HotelFact>(key: K, value: HotelFact[K]) =>
    onPatch(index, { [key]: value } as Partial<HotelFact>);
  const complete = Boolean(hotel.name && hotel.destination);
  return (
    <article
      id={`facts-hotel-${index}`}
      className={cn(
        "facts-repeatable content-visibility-auto rounded-[var(--radius-card)] transition-all duration-200",
        open
          ? "border-2 border-[var(--color-accent)] border-l-4 border-l-[var(--color-accent)] bg-[var(--color-surface-white)] shadow-md"
          : "border border-[var(--color-border-strong)] bg-[var(--color-surface-white)] hover:border-[var(--color-accent)] shadow-2xs",
      )}
    >
      <button
        type="button"
        onClick={() => onToggle(index)}
        aria-expanded={open}
        className={cn(
          "flex min-h-14 w-full items-center justify-between gap-3 px-4 text-left transition-colors focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[var(--color-focus)]",
          open
            ? "rounded-t-[calc(var(--radius-card)-2px)] bg-[color-mix(in_srgb,var(--color-accent-wash)_45%,var(--color-surface-white))]"
            : "rounded-[var(--radius-card)] hover:bg-[var(--color-surface-hover)]",
        )}
      >
        <span className="min-w-0">
          <span
            className={cn(
              getTypographyClassName("cardTitle"),
              "block truncate text-[var(--color-on-surface)]",
            )}
          >
            {hotel.name || `Hotel ${index + 1}`}
          </span>
          <span
            className={cn(
              getTypographyClassName("caption"),
              "block truncate text-[var(--color-muted)]",
            )}
          >
            {hotel.destination || "Destination needed"}
          </span>
        </span>
        <span
          className={cn(
            getTypographyClassName("caption"),
            "rounded-full px-2.5 py-0.5 shrink-0",
            complete
              ? "bg-[var(--color-accent-wash)] text-[var(--color-accent)]"
              : "bg-[var(--color-surface-muted)] text-[var(--color-muted)]",
          )}
        >
          {complete ? "Ready" : "Needs facts"}
        </span>
      </button>
      {open ? (
        <div className="facts-accordion-body grid gap-4 border-t border-[var(--color-border-strong)] bg-[var(--color-surface-white)] p-4 sm:grid-cols-2">
          {/* ESSENTIAL FIELDS */}
          <DestinationInput
            label={`Hotel ${index + 1} destination`}
            disabled={readOnly}
            value={hotel.destination}
            onChange={(value) => patch("destination", value)}
            onSelect={(ref) => patch("destination_ref", ref)}
          />
          <Field
            id={`hotel-${index}-name`}
            label="Hotel name"
            disabled={readOnly}
            value={hotel.name}
            onChange={(value) => patch("name", value || null)}
          />
          <Field
            label="Room type"
            disabled={readOnly}
            value={hotel.room_type}
            onChange={(value) => patch("room_type", value || null)}
          />
          <Field
            label="Check-in"
            type="date"
            disabled={readOnly}
            value={hotel.check_in}
            onChange={(value) => patch("check_in", value || null)}
          />
          <Field
            label="Check-out"
            type="date"
            disabled={readOnly}
            value={hotel.check_out}
            onChange={(value) => patch("check_out", value || null)}
          />
          <div className="sm:col-span-2">
            <Area
              label="Stay notes"
              disabled={readOnly}
              value={hotel.intro}
              onChange={(value) => patch("intro", value || null)}
            />
          </div>

          <Field label="Hotel phone" disabled={readOnly} value={hotel.phone} onChange={(value) => patch("phone", value || null)} />
          <Field label="Display city" disabled={readOnly} value={hotel.display_city} onChange={(value) => patch("display_city", value || null)} />
          <Field label="Display dates" disabled={readOnly} value={hotel.display_date} onChange={(value) => patch("display_date", value || null)} />
          {mediaWorkspace ? <MediaSlotRenderer workspace={mediaWorkspace} editorRoute="facts.services.hotel" readOnly={readOnly} context={{
            index,
            destinationId: hotel.destination_ref?.id,
            accommodationName: hotel.name ?? undefined,
            profileAssetKeys: {
              [`stays.hotels.${index}.hotelImage`]: hotel.hotel_asset,
              [`stays.hotels.${index}.roomImage`]: hotel.room_asset,
            },
          }} /> : null}
          {!readOnly ? (
            <button
              type="button"
              onClick={() => onRemove(index)}
              className={cn(
                getTypographyClassName("buttonSecondary"),
                "min-h-10 w-fit rounded-[var(--radius-button)] bg-rose-700 !text-white hover:bg-rose-800 px-4 shadow-2xs border border-transparent transition-all",
              )}
            >
              Remove hotel
            </button>
          ) : null}
        </div>
      ) : null}
    </article>
  );
});

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
  const facts = useMemo(() => ensureFactsDefaults(inputFacts), [inputFacts]);
  const trip = facts.trip_facts;
  const customer = facts.customer_facts;
  const services = facts.service_facts;
  const pricing = facts.pricing_facts;
  const booking = facts.booking_facts;
  const finalization = facts.finalization_facts;
  const presentation = facts.presentation_options;

  const [activeDay, setActiveDay] = useState<number | null>(
    trip.itinerary.length ? 0 : null,
  );
  const [activeHotel, setActiveHotel] = useState<number | null>(
    services.hotels.length ? 0 : null,
  );
  const [selectedDesigner, setSelectedDesigner] = useState<TravelDesignerProfile | null>(null);
  const storedDesigner = mediaWorkspace?.document?.designer as {
    name?: string;
    email?: string;
    phone?: string;
    image?: { r2Key?: string };
  } | undefined;
  const designerIdentity = selectedDesigner ?? (storedDesigner?.name ? {
    id: presentation.travel_designer_id ?? "",
    name: storedDesigner.name,
    email: storedDesigner.email ?? "",
    phone: storedDesigner.phone ?? "",
    isActive: true,
  } : null);
  const focusTarget = useRef<{ kind: "day" | "hotel" | "pricingOption" | "bookingTerm"; index: number } | null>(
    null,
  );

  const update = useCallback(
    <K extends keyof QuotationFacts>(key: K, value: QuotationFacts[K]) =>
      onChange((current) => ({ ...ensureFactsDefaults(current), [key]: value })),
    [onChange],
  );
  const patchDay = useCallback(
    (index: number, patch: Partial<ItineraryDayFact>) =>
      onChange((current) => {
        const safe = ensureFactsDefaults(current);
        const itinerary = safe.trip_facts.itinerary.map((item, itemIndex) =>
          itemIndex === index ? { ...item, ...patch } : item,
        );
        const destination_refs = routeDestinationRefsFromItinerary(itinerary);
        return {
          ...safe,
          trip_facts: {
            ...safe.trip_facts,
            itinerary,
            destination_refs,
            destinations: destination_refs.map((ref) => ref.name),
          },
        };
      }),
    [onChange],
  );
  const patchHotel = useCallback(
    (index: number, patch: Partial<HotelFact>) =>
      onChange((current) => {
        const safe = ensureFactsDefaults(current);
        return {
          ...safe,
          service_facts: {
            ...safe.service_facts,
            hotels: safe.service_facts.hotels.map((item, itemIndex) =>
              itemIndex === index ? { ...item, ...patch } : item,
            ),
          },
        };
      }),
    [onChange],
  );
  const toggleDay = useCallback(
    (index: number) =>
      setActiveDay((current) => (current === index ? null : index)),
    [],
  );
  const toggleHotel = useCallback(
    (index: number) =>
      setActiveHotel((current) => (current === index ? null : index)),
    [],
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
              (_, itemIndex) => itemIndex !== index,
            ),
          },
        };
      });
      setActiveDay(null);
      onDayRemoved?.(index);
    },
    [onChange, onDayRemoved],
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
              (_, itemIndex) => itemIndex !== index,
            ),
          },
        };
      });
      setActiveHotel(null);
      onHotelRemoved?.(index);
    },
    [onChange, onHotelRemoved],
  );
  const addDay = useCallback(() => {
    const index = trip.itinerary.length;
    onChange((current) => {
      const safe = ensureFactsDefaults(current);
      return {
        ...safe,
        trip_facts: {
          ...safe.trip_facts,
          itinerary: [...safe.trip_facts.itinerary, createItineraryDay({ index, startDate: safe.trip_facts.start_date })],
        },
      };
    });
    setActiveDay(index);
    focusTarget.current = { kind: "day", index };
  }, [onChange, trip.itinerary.length]);
  const patchTripStartDate = useCallback((value: string) => {
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
            display_date: dateForItineraryDay(startDate, day.day_number ?? index + 1),
          })),
        },
      };
    });
  }, [onChange]);
  const addPricingOption = useCallback(() => {
    onChange((current) => {
      const safe = ensureFactsDefaults(current);
      return safe.pricing_facts.options.length >= MAX_COMMERCIAL_OPTIONS ? safe : ({
        ...safe,
        pricing_facts: { ...safe.pricing_facts, options: [...safe.pricing_facts.options, createPricingOption(safe.pricing_facts.options.length + 1)] },
      });
    });
  }, [onChange]);
  const patchPricingOption = useCallback((index: number, patch: Partial<QuotationFacts["pricing_facts"]["options"][number]>) => {
    onChange((current) => {
      const safe = ensureFactsDefaults(current);
      return {
        ...safe,
        pricing_facts: { ...safe.pricing_facts, options: safe.pricing_facts.options.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item) },
      };
    });
  }, [onChange]);
  const removePricingOption = useCallback((index: number) => {
    onChange((current) => {
      const safe = ensureFactsDefaults(current);
      return { ...safe, pricing_facts: { ...safe.pricing_facts, options: safe.pricing_facts.options.filter((_, itemIndex) => itemIndex !== index) } };
    });
  }, [onChange]);
  const addHotel = useCallback(() => {
    const index = services.hotels.length;
    onChange((current) => {
      const safe = ensureFactsDefaults(current);
      return {
        ...safe,
        service_facts: {
          ...safe.service_facts,
          hotels: [...safe.service_facts.hotels, newHotel()],
        },
      };
    });
    setActiveHotel(index);
    focusTarget.current = { kind: "hotel", index };
  }, [onChange, services.hotels.length]);
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
              : `booking-term-${target.index}-label`,
      )
      ?.focus();
    focusTarget.current = null;
  }, [facts]);
  const deepLinkKey = deepLink ? `${deepLink.section}:${deepLink.focus?.kind ?? "section"}:${deepLink.focus?.index ?? ""}` : "";
  useEffect(() => {
    if (!deepLink) return;
    document.getElementById(`facts-${deepLink.section}`)?.scrollIntoView({ behavior: "auto", block: "start" });
    const focus = deepLink.focus;
    if (!focus) return;
    if (!["day", "hotel", "pricingOption", "bookingTerm"].includes(focus.kind)) return;
    const controlId = focus.kind === "day"
      ? `day-${focus.index}-number`
      : focus.kind === "hotel"
        ? `hotel-${focus.index}-name`
        : focus.kind === "pricingOption"
          ? `pricing-${focus.index}-label`
          : `booking-term-${focus.index}-label`;
    let focusFrame: number | undefined;
    const frame = requestAnimationFrame(() => {
      if (focus.kind === "day" && focus.index < trip.itinerary.length) setActiveDay(focus.index);
      if (focus.kind === "hotel" && focus.index < services.hotels.length) setActiveHotel(focus.index);
      focusFrame = requestAnimationFrame(() => document.getElementById(controlId)?.focus());
    });
    return () => {
      cancelAnimationFrame(frame);
      if (focusFrame !== undefined) cancelAnimationFrame(focusFrame);
    };
  }, [deepLinkKey, deepLink, services.hotels.length, trip.itinerary.length]);
  const sections = useMemo<FactSectionStatus[]>(
    () => [
      {
        id: "trip",
        label: "Trip",
        detail: trip.destinations.length || trip.itinerary.length ? "Route ready" : "Route needed",
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
        detail: `${trip.itinerary.filter((day) => day.destination && (day.summary || day.highlights.length)).length}/${trip.itinerary.length} days ready`,
        complete:
          trip.itinerary.length > 0 &&
          trip.itinerary.every(
            (day) => day.destination && (day.summary || day.highlights.length),
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
        detail: pricing.options.length ? `${pricing.options.length} option${pricing.options.length === 1 ? "" : "s"} added` : "Optional",
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
          presentation.travel_designer_id || booking.description,
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
    ],
  );
  const status = (id: FactSectionId) =>
    sections.find((item) => item.id === id)!;
  const canSubmit = Boolean(onSubmit && (!readOnly || allowSubmitWhenReadOnly));
  return (
    <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_18rem]">
      <div className="order-2 flex min-w-0 flex-col gap-5 lg:order-1">
        {sourceNote ? (
          <p
            className={cn(
              getTypographyClassName("caption"),
              "rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3 text-[var(--color-muted)]",
            )}
          >
            {sourceNote}
          </p>
        ) : null}
        {mediaWorkspace ? <section className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] sm:p-6"><h2 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>Brochure assets</h2><p className={cn(getTypographyClassName("bodySm"), "mt-1 text-[var(--color-muted)]")}>Quote-specific images are canonical Facts.</p><div className="mt-4"><BrochureAssetsEditor workspace={mediaWorkspace} readOnly={readOnly} context={{
          travelDesignerId: presentation.travel_designer_id ?? selectedDesigner?.id,
        }} /></div></section> : null}
        <FactCard
          id="trip"
          title="Trip"
          subtitle="Essential trip details. AI will write the brochure narrative from these facts."
          status={status("trip")}
          alternateBg={true}
        >
          <div className="grid gap-4 sm:grid-cols-2">
            {options?.brands ? (
              <SelectField
                label="Brand"
                required
                disabled={readOnly}
                value={facts.brand_id}
                options={options.brands}
                onChange={(value) => update("brand_id", value)}
              />
            ) : (
              <Field
                label="Brand"
                required
                disabled={readOnly}
                value={facts.brand_id}
                onChange={(value) => update("brand_id", value || null)}
              />
            )}
            {options?.languages ? (
              <SelectField
                label="Language"
                required
                disabled={readOnly}
                value={facts.lang}
                options={options.languages}
                onChange={(value) =>
                  update("lang", value as QuotationFacts["lang"])
                }
              />
            ) : null}
            {options?.templates ? (
              <SelectField
                label="Template"
                value={facts.presentation_options.template_id}
                options={(options.templates ?? []).filter(
                  (item) =>
                    !facts.brand_id ||
                    (item.brandIds ?? []).includes(facts.brand_id),
                )}
                onChange={(value) =>
                  update("presentation_options", {
                    ...facts.presentation_options,
                    template_id: value,
                  })
                }
              />
            ) : null}
            <TravelDesignerPicker
              value={facts.presentation_options.travel_designer_id}
              brandId={facts.brand_id}
              disabled={readOnly && !allowPresentationEdits}
              onChange={(value, profile) => {
                setSelectedDesigner(profile ?? null);
                if (value && onDesignerSelected) { void onDesignerSelected(value); return; }
                onChange((current) => ({ ...current, presentation_options: { ...current.presentation_options, travel_designer_id: value } }));
              }}
            />
            <div className="sm:col-span-2 grid gap-3 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3 sm:grid-cols-3">
              <Field label="Designer name" disabled value={designerIdentity?.name ?? null} onChange={() => undefined} />
              <Field label="Designer email" disabled value={designerIdentity?.email ?? null} onChange={() => undefined} />
              <Field label="Designer phone" disabled value={designerIdentity?.phone ?? null} onChange={() => undefined} />
            </div>
            <p className={cn(getTypographyClassName("bodySm"), "sm:col-span-2 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3 text-[var(--color-muted)]")}>Trip title and brochure narrative are created and reviewed in Content Studio after these route facts are saved.</p>
            <Field
              label="Start date"
              type="date"
              disabled={readOnly}
              value={trip.start_date}
              onChange={patchTripStartDate}
            />
            <Field
              label="End date"
              type="date"
              disabled={readOnly}
              value={trip.end_date}
              onChange={(value) =>
                update("trip_facts", { ...trip, end_date: value || null })
              }
            />
            <div className="sm:col-span-2">
              <DestinationMultiSelect
                disabled={readOnly}
                refs={trip.destination_refs ?? []}
                onChange={(refs) =>
                  update("trip_facts", {
                    ...trip,
                    destination_refs: refs,
                    destinations: refs.map((ref) => ref.name),
                  })
                }
              />
            </div>
            <div className="sm:col-span-2 grid gap-3 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3 sm:grid-cols-2">
              <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>Derived route · {resolvedFacts?.routeLabel || "Add itinerary destinations"}</p>
              <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>Derived dates · {resolvedFacts?.travelDatesLabel || "Add start and end dates"}</p>
              <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>Derived duration · {resolvedFacts?.durationDays ?? "—"} days / {resolvedFacts?.durationNights ?? "—"} nights</p>
              <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>Derived party · {resolvedFacts?.partyLabel || "Add traveller counts"}</p>
            </div>
            <div className="sm:col-span-2">
              <Area
                label="Special requirements"
                disabled={readOnly}
                value={lines(trip.special_requirements)}
                onChange={(value) =>
                  update("trip_facts", {
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
        </FactCard>
        <FactCard
          id="travellers"
          title="Travellers"
          subtitle="Essential guest details — AI uses these to personalize greeting and story tone."
          status={status("travellers")}
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <Field
              label="Customer name"
              disabled={readOnly}
              value={customer.customer_name}
              onChange={(value) =>
                update("customer_facts", {
                  ...customer,
                  customer_name: value || null,
                })
              }
            />
            <Field
              label="Adults"
              type="number"
              disabled={readOnly}
              value={customer.adults}
              onChange={(value) =>
                update("customer_facts", {
                  ...customer,
                  adults: value ? Number(value) : null,
                })
              }
            />
            <Field
              label="Children"
              type="number"
              disabled={readOnly}
              value={customer.children}
              onChange={(value) =>
                update("customer_facts", {
                  ...customer,
                  children: value ? Number(value) : null,
                })
              }
            />
            <Field
              label="Nationality"
              disabled={readOnly}
              value={customer.nationality}
              onChange={(value) =>
                update("customer_facts", {
                  ...customer,
                  nationality: value || null,
                })
              }
            />
            <Field
              label="Guest profile"
              disabled={readOnly}
              value={customer.guest_profile}
              onChange={(value) =>
                update("customer_facts", {
                  ...customer,
                  guest_profile: value || null,
                })
              }
            />
            <Field
              label="Market"
              disabled={readOnly}
              value={customer.market}
              onChange={(value) =>
                update("customer_facts", { ...customer, market: value || null })
              }
            />
          </div>
        </FactCard>
        <FactCard
          id="programme"
          title="Daily programme"
          subtitle="Provide day destinations and highlights so AI can generate the daily itinerary story."
          status={status("programme")}
          alternateBg={true}
        >
          <div className="flex flex-col gap-3">
            {trip.itinerary.map((day, index) => (
              <DayEditor
                key={index}
                day={day}
                index={index}
                startDate={trip.start_date}
                open={activeDay === index}
                readOnly={readOnly}
                onToggle={toggleDay}
                onPatch={patchDay}
                onRemove={removeDay}
                mediaWorkspace={mediaWorkspace}
              />
            ))}
            {!readOnly ? (
              <button
                type="button"
                onClick={addDay}
                className={cn(
                  getTypographyClassName("buttonSecondary"),
                  "min-h-14 rounded-[var(--radius-button)] border-2 border-dashed border-[var(--color-accent)] bg-[color-mix(in_srgb,var(--color-accent-wash)_60%,white)] px-4 text-[var(--color-accent)] transition-all duration-200 hover:bg-[var(--color-accent)] hover:text-white hover:shadow-xs",
                )}
              >
                + Add itinerary day
              </button>
            ) : null}
          </div>
        </FactCard>
        <FactCard
          id="services"
          title="Hotels & services"
          subtitle="Accommodations and factual inclusions/exclusions."
          status={status("services")}
        >
          <div className="flex flex-col gap-4">
            {services.hotels.map((hotel, index) => (
              <HotelEditor
                key={index}
                hotel={hotel}
                index={index}
                open={activeHotel === index}
                readOnly={readOnly}
                onToggle={toggleHotel}
                onPatch={patchHotel}
                onRemove={removeHotel}
                mediaWorkspace={mediaWorkspace}
              />
            ))}
            {!readOnly ? (
              <button
                type="button"
                onClick={addHotel}
                className={cn(
                  getTypographyClassName("buttonSecondary"),
                  "min-h-14 rounded-[var(--radius-button)] border-2 border-dashed border-[var(--color-accent)] bg-[color-mix(in_srgb,var(--color-accent-wash)_60%,white)] px-4 text-[var(--color-accent)] transition-all duration-200 hover:bg-[var(--color-accent)] hover:text-white hover:shadow-xs",
                )}
              >
                + Add hotel
              </button>
            ) : null}
            <div className="grid gap-4 sm:grid-cols-2">
              <Area
                label="Inclusions"
                disabled={readOnly}
                value={lines(services.inclusions)}
                onChange={(value) =>
                  update("service_facts", {
                    ...services,
                    inclusions: toLines(value),
                  })
                }
                hint="One factual item per line."
              />
              <Area
                label="Exclusions"
                disabled={readOnly}
                value={lines(services.exclusions)}
                onChange={(value) =>
                  update("service_facts", {
                    ...services,
                    exclusions: toLines(value),
                  })
                }
                hint="One factual item per line."
              />
            </div>
            <Area
              label="Room notes"
              disabled={readOnly}
              value={services.room_notes}
              onChange={(value) =>
                update("service_facts", {
                  ...services,
                  room_notes: value || null,
                })
              }
            />
          </div>
        </FactCard>
        <FactCard
          id="commercial"
          title="Commercial"
          subtitle="Each option carries its own currency, per traveler price, and group total."
          status={status("commercial")}
          alternateBg={true}
        >
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between gap-3"><span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Pricing options ({pricing.options.length}/{MAX_COMMERCIAL_OPTIONS})</span><button type="button" disabled={readOnly || pricing.options.length >= MAX_COMMERCIAL_OPTIONS} onClick={addPricingOption} className={cn(getTypographyClassName("buttonSecondary"), "min-h-10 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-3.5 shadow-2xs border border-transparent transition-all disabled:opacity-50")}>Add option</button></div>
            {pricing.options.map((option, index) => { const expectedTotal = customer.adults && option.per_traveler_amount_minor ? option.per_traveler_amount_minor * customer.adults : null; const inconsistent = expectedTotal !== null && option.group_total_amount_minor !== null && expectedTotal !== option.group_total_amount_minor; return <div id={`pricing-option-${index}`} key={option.id} className="grid gap-3 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface-white)] p-4 shadow-2xs sm:grid-cols-2">
              <Field id={`pricing-${index}-label`} label="Option label" required disabled={readOnly} value={option.label} onChange={(value) => patchPricingOption(index, { label: value })} />
              <SelectField label="Currency" disabled={readOnly} value={option.currency} options={CURRENCY_OPTIONS} onChange={(value) => patchPricingOption(index, { currency: value })} />
              <Field label="Per traveler price" required type="number" disabled={readOnly} value={minorAmountToInput(option.per_traveler_amount_minor, option.currency)} onChange={(value) => patchPricingOption(index, { per_traveler_amount_minor: minorAmountFromInput(value, option.currency) })} />
              <Field label="Group total price" required type="number" disabled={readOnly} value={minorAmountToInput(option.group_total_amount_minor, option.currency)} onChange={(value) => patchPricingOption(index, { group_total_amount_minor: minorAmountFromInput(value, option.currency) })} />
              {inconsistent ? <p className={cn(getTypographyClassName("caption"), "sm:col-span-2 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] p-3 text-[var(--color-muted)]")}>{`For ${customer.adults} adults, the per traveler price equals ${formatMinorAmount(expectedTotal, option.currency, facts.lang ?? "en")}; the entered group total is kept unchanged.`}</p> : null}
              <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>{isRenderablePricingOption(option) ? "Will appear in the brochure." : "Complete the option before it can be saved."}</p>
              {!readOnly ? <button type="button" onClick={() => removePricingOption(index)} className={cn(getTypographyClassName("buttonSecondary"), "min-h-10 w-fit rounded-[var(--radius-button)] bg-rose-700 !text-white hover:bg-rose-800 px-3.5 shadow-2xs border border-transparent transition-all")}>Remove option</button> : null}
            </div>; })}
            <Area label="Pricing note" disabled={readOnly} value={lines(pricing.conditions)} onChange={(value) => update("pricing_facts", { ...pricing, conditions: toLines(value) })} hint="Optional. One factual note per line; the brochure hides this block when empty." />
          </div>
        </FactCard>
        <FactCard
          id="seller"
          title="BOOKING & PAYMENT TERMS"
          subtitle="Booking terms, confirmation checklist, and travel designer profile copy."
          status={status("seller")}
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2 flex flex-col gap-4">
              <Area
                label="Booking information"
                disabled={readOnly}
                value={booking.description}
                onChange={(value) =>
                  update("booking_facts", {
                    ...booking,
                    description: value,
                  })
                }
              />
              <Area
                label="Required before confirmation"
                disabled={readOnly}
                value={lines(finalization.required_items)}
                onChange={(value) =>
                  update("finalization_facts", {
                    ...finalization,
                    required_items: toLines(value),
                  })
                }
                hint="One requirement per line."
              />
            </div>
            <div className="sm:col-span-2 flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <p className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Booking term details (Key & Value)</p>
                {!readOnly ? (
                  <button
                    type="button"
                    onClick={() =>
                      update("booking_facts", {
                        ...booking,
                        items: [...booking.items, { key: null, label: "Deposit", body: null }],
                      })
                    }
                    className={cn(
                      getTypographyClassName("buttonSecondary"),
                      "min-h-8 rounded-[var(--radius-button)] border border-[var(--color-border)] px-3 py-1 text-[var(--color-on-surface)] hover:bg-[var(--color-surface-muted)] transition-colors",
                    )}
                  >
                    + Add term
                  </button>
                ) : null}
              </div>
              {booking.items.map((item, index) => (
                <div id={`booking-term-${index}`} key={item.key ?? index} className="grid gap-3 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-white)] p-4 shadow-2xs sm:grid-cols-12 items-start">
                  <div className="sm:col-span-4 flex flex-col gap-2">
                    <Field id={`booking-term-${index}-label`} label="Term label (Key)" disabled={readOnly} value={item.label} onChange={(value) => update("booking_facts", { ...booking, items: booking.items.map((current, currentIndex) => currentIndex === index ? { ...current, label: value || null } : current) })} />
                    {!readOnly ? (
                      <div className="flex flex-wrap gap-1 mt-1">
                        <button type="button" onClick={() => update("booking_facts", { ...booking, items: booking.items.map((c, i) => i === index ? { ...c, label: "Deposit" } : c) })} className={cn(getTypographyClassName("caption"), "px-2 py-0.5 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-muted)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-on-surface)] transition-colors")}>+ Deposit</button>
                        <button type="button" onClick={() => update("booking_facts", { ...booking, items: booking.items.map((c, i) => i === index ? { ...c, label: "Balance" } : c) })} className={cn(getTypographyClassName("caption"), "px-2 py-0.5 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-muted)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-on-surface)] transition-colors")}>+ Balance</button>
                        <button type="button" onClick={() => update("booking_facts", { ...booking, items: booking.items.map((c, i) => i === index ? { ...c, label: "Cancellation" } : c) })} className={cn(getTypographyClassName("caption"), "px-2 py-0.5 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-muted)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-on-surface)] transition-colors")}>+ Cancellation</button>
                      </div>
                    ) : null}
                  </div>
                  <div className="sm:col-span-8 flex flex-col gap-2">
                    <Area label="Term details (Value)" hint="Plain text details." disabled={readOnly} value={item.body} onChange={(value) => update("booking_facts", { ...booking, items: booking.items.map((current, currentIndex) => currentIndex === index ? { ...current, body: value || null } : current) })} />
                    {!readOnly ? (
                      <div className="flex justify-end mt-1">
                        <button type="button" onClick={() => update("booking_facts", { ...booking, items: booking.items.filter((_, i) => i !== index) })} className={cn(getTypographyClassName("caption"), "text-rose-600 hover:underline")}>Remove term</button>
                      </div>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>

            <div className="sm:col-span-2 grid gap-4 sm:grid-cols-2">
              <Field label="Booking terms title" disabled={readOnly} value={booking.title} onChange={(value) => update("booking_facts", { ...booking, title: value || null })} />
              <Field label="Required-items title" disabled={readOnly} value={finalization.required_title} onChange={(value) => update("finalization_facts", { ...finalization, required_title: value || null })} />
              <Field label="After-confirmation title" disabled={readOnly} value={finalization.after_confirmation_title} onChange={(value) => update("finalization_facts", { ...finalization, after_confirmation_title: value || null })} />
              <div className="sm:col-span-2">
                <Area label="After confirmation" disabled={readOnly} value={lines(finalization.after_confirmation_items)} onChange={(value) => update("finalization_facts", { ...finalization, after_confirmation_items: toLines(value) })} hint="One follow-up item per line." />
              </div>
            </div>
          </div>
        </FactCard>
        {canSubmit ? (
          <div className="flex justify-end lg:hidden">
            <button
              type="button"
              onClick={onSubmit}
              disabled={pending}
              className={cn(
                getTypographyClassName("buttonPrimary"),
                "min-h-11 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-6 shadow-md border border-transparent transition-all disabled:opacity-50",
              )}
            >
              {pending ? "Saving facts…" : submitLabel}
            </button>
          </div>
        ) : null}
      </div>
      <div className="order-1 lg:order-2">
        <FactsNavigator
          sections={sections}
          activeSection={deepLink?.section}
          onSubmit={canSubmit ? onSubmit : undefined}
          submitLabel={submitLabel}
          pending={pending}
        />
      </div>
    </div>
  );
}
