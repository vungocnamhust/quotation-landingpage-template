import type {
  CostingSheetProfile,
  CostingSummary,
  CostingWorkbenchResponse,
  ServiceLineProfile,
  ServiceLineWriteInput,
} from "../../lib/quotationApi.ts";

export type {
  CostingSheetProfile,
  CostingSummary,
  CostingWorkbenchResponse,
  ServiceLineProfile,
  ServiceLineWriteInput,
};

/** Exactly one of the two is set — a workbench anchors to a request or a quotation (chốt #1). */
export type CostingWorkbenchAnchor = { requestId: string; quotationId?: undefined } | { requestId?: undefined; quotationId: string };
