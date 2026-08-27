import type {
  SupplierCancellationPolicy,
  SupplierCancellationTier,
  SupplierChildAgeBand,
  SupplierChildPolicy,
  SupplierContact,
  SupplierInput,
  SupplierPaymentTerms,
  SupplierPreferredStatus,
  SupplierProfile,
  SupplierQualityTier,
  SupplierType,
} from "../../lib/quotationApi.ts";

export type {
  SupplierCancellationPolicy,
  SupplierCancellationTier,
  SupplierChildAgeBand,
  SupplierChildPolicy,
  SupplierContact,
  SupplierInput,
  SupplierPaymentTerms,
  SupplierPreferredStatus,
  SupplierProfile,
  SupplierQualityTier,
  SupplierType,
};

export type SupplierSelectSize = "sm" | "md" | "lg";
export type SupplierSelectVariant = "default" | "compact" | "inline";

export interface SupplierSelectProps {
  /** Selected Supplier ID */
  value?: string | null;

  /** Unified change handler returning both supplierId and canonical supplier object */
  onChange?: (supplierId: string | null, supplier?: SupplierProfile | null) => void;

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
  size?: SupplierSelectSize;

  /** Visual variant */
  variant?: SupplierSelectVariant;

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
