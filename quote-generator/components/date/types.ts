import type { ReactNode } from "react";

export type DateInputMode = "iso" | "text";
export type DateInputSize = "sm" | "md" | "lg";
export type DateInputVariant = "default" | "compact" | "inline";

export interface DateInputProps {
  /** Mode: "iso" (YYYY-MM-DD standard date input) or "text" (freeform / formatted display date) */
  mode?: DateInputMode;

  /** Value string (ISO date YYYY-MM-DD or display string) */
  value?: string | null;

  /** Callback when date changes */
  onChange?: (value: string | null) => void;

  /** Label rendered above or beside the input */
  label?: string;

  /** Slot for extra action on the label line (e.g. Auto-fill button, duration hint) */
  labelAction?: ReactNode;

  /** Placeholder text */
  placeholder?: string;

  /** Minimum date (YYYY-MM-DD for ISO mode) */
  min?: string | null;

  /** Maximum date (YYYY-MM-DD for ISO mode) */
  max?: string | null;

  /** Required state */
  required?: boolean;

  /** Disabled state */
  disabled?: boolean;

  /** ReadOnly state */
  readOnly?: boolean;

  /** Size variant: "sm" (h-9 compact), "md" (min-h-11 standard), "lg" (min-h-12) */
  size?: DateInputSize;

  /** Visual variant: "default" | "compact" | "inline" */
  variant?: DateInputVariant;

  /** Allow clear button (X) when a value is present (default: true) */
  allowClear?: boolean;

  /** Validation error message */
  error?: string | null;

  /** Helper text displayed below input */
  helperText?: string;

  /** Container class */
  className?: string;

  /** Custom input element class */
  inputClassName?: string;

  /** Accessibility label */
  "aria-label"?: string;

  /** Custom element ID */
  id?: string;
}
