import type { QuoteRequestItem } from "../components/quotation-workspace/factsTypes.ts";

export type RequestStatus = QuoteRequestItem["status"];
export const REQUEST_KANBAN_COLUMNS = [
  { id: "new", label: "New", ariaLabel: "New requests" },
  { id: "under_review", label: "Under Review", ariaLabel: "Requests under review" },
  { id: "quotation_created", label: "Quotation Created", ariaLabel: "Requests with quotation" },
  { id: "archived", label: "Archived", ariaLabel: "Archived requests" },
] as const;
export function canTransitionRequestStatus(from: RequestStatus, to: RequestStatus): boolean {
  return (from === "new" && (to === "under_review" || to === "archived")) || (from === "under_review" && (to === "quotation_created" || to === "archived")) || (from === "quotation_created" && to === "archived") || (from === "archived" && to === "under_review");
}
