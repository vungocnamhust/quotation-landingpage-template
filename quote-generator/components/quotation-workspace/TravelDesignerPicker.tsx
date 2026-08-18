"use client";

import { TravelDesignerSelect } from "../travel-designer/TravelDesignerSelect";
import type { TravelDesignerProfile } from "../travel-designer/types";

type Props = {
  value: string | null;
  brandId?: string | null;
  disabled?: boolean;
  onChange: (profileId: string | null, profile?: TravelDesignerProfile) => void;
};

/**
 * Backward-compatible adapter wrapper for TravelDesignerPicker.
 * Delegating all logic to the standardized TravelDesignerSelect component.
 */
export default function TravelDesignerPicker({
  value,
  brandId,
  disabled = false,
  onChange,
}: Props) {
  return (
    <TravelDesignerSelect
      label="Travel designer"
      value={value}
      brandId={brandId}
      disabled={disabled}
      onChange={(profileId, profile) => onChange(profileId, profile ?? undefined)}
    />
  );
}
