"use client";

import { useCallback, useMemo, useState, type Dispatch, type ReactNode, type SetStateAction } from "react";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";
import CustomSelect from "../ui/CustomSelect";
import { DestinationInput } from "./DestinationInputs";
import TravelDesignerPicker from "./TravelDesignerPicker";
import AccommodationPicker from "./AccommodationPicker";
import type { AccommodationProfile, TravelDesignerProfile } from "../../lib/quotationApi";
import { BrochureAssetsEditor, MediaSlotRenderer, type MediaSlotValue, type MediaWorkspace } from "./MediaSlotRenderer";
import {
  createItineraryDay,
  createPricingOption,
  CURRENCY_OPTIONS,
  dateForItineraryDay,
  ensureFactsDefaults,
  formatMinorAmount,
  minorAmountFromInput,
  minorAmountToInput,
  routeDestinationRefsFromItinerary,
  type ItineraryDayFact,
  type HotelFact,
  MAX_COMMERCIAL_OPTIONS,
  type PricingOptionFact,
  type QuotationFacts,
  type QuotationOptions,
  type DraftMediaSelections,
} from "./factsTypes";

type Props = {
  facts: QuotationFacts;
  options: QuotationOptions;
  pending?: boolean;
  draftMediaSelections: DraftMediaSelections;
  onDraftMediaSelectionChange: (fieldId: string, value: MediaSlotValue) => void;
  onChange: Dispatch<SetStateAction<QuotationFacts>>;
  onSubmit: () => void;
};

const inputClass = cn(
  getTypographyClassName("bodyMd"),
  "min-h-11 w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60",
);

function daysBetween(startDate: string | null, endDate: string | null): number | null {
  if (!startDate || !endDate) return null;
  const start = new Date(`${startDate}T00:00:00.000Z`);
  const end = new Date(`${endDate}T00:00:00.000Z`);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || end < start) return null;
  return Math.floor((end.getTime() - start.getTime()) / 86_400_000) + 1;
}

function fieldIsBlank(day: ItineraryDayFact): boolean {
  return !day.destination && !day.destination_ref && !day.summary && !day.overnight && !day.highlights.length && !day.meals.length && !day.notes.length;
}

function emptyHotel(): HotelFact {
  return { accommodation_id: null, destination: null, destination_ref: null, name: null, room_type: null, check_in: null, check_out: null, intro: null, phone: null, display_city: null, display_date: null, hotel_asset: null, room_asset: null };
}

function hotelFromProfile(profile: AccommodationProfile): HotelFact {
  return { accommodation_id: profile.id, destination: profile.destination, destination_ref: profile.destination_ref, name: profile.name, room_type: profile.room_type, check_in: profile.check_in, check_out: profile.check_out, intro: profile.intro, phone: profile.phone, display_city: profile.display_city, display_date: profile.display_date, hotel_asset: profile.hotel_asset, room_asset: profile.room_asset };
}

function Field({ label, value, onChange, type = "text", required = false, min }: { label: string; value: string | number | null; onChange: (value: string) => void; type?: string; required?: boolean; min?: number }) {
  return <label className="flex flex-col gap-2"><span className={cn(getTypographyClassName("label"), "flex justify-between gap-3 text-[var(--color-muted)]")}><span>{label}</span><span className={cn(getTypographyClassName("caption"), required ? "text-[var(--color-accent)]" : "text-[var(--color-muted)]")}>{required ? "Required" : "Optional"}</span></span><input className={inputClass} type={type} min={min} required={required} value={value ?? ""} onChange={(event) => onChange(event.target.value)} /></label>;
}

function IntakeCard({ title, description, alternateBg = false, children }: { title: string; description: string; alternateBg?: boolean; children: ReactNode }) {
  return <section className={cn("rounded-[var(--radius-card)] border border-[var(--color-border-strong)] p-5 shadow-[var(--elevation-card)] sm:p-6 transition-colors", alternateBg ? "bg-[color-mix(in_srgb,var(--color-surface-muted)_70%,var(--color-surface))]" : "bg-[var(--color-surface)]")}><div className="mb-5"><h2 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>{title}</h2><p className={cn(getTypographyClassName("bodySm"), "mt-1 text-[var(--color-muted)]")}>{description}</p></div>{children}</section>;
}

