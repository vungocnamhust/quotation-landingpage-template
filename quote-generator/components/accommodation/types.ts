import type {
  AccommodationProfile,
  AccommodationProfileInput,
} from "../../lib/quotationApi.ts";

export type { AccommodationProfile, AccommodationProfileInput };

export type AccommodationSelectSize = "sm" | "md" | "lg";
export type AccommodationSelectVariant = "default" | "compact" | "inline";

export interface AccommodationSelectProps {
  /** Selected accommodation ID */
  value?: string | null;

  /** Fallback accommodation name for display if unmapped */
  name?: string | null;

  /** Filter by destination ID or name */
  destinationId?: string | null;
  destination?: string | null;

  /** Unified change handler: receives profile as primary argument, id as secondary argument, and customName as third argument */
  onChange?: (profile: AccommodationProfile | null, id?: string | null, customName?: string | null) => void;

  /** Allow typing and selecting custom accommodation name */
  allowCustom?: boolean;

  /** Label rendered above selector */
  label?: string;

  /** Placeholder text */
  placeholder?: string;

  /** Disabled state */
  disabled?: boolean;

  /** ReadOnly state */
  readOnly?: boolean;

  /** Required state */
  required?: boolean;

  /** Size variant */
  size?: AccommodationSelectSize;

  /** Visual variant */
  variant?: AccommodationSelectVariant;

  /** Allow opening create/manage drawer */
  allowManage?: boolean;

  /** Custom container class */
  className?: string;

  /** Validation error message */
  error?: string | null;

  /** Helper text displayed below input */
  helperText?: string;

  /** Element id for accessibility */
  id?: string;

  /** Accessibility label */
  "aria-label"?: string;
}
