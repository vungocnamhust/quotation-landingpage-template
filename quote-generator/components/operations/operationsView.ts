import type { ViewModeOption } from "../ui/data-view/DataViewToggle.tsx";
import type { BookingBoardItem, BookingLineStatus, BookingLineUrgency } from "./types.ts";

export type OperationsViewMode = ViewModeOption;

export const OPERATIONS_URGENCY_GROUPS = ["overdue", "due_soon", "upcoming", "done"] as const;
export type OperationsUrgencyGroup = (typeof OPERATIONS_URGENCY_GROUPS)[number];

export const OPERATIONS_URGENCY_LABEL: Record<OperationsUrgencyGroup, string> = {
  overdue: "Overdue",
  due_soon: "This week / Due Soon",
  upcoming: "Upcoming",
  done: "Done / Delivered",
};

const STATUS_LABEL: Record<BookingLineStatus, string> = {
  to_request: "To request",
  requested: "Requested",
  confirmed: "Confirmed",
  delivered: "Delivered",
  cancelled: "Cancelled",
};

const URGENCY_LABEL: Record<BookingLineUrgency | "none", string> = {
  overdue: "Overdue",
  due_soon: "Due soon",
  ok: "On track",
  none: "No deadline",
};

const NEXT_STATUS: Record<BookingLineStatus, Exclude<BookingLineStatus, "to_request" | "cancelled"> | null> = {
  to_request: "requested",
  requested: "confirmed",
  confirmed: "delivered",
  delivered: null,
  cancelled: null,
};

export function normalizeOperationsView(value: string | null): OperationsViewMode {
  return value === "grid" || value === "table" || value === "kanban" ? value : "kanban";
}

export function urgencyGroupOf(item: BookingBoardItem): OperationsUrgencyGroup {
  if (item.line.status === "delivered" || item.line.status === "cancelled") return "done";
  if (item.line.urgency === "overdue") return "overdue";
  if (item.line.urgency === "due_soon") return "due_soon";
  return "upcoming";
}

export function getStatusLabel(status: BookingLineStatus): string {
  return STATUS_LABEL[status];
}

export function getUrgencyLabel(urgency: BookingLineUrgency | null): string {
  return URGENCY_LABEL[urgency ?? "none"];
}

export function getNextStatus(status: BookingLineStatus): Exclude<BookingLineStatus, "to_request" | "cancelled"> | null {
  return NEXT_STATUS[status];
}

export function formatOperationDate(value: string | null): string {
  if (!value) return "—";
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

export function matchesOperationsSearch(item: BookingBoardItem, query: string): boolean {
  if (!query.trim()) return true;
  const haystack = [
    item.booking_code,
    item.party_label_snapshot ?? "",
    item.line.title_snapshot,
    item.line.supplier_name_snapshot ?? "",
    item.line.voucher_ref ?? "",
  ].join(" ").toLowerCase();
  return haystack.includes(query.trim().toLowerCase());
}