export default function QuotationIntakeForm({ facts: inputFacts, options, pending = false, draftMediaSelections, onDraftMediaSelectionChange, onChange, onSubmit }: Props) {
  const facts = useMemo(() => ensureFactsDefaults(inputFacts), [inputFacts]);
  const trip = facts.trip_facts;
  const customer = facts.customer_facts;
  const pricing = facts.pricing_facts;
  const [pendingRouteReduction, setPendingRouteReduction] = useState<{ endDate: string | null; length: number; startDate: string | null } | null>(null);
  const [selectedDesigner, setSelectedDesigner] = useState<TravelDesignerProfile | null>(null);
  const compatibleTemplates = useMemo(() => options.templates.filter((template) => !facts.brand_id || template.brandIds.includes(facts.brand_id)), [facts.brand_id, options.templates]);
  const durationDays = daysBetween(trip.start_date, trip.end_date);
  const mediaWorkspace = useMemo<MediaWorkspace>(() => ({ contract: options.editableContract, draftSelections: draftMediaSelections, onDraftSelectionChange: onDraftMediaSelectionChange }), [draftMediaSelections, onDraftMediaSelectionChange, options.editableContract]);

  const patchFacts = useCallback((patch: (current: QuotationFacts) => QuotationFacts) => onChange((current) => patch(ensureFactsDefaults(current))), [onChange]);
  const applyRouteDates = useCallback((startDate: string | null, endDate: string | null, nextLength: number) => {
    patchFacts((current) => {
      const currentDays = current.trip_facts.itinerary;
      const itinerary = Array.from({ length: nextLength }, (_, index) => {
        const existing = currentDays[index];
        return existing ? { ...existing, day_number: index + 1, display_date: dateForItineraryDay(startDate, index + 1) } : createItineraryDay({ index, startDate });
      });
      const destination_refs = routeDestinationRefsFromItinerary(itinerary);
      return { ...current, trip_facts: { ...current.trip_facts, start_date: startDate, end_date: endDate, itinerary, destination_refs, destinations: destination_refs.map((ref) => ref.name) } };
    });
  }, [patchFacts]);
  const changeDate = useCallback((field: "start_date" | "end_date", value: string) => {
    const nextStartDate = field === "start_date" ? value || null : trip.start_date;
    const nextEndDate = field === "end_date" ? value || null : trip.end_date;
    const nextLength = daysBetween(nextStartDate, nextEndDate);
    if (nextLength === null) {
      patchFacts((current) => ({ ...current, trip_facts: { ...current.trip_facts, [field]: value || null } }));
      return;
    }
    if (nextLength < trip.itinerary.length && trip.itinerary.slice(nextLength).some((day) => !fieldIsBlank(day))) {
      setPendingRouteReduction({ startDate: nextStartDate, endDate: nextEndDate, length: nextLength });
      return;
    }
    applyRouteDates(nextStartDate, nextEndDate, nextLength);
  }, [applyRouteDates, patchFacts, trip.end_date, trip.itinerary, trip.start_date]);
  const confirmRouteReduction = useCallback(() => {
    if (!pendingRouteReduction) return;
    applyRouteDates(pendingRouteReduction.startDate, pendingRouteReduction.endDate, pendingRouteReduction.length);
    setPendingRouteReduction(null);
  }, [applyRouteDates, pendingRouteReduction]);

  const patchDay = useCallback((index: number, patch: Partial<ItineraryDayFact>) => patchFacts((current) => {
    const rawDays = current.trip_facts.itinerary;
    const days: ItineraryDayFact[] = Array.isArray(rawDays) ? rawDays : [];
    const itinerary = days.map((day, dayIndex) => dayIndex === index ? { ...day, ...patch } : day);
    const destination_refs = routeDestinationRefsFromItinerary(itinerary);
    return { ...current, trip_facts: { ...current.trip_facts, itinerary, destination_refs, destinations: destination_refs.map((ref) => ref.name) } };
  }), [patchFacts]);

  const patchHotel = useCallback((index: number, patch: Partial<HotelFact>) => patchFacts((current) => ({ ...current, service_facts: { ...current.service_facts, hotels: current.service_facts.hotels.map((hotel, hotelIndex) => hotelIndex === index ? { ...hotel, ...patch } : hotel) } })), [patchFacts]);
  const addHotel = useCallback(() => patchFacts((current) => ({ ...current, service_facts: { ...current.service_facts, hotels: [...current.service_facts.hotels, emptyHotel()] } })), [patchFacts]);
  const removeHotel = useCallback((index: number) => patchFacts((current) => ({ ...current, service_facts: { ...current.service_facts, hotels: current.service_facts.hotels.filter((_, hotelIndex) => hotelIndex !== index) } })), [patchFacts]);

  const seedProfileMedia = useCallback((fieldId: string, r2Key: string | null | undefined) => {
    if (!r2Key || Object.prototype.hasOwnProperty.call(draftMediaSelections, fieldId)) return;
    onDraftMediaSelectionChange(fieldId, { r2Key, status: "ready", source: "manual" });
  }, [draftMediaSelections, onDraftMediaSelectionChange]);

  const addPricingOption = useCallback(() => patchFacts((current) => (current.pricing_facts.options.length >= MAX_COMMERCIAL_OPTIONS ? current : { ...current, pricing_facts: { ...current.pricing_facts, options: [...current.pricing_facts.options, createPricingOption(current.pricing_facts.options.length + 1)] } })), [patchFacts]);
  const patchPricingOption = useCallback((index: number, patch: Partial<PricingOptionFact>) => patchFacts((current) => ({ ...current, pricing_facts: { ...current.pricing_facts, options: current.pricing_facts.options.map((option, optionIndex) => optionIndex === index ? { ...option, ...patch } : option) } })), [patchFacts]);
  const removePricingOption = useCallback((index: number) => patchFacts((current) => ({ ...current, pricing_facts: { ...current.pricing_facts, options: current.pricing_facts.options.filter((_, optionIndex) => optionIndex !== index) } })), [patchFacts]);

  return <form onSubmit={(event) => { event.preventDefault(); onSubmit(); }} className="mx-auto flex w-full max-w-5xl flex-col gap-6">
    <IntakeCard title="Quotation Options" description="Choose the brand and presentation template before assembling facts." alternateBg={false}>
      <div className="grid gap-4 sm:grid-cols-2">
        {options.brands.length ? <label className="flex flex-col gap-2"><span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Brand</span><CustomSelect value={facts.brand_id} placeholder="Select brand" options={options.brands} onChange={(brandId) => patchFacts((current) => ({ ...current, brand_id: brandId, presentation_options: { ...current.presentation_options, template_id: options.templates.find((item) => item.brandIds.includes(brandId))?.id ?? current.presentation_options.template_id } }))} /></label> : null}
        {options.languages.length ? <label className="flex flex-col gap-2"><span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Language</span><CustomSelect value={facts.lang} placeholder="Select language" options={options.languages} onChange={(lang) => patchFacts((current) => ({ ...current, lang: lang as QuotationFacts["lang"] }))} /></label> : null}
        {compatibleTemplates.length ? <label className="flex flex-col gap-2"><span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Brochure template</span><CustomSelect value={facts.presentation_options.template_id} placeholder="Select template" options={compatibleTemplates} onChange={(templateId) => patchFacts((current) => ({ ...current, presentation_options: { ...current.presentation_options, template_id: templateId } }))} /></label> : null}
        <TravelDesignerPicker value={facts.presentation_options.travel_designer_id} brandId={facts.brand_id} onChange={(travelDesignerId, profile) => { setSelectedDesigner(profile ?? null); seedProfileMedia("designer.image", profile?.imageR2Key); patchFacts((current) => ({ ...current, presentation_options: { ...current.presentation_options, travel_designer_id: travelDesignerId } })); }} />
        {selectedDesigner ? <div className="sm:col-span-2 grid gap-2 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3 sm:grid-cols-3"><p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>{selectedDesigner.name}</p><p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>{selectedDesigner.email}</p><p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>{selectedDesigner.phone || "No phone"}</p></div> : null}
      </div>
    </IntakeCard>

    <IntakeCard title="Brochure media" description="Choose quote-specific images now, or let Facts generate matching R2 defaults after creation." alternateBg={true}>
      <BrochureAssetsEditor workspace={mediaWorkspace} context={{ travelDesignerId: facts.presentation_options.travel_designer_id ?? selectedDesigner?.id }} />
    </IntakeCard>

    <IntakeCard title="Trip" description="Set the travel dates, then assign a destination to each day in the route." alternateBg={false}>
      <div className="grid gap-4 sm:grid-cols-2"><Field label="Start date" required type="date" value={trip.start_date} onChange={(value) => changeDate("start_date", value)} /><Field label="End date" required type="date" value={trip.end_date} onChange={(value) => changeDate("end_date", value)} /><div className="flex flex-col gap-2"><span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Duration</span><p className={cn(getTypographyClassName("bodyMd"), "flex min-h-11 items-center rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] px-3 text-[var(--color-on-surface)]")}>{durationDays === null ? "Choose travel dates" : `${durationDays} days / ${Math.max(durationDays - 1, 0)} nights`}</p></div></div>
      <div className="mt-5 flex flex-col gap-3"><div><h3 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>Brief Route</h3><p className={cn(getTypographyClassName("bodySm"), "mt-1 text-[var(--color-muted)]")}>Each day requires factual programme details and an overnight destination.</p></div>{trip.itinerary.map((day, index) => <div key={index} className="grid items-end gap-3 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] p-4 shadow-2xs sm:grid-cols-2"><p className={cn(getTypographyClassName("bodyMd"), "sm:col-span-2 text-[var(--color-on-surface)]")}>{`Day ${index + 1}${day.display_date ? ` · ${day.display_date}` : ""}`}</p><DestinationInput label="Destination" value={day.destination} onChange={(destination) => patchDay(index, { destination, destination_ref: null })} onSelect={(destinationRef) => patchDay(index, { destination: destinationRef?.name ?? null, destination_ref: destinationRef, ...(day.overnight ? {} : { overnight: destinationRef?.name ?? null }) })} /><DestinationInput label="Overnight" value={day.overnight} onChange={(overnight) => patchDay(index, { overnight })} /><label className="sm:col-span-2 flex flex-col gap-1.5"><span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Program summary</span><textarea className={cn(inputClass, "min-h-24 py-3")} value={day.summary ?? ""} onChange={(event) => patchDay(index, { summary: event.target.value || null })} /></label><label className="flex flex-col gap-1.5"><span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Meals</span><textarea className={cn(inputClass, "min-h-20 py-3")} value={day.meals.join("\n")} onChange={(event) => patchDay(index, { meals: event.target.value.split("\n") })} /></label><label className="flex flex-col gap-1.5"><span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Notes</span><textarea className={cn(inputClass, "min-h-20 py-3")} value={day.notes.join("\n")} onChange={(event) => patchDay(index, { notes: event.target.value.split("\n") })} /></label><MediaSlotRenderer workspace={mediaWorkspace} editorRoute="facts.programme.day" context={{ index, destinationId: day.destination_ref?.id }} /></div>)}</div>
    </IntakeCard>

    <IntakeCard title="Accommodations" description="Select the stays for this quotation. They remain independent from the Brief Route." alternateBg={true}>
      <div className="flex flex-col gap-4">{facts.service_facts.hotels.map((hotel, index) => <article key={index} className="grid gap-3 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] p-4 shadow-2xs sm:grid-cols-2"><AccommodationPicker value={hotel.accommodation_id} name={hotel.name} destination={hotel.destination || hotel.display_city} onChange={(profile) => { patchHotel(index, profile ? hotelFromProfile(profile) : emptyHotel()); seedProfileMedia(`stays.hotels.${index}.hotelImage`, profile?.hotel_asset); seedProfileMedia(`stays.hotels.${index}.roomImage`, profile?.room_asset); }} /><Field label="Check-in" required type="date" value={hotel.check_in} onChange={(checkIn) => patchHotel(index, { check_in: checkIn || null })} /><Field label="Check-out" required type="date" value={hotel.check_out} onChange={(checkOut) => patchHotel(index, { check_out: checkOut || null })} /><Field label="Room type" required value={hotel.room_type} onChange={(roomType) => patchHotel(index, { room_type: roomType || null })} /><label className="sm:col-span-2 flex flex-col gap-1.5"><span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Stay notes</span><textarea className={cn(inputClass, "min-h-20 py-3")} value={hotel.intro ?? ""} onChange={(event) => patchHotel(index, { intro: event.target.value || null })} /></label><MediaSlotRenderer workspace={mediaWorkspace} editorRoute="facts.services.hotel" context={{ index, destinationId: hotel.destination_ref?.id, accommodationName: hotel.name ?? undefined, profileAssetKeys: { [`stays.hotels.${index}.hotelImage`]: hotel.hotel_asset, [`stays.hotels.${index}.roomImage`]: hotel.room_asset } }} /><button type="button" onClick={() => removeHotel(index)} className={cn(getTypographyClassName("buttonSecondary"), "min-h-10 w-fit rounded-[var(--radius-button)] bg-rose-700 !text-white hover:bg-rose-800 px-3.5 shadow-2xs border border-transparent transition-all")}>Remove accommodation</button></article>)}<button type="button" onClick={addHotel} className={cn(getTypographyClassName("buttonSecondary"), "min-h-14 rounded-[var(--radius-button)] border-2 border-dashed border-[var(--color-accent)] bg-[color-mix(in_srgb,var(--color-accent-wash)_60%,white)] px-4 text-[var(--color-accent)] transition-all duration-200 hover:bg-[var(--color-accent)] hover:!text-white hover:shadow-xs")}>+ Add accommodation</button></div>
    </IntakeCard>

    <IntakeCard title="Pricing options" description="Add a price per traveler and group total for each option. You can complete pricing later in Facts." alternateBg={false}>
      <div className="flex flex-col gap-3"><div className="flex items-center justify-between gap-3"><span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>{`Options (${pricing.options.length}/${MAX_COMMERCIAL_OPTIONS})`}</span><button type="button" disabled={pricing.options.length >= MAX_COMMERCIAL_OPTIONS} onClick={addPricingOption} className={cn(getTypographyClassName("buttonSecondary"), "min-h-10 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-3.5 shadow-2xs border border-transparent transition-all disabled:opacity-50")}>Add option</button></div>{pricing.options.map((option, index) => { const expectedTotal = customer.adults && option.per_traveler_amount_minor ? option.per_traveler_amount_minor * customer.adults : null; const inconsistent = expectedTotal !== null && option.group_total_amount_minor !== null && expectedTotal !== option.group_total_amount_minor; return <article key={option.id} className="grid gap-3 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] p-4 shadow-2xs sm:grid-cols-2"><Field label="Option label" required value={option.label} onChange={(label) => patchPricingOption(index, { label })} /><div className="flex flex-col gap-1.5"><span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Currency</span><CustomSelect value={option.currency} placeholder="Select currency" options={CURRENCY_OPTIONS} onChange={(currency) => patchPricingOption(index, { currency })} /></div><Field label="Per traveler price" required type="number" value={minorAmountToInput(option.per_traveler_amount_minor, option.currency)} onChange={(value) => patchPricingOption(index, { per_traveler_amount_minor: minorAmountFromInput(value, option.currency) })} /><Field label="Group total price" required type="number" value={minorAmountToInput(option.group_total_amount_minor, option.currency)} onChange={(value) => patchPricingOption(index, { group_total_amount_minor: minorAmountFromInput(value, option.currency) })} />{inconsistent ? <p className={cn(getTypographyClassName("caption"), "sm:col-span-2 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] p-3 text-[var(--color-muted)]")}>{`For ${customer.adults} adults, the per traveler price equals ${formatMinorAmount(expectedTotal, option.currency, facts.lang ?? "en")}; the entered group total is kept unchanged.`}</p> : null}<button type="button" onClick={() => removePricingOption(index)} className={cn(getTypographyClassName("buttonSecondary"), "min-h-10 w-fit rounded-[var(--radius-button)] bg-rose-700 !text-white hover:bg-rose-800 px-3.5 shadow-2xs border border-transparent transition-all")}>Remove option</button></article>; })}</div>
    </IntakeCard>

    <IntakeCard title="Travellers" description="These facts personalize the quotation and guide its language and recommendations." alternateBg={true}>
      <div className="grid gap-4 sm:grid-cols-2"><Field label="Customer name" required value={customer.customer_name} onChange={(customerName) => patchFacts((current) => ({ ...current, customer_facts: { ...current.customer_facts, customer_name: customerName || null } }))} /><Field label="Nationality" required value={customer.nationality} onChange={(nationality) => patchFacts((current) => ({ ...current, customer_facts: { ...current.customer_facts, nationality: nationality || null } }))} /><Field label="Adults" required min={1} type="number" value={customer.adults} onChange={(adults) => patchFacts((current) => ({ ...current, customer_facts: { ...current.customer_facts, adults: adults ? Number(adults) : null } }))} /><Field label="Children" min={0} type="number" value={customer.children ?? 0} onChange={(children) => patchFacts((current) => ({ ...current, customer_facts: { ...current.customer_facts, children: children ? Number(children) : 0 } }))} /><Field label="Guest profile" value={customer.guest_profile} onChange={(guestProfile) => patchFacts((current) => ({ ...current, customer_facts: { ...current.customer_facts, guest_profile: guestProfile || null } }))} /></div>
      <label className="mt-4 flex flex-col gap-2"><span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Special requirements</span><span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>Optional. Add one factual requirement per line.</span><textarea className={cn(inputClass, "min-h-28 rounded-[var(--radius-card)] py-3")} value={trip.special_requirements.join("\n")} onChange={(event) => patchFacts((current) => ({ ...current, trip_facts: { ...current.trip_facts, special_requirements: event.target.value.split("\n") } }))} /></label>
    </IntakeCard>
    <button type="submit" disabled={pending} className={cn(getTypographyClassName("buttonPrimary"), "min-h-12 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-6 shadow-md border border-transparent transition-all disabled:opacity-50")}>{pending ? "Creating quotation…" : "Create quotation & continue to Facts"}</button>
    {pendingRouteReduction !== null ? <div role="dialog" aria-modal="true" aria-label="Confirm route reduction" className="fixed inset-0 z-50 grid place-items-center bg-[color-mix(in_srgb,var(--color-contrast)_35%,transparent)] p-5"><section className="w-full max-w-md rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)]"><h2 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>Shorten the route?</h2><p className={cn(getTypographyClassName("bodySm"), "mt-2 text-[var(--color-muted)]")}>The removed final days contain route information. Confirm to discard them.</p><div className="mt-5 flex justify-end gap-3"><button type="button" onClick={() => setPendingRouteReduction(null)} className={cn(getTypographyClassName("buttonSecondary"), "min-h-10 rounded-[var(--radius-button)] bg-[var(--color-contrast)] !text-white hover:opacity-90 px-4 shadow-2xs border border-transparent transition-all")}>Keep current route</button><button type="button" onClick={confirmRouteReduction} className={cn(getTypographyClassName("buttonPrimary"), "min-h-10 rounded-[var(--radius-button)] bg-rose-700 !text-white hover:bg-rose-800 px-4 shadow-xs border border-transparent transition-all")}>Discard final days</button></div></section></div> : null}
  </form>;
}
