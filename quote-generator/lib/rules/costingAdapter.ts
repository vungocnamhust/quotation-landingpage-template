/**
 * Canonical Adapter Layer for the Costing Workbench (15.4) — bridges the raw
 * `CostingWorkbenchResponse` API payload (`lib/quotationApi.ts`) to the row
 * shape the grid components render, and back to write payloads. Pure shape
 * mapping only; all cost/sell math lives server-side (see `costingReconciler.ts`
 * module doc for why this module never recomputes totals).
 */
import type {
  CostingSummary,
  CostingWorkbenchResponse,
  ServiceLineProfile,
  ServiceLineWriteInput,
} from "../quotationApi.ts";
import type { CostingGroupRow } from "./costingReconciler.ts";

export type CostingRowView = CostingGroupRow & {
  line: ServiceLineProfile;
};

/**
 * `CostingWorkbenchResponse.items` → grid rows. The server-confirmed
 * `cost_minor`/`sell_minor` on each line are carried through untouched —
 * there is no client recomputation step here.
 */
export function toCostingRows(workbench: CostingWorkbenchResponse): CostingRowView[] {
  return workbench.items.map((line) => ({
    id: line.id,
    dayNumber: line.day_number,
    category: line.category,
    costMinor: line.cost_minor,
    sellMinor: line.sell_minor,
    line,
  }));
}

export function summaryTotals(summary: CostingSummary): { costTotalMinor: number; sellTotalMinor: number; marginBps: number } {
  return {
    costTotalMinor: summary.cost_total_minor,
    sellTotalMinor: summary.sell_total_minor,
    marginBps: summary.margin_bps,
  };
}

/** Form-state shape for the "add/edit service line" flow — one canonical draft for catalog-pick or manual entry. */
export type ServiceLineDraftForm = {
  dayNumber: number | null;
  serviceDate: string | null;
  category: string | null;
  subcategory: string | null;
  title: string | null;
  supplierId: string | null;
  productId: string | null;
  rateId: string | null;
  priceLineId: number | null;
  unit: string | null;
  timeBasis: string | null;
  qtyUnit: number;
  qtyTime: number;
  unitCostMinor: number | null;
  costCurrency: string | null;
  fxRatePpm: number | null;
  sellOverrideMinor: number | null;
  note: string | null;
  sortOrder: number;
};

export function emptyServiceLineDraft(defaults: Partial<ServiceLineDraftForm> = {}): ServiceLineDraftForm {
  return {
    dayNumber: null,
    serviceDate: null,
    category: null,
    subcategory: null,
    title: null,
    supplierId: null,
    productId: null,
    rateId: null,
    priceLineId: null,
    unit: null,
    timeBasis: null,
    qtyUnit: 1,
    qtyTime: 1,
    unitCostMinor: null,
    costCurrency: null,
    fxRatePpm: null,
    sellOverrideMinor: null,
    note: null,
    sortOrder: 0,
    ...defaults,
  };
}

export function draftFromServiceLine(line: ServiceLineProfile): ServiceLineDraftForm {
  return {
    dayNumber: line.day_number,
    serviceDate: line.service_date,
    category: line.category,
    subcategory: line.subcategory,
    title: line.title,
    supplierId: line.supplier_id,
    productId: line.product_id,
    rateId: line.tariff_id,
    priceLineId: line.price_line_id,
    unit: line.unit,
    timeBasis: line.time_basis,
    qtyUnit: line.qty_unit,
    qtyTime: line.qty_time,
    unitCostMinor: line.unit_cost_minor,
    costCurrency: line.cost_currency,
    fxRatePpm: line.fx_rate_ppm,
    sellOverrideMinor: line.sell_override_minor,
    note: line.note,
    sortOrder: line.sort_order,
  };
}

export function draftToWriteInput(draft: ServiceLineDraftForm, baseCostingRevision: number): ServiceLineWriteInput {
  return {
    base_costing_revision: baseCostingRevision,
    day_number: draft.dayNumber,
    service_date: draft.serviceDate,
    category: draft.category,
    subcategory: draft.subcategory,
    title: draft.title,
    supplier_id: draft.supplierId,
    product_id: draft.productId,
    rate_id: draft.rateId,
    price_line_id: draft.priceLineId,
    unit: draft.unit,
    time_basis: draft.timeBasis,
    qty_unit: draft.qtyUnit,
    qty_time: draft.qtyTime,
    unit_cost_minor: draft.unitCostMinor,
    cost_currency: draft.costCurrency,
    fx_rate_ppm: draft.fxRatePpm,
    sell_override_minor: draft.sellOverrideMinor,
    note: draft.note,
    sort_order: draft.sortOrder,
  };
}

export const costingAdapter = {
  toCostingRows,
  summaryTotals,
  emptyServiceLineDraft,
  draftFromServiceLine,
  draftToWriteInput,
};
