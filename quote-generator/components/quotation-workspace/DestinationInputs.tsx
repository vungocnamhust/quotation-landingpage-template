"use client";

import { DestinationSelect } from "../destination/DestinationSelect";
import type { DestinationRef } from "./factsTypes";

export type { DestinationRef } from "./factsTypes";

/**
 * Backward-compatibility wrapper for DestinationInput using the new unified DestinationSelect component.
 */
export function DestinationInput({
  value,
  onChange,
  onSelect,
  disabled = false,
  label = "Destination",
}: {
  value: string | null;
  onChange: (value: string | null) => void;
  onSelect?: (ref: DestinationRef | null) => void;
  disabled?: boolean;
  label?: string;
}) {
  return (
    <DestinationSelect
      mode="single"
      label={label}
      value={value}
      disabled={disabled}
      onChange={(name, ref) => {
        const destName =
          typeof name === "string"
            ? name
            : Array.isArray(name)
              ? name[0]?.name ?? null
              : null;
        onChange(destName);
        onSelect?.(ref ?? null);
      }}
      onSelect={onSelect}
    />
  );
}

/**
 * Backward-compatibility wrapper for DestinationMultiSelect using the new unified DestinationSelect component.
 */
export function DestinationMultiSelect({
  refs,
  onChange,
  disabled = false,
}: {
  refs: DestinationRef[];
  onChange: (refs: DestinationRef[]) => void;
  disabled?: boolean;
}) {
  return (
    <DestinationSelect
      mode="multiple"
      label="Destinations"
      values={refs}
      disabled={disabled}
      onChange={(nextRefs) => {
        if (Array.isArray(nextRefs)) {
          onChange(nextRefs);
        }
      }}
    />
  );
}
