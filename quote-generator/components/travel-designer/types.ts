import type { TravelDesignerInput, TravelDesignerProfile } from "../../lib/quotationApi";

export type { TravelDesignerInput, TravelDesignerProfile };

export type TravelDesignerSelectSize = "sm" | "md" | "lg";
export type TravelDesignerSelectVariant = "default" | "compact" | "inline";

export interface TravelDesignerSelectProps {
  /** Selected Travel Designer Profile ID */
  value?: string | null;

  /** Filter or associate by brandId */
  brandId?: string | null;

  /** Unified change handler returning both profileId and canonical profile object */
  onChange?: (profileId: string | null, profile?: TravelDesignerProfile | null) => void;

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
  size?: TravelDesignerSelectSize;

  /** Visual variant */
  variant?: TravelDesignerSelectVariant;

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
