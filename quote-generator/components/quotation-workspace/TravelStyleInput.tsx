"use client";

import { TravelStyleSelect } from "../travel-style/TravelStyleSelect";

type TravelStyleInputProps = {
  label?: string;
  value: string | null;
  disabled?: boolean;
  onChange: (value: string | null) => void;
};

/**
 * Backward-compatible adapter wrapper for TravelStyleInput.
 * Delegating all logic to the standardized TravelStyleSelect component.
 */
export default function TravelStyleInput({
  label = "Travel Style",
  value,
  disabled = false,
  onChange,
}: TravelStyleInputProps) {
  return (
    <TravelStyleSelect
      label={label}
      value={value}
      disabled={disabled}
      onChange={onChange}
    />
  );
}
