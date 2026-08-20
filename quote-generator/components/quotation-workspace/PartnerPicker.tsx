"use client";

import { PartnerSelect } from "../partner/PartnerSelect.tsx";
import type { PartnerProfile } from "../partner/types.ts";

type Props = {
  value: string | null;
  disabled?: boolean;
  onChange: (partnerId: string | null, partner?: PartnerProfile) => void;
};

/**
 * Backward-compatible adapter wrapper for PartnerPicker.
 * Delegating all logic to the standardized PartnerSelect component.
 */
export default function PartnerPicker({
  value,
  disabled = false,
  onChange,
}: Props) {
  return (
    <PartnerSelect
      label="Partner Agency"
      value={value}
      disabled={disabled}
      onChange={(partnerId, partner) => onChange(partnerId, partner ?? undefined)}
    />
  );
}
