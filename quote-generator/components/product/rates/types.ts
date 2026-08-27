// Mirrors core/rules/catalog_vocab.py (OCCUPANCY_BASIS/PRICE_FOR/RATE_BASIS) — 15.3.
import type {
  RateAggregateInput,
  RateBasis,
  RateBlackoutWindow,
  RateChannel,
  RateDocumentType,
  RateLifecycleStatus,
  RateOccupancyBasis,
  RatePriceFor,
  RatePriceLine,
  RateProfile,
  RateSource,
  RateSourceInput,
  RateSupplement,
} from "../../../lib/quotationApi.ts";

export type {
  RateAggregateInput,
  RateBasis,
  RateBlackoutWindow,
  RateChannel,
  RateDocumentType,
  RateLifecycleStatus,
  RateOccupancyBasis,
  RatePriceFor,
  RatePriceLine,
  RateProfile,
  RateSource,
  RateSourceInput,
  RateSupplement,
};

export const OCCUPANCY_BASIS_OPTIONS: RateOccupancyBasis[] = ["sgl", "dbl", "twn", "trpl", "quad", "na"];
export const PRICE_FOR_OPTIONS: RatePriceFor[] = [
  "adult",
  "child",
  "infant",
  "room",
  "vehicle",
  "guide",
  "group",
  "unit",
];
export const RATE_BASIS_OPTIONS: RateBasis[] = ["net", "gross_commissionable"];
export const DOCUMENT_TYPE_OPTIONS: RateDocumentType[] = [
  "rate_sheet",
  "contract",
  "amendment",
  "quotation",
  "promotion",
  "manual_note",
];
export const CHANNEL_OPTIONS: RateChannel[] = ["email", "zalo", "whatsapp", "portal", "in_person", "internal"];

export const LIFECYCLE_STATUS_LABEL: Record<RateLifecycleStatus, string> = {
  draft: "Draft",
  active: "Active",
  superseded: "Superseded",
  expired: "Expired",
};

export function blankPriceLine(): RatePriceLine {
  return {
    price_for: "adult",
    occupancy_basis: "na",
    unit: "person",
    amount_minor: 0,
    tier_min_pax: null,
    tier_max_pax: null,
    note: null,
    sort_order: 0,
  };
}
