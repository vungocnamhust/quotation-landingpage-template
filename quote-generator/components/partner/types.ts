import type { PartnerInput, PartnerProfile } from "../../lib/quotationApi";

export type { PartnerInput, PartnerProfile };

export type PartnerSelectSize = "sm" | "md" | "lg";
export type PartnerSelectVariant = "default" | "compact" | "inline";

export interface PartnerSelectProps {
  /** Selected Partner ID */
  value?: string | null;

  /** Unified change handler returning both partnerId and canonical partner object */
  onChange?: (partnerId: string | null, partner?: PartnerProfile | null) => void;

  /** Label rendered above input */
  label?: string;

  /** Placeholder text when unselected */
  placeholder?: string;

  /** Disabled state */
  disabled?: boolean;

  /** ReadOnly state */
  readOnly?: boolean;

  /** Required field */
  required?: boolean;

  /** Size variant */
  size?: PartnerSelectSize;

  /** Visual variant */
  variant?: PartnerSelectVariant;

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
