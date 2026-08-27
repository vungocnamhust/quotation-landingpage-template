import type { DestinationRef } from "../quotation-workspace/factsTypes.ts";

export type { DestinationRef };

// destination_type vocab mirrors core/rules/catalog_vocab.py DESTINATION_TYPE (15.2b) — keep
// both files' comments pointing at each other when either changes.
export type DestinationType = "country" | "region" | "province" | "city" | "sub_zone";

export interface DestinationCatalogItem {
  id: string;
  name: string;
  slug: string;
  countrySlug?: string | null;
  regionSlug?: string | null;
  provinceSlug?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  isActive?: boolean;
  aliases?: string[];
  mediaPrefix?: string | null;
  defaultMediaPrefix?: string;
  matchedFrom?: string;
  parentId?: string | null;
  destinationType?: DestinationType;
  countryCode?: string | null;
  iataCode?: string | null;
  timezone?: string;
  mergedIntoId?: string | null;
}

/** DestinationRef plus display-only badge fields (15.2b §5.2) — never written into facts. */
export interface DestinationSearchResult extends DestinationRef {
  destinationType?: DestinationType;
  iataCode?: string | null;
  mergedIntoId?: string | null;
}

export type DestinationSelectMode = "single" | "multiple";
export type DestinationSelectSize = "sm" | "md" | "lg";
export type DestinationSelectVariant = "default" | "compact" | "inline";

export interface DestinationSelectProps {
  /** Mode: "single" (default) or "multiple" */
  mode?: DestinationSelectMode;

  /** Single mode value: string (name) or DestinationRef */
  value?: string | DestinationRef | null;

  /** Multiple mode values: array of DestinationRef */
  values?: DestinationRef[];

  /**
   * Unified Change Handler:
   * - Single mode: (name: string | null, ref: DestinationRef | null) => void
   * - Multiple mode: (refs: DestinationRef[]) => void
   */
  onChange?: (value: string | DestinationRef[] | null, ref?: DestinationRef | null) => void;

  /** @deprecated Prefer using `onChange(value, ref)` which provides the DestinationRef in the 2nd argument. */
  onSelect?: (ref: DestinationRef | null) => void;

  /** Label rendered above input */
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
  size?: DestinationSelectSize;

  /** Visual variant */
  variant?: DestinationSelectVariant;

  /** Allow entering free text when not found in catalog */
  allowCustom?: boolean;

  /** Container class */
  className?: string;

  /** Custom input class */
  inputClassName?: string;

  /** Custom menu / popover class */
  menuClassName?: string;

  /** Validation error message */
  error?: string | null;

  /** Helper text displayed below input */
  helperText?: string;

  /** Accessibility label */
  "aria-label"?: string;

  /** ID for accessibility */
  id?: string;
}
