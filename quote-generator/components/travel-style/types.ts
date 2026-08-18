import type { TravelStyleCategoryGroup, TravelStyleTagItem } from "../../lib/quotationApi";

export type { TravelStyleCategoryGroup, TravelStyleTagItem };

export type TravelStyleSelectSize = "sm" | "md";

export interface TravelStyleSelectProps {
  /** Label rendered above selector */
  label?: string;

  /** Comma-separated tag string or single travel style value */
  value?: string | null;

  /** Unified change handler */
  onChange?: (value: string | null) => void;

  /** Disabled state */
  disabled?: boolean;

  /** Size variant */
  size?: TravelStyleSelectSize;

  /** Allow entering custom free-text travel style tags */
  allowCustom?: boolean;

  /** Custom container class */
  className?: string;

  /** Helper text displayed below input */
  helperText?: string;
}
