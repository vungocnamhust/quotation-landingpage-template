"use client";

import { AccommodationSelect } from "../accommodation/AccommodationSelect.tsx";
import type { AccommodationProfile, AccommodationProfileInput } from "../accommodation/types.ts";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";

type Props = {
  value: string | null;
  name?: string | null;
  destination?: string | null;
  destinationId?: string | null;
  disabled?: boolean;
  onChange: (profile: AccommodationProfile | null) => void;
};

export const blankInput = (): AccommodationProfileInput => ({
  destinationId: "",
  name: "",
  room_type: null,
  intro: null,
  phone: null,
  display_city: null,
  display_date: null,
  hotel_asset: null,
  room_asset: null,
});

export const inputClass = cn(
  getTypographyClassName("bodyMd"),
  "min-h-11 w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)]"
);

export function profileInput(profile: AccommodationProfile): AccommodationProfileInput {
  return {
    destinationId: profile.destination_id,
    name: profile.name,
    room_type: profile.room_type,
    intro: profile.intro,
    phone: profile.phone,
    display_city: profile.display_city,
    display_date: profile.display_date,
    hotel_asset: profile.hotel_asset,
    room_asset: profile.room_asset,
  };
}

/**
 * Backward-compatible adapter wrapper for AccommodationPicker.
 * Delegating all logic to the standardized AccommodationSelect component.
 */
export default function AccommodationPicker({
  value,
  name,
  destination,
  destinationId,
  disabled = false,
  onChange,
}: Props) {
  return (
    <AccommodationSelect
      label="Accommodation"
      value={value}
      name={name}
      destination={destination}
      destinationId={destinationId}
      disabled={disabled}
      onChange={onChange}
    />
  );
}
