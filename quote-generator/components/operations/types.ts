export type {
  BookingBoardItem,
  BookingBoardResponse,
  BookingDetailResponse,
  BookingHeaderStatus,
  BookingLineProfile,
  BookingLineStatus,
  BookingLineUrgency,
  BookingProfile,
  CancellationPolicyProfile,
  PaymentTermsProfile,
  SupplierContactProfile,
} from "../../lib/quotationApi.ts";

export const URGENCY_GROUPS = ["overdue", "due_soon", "upcoming", "done"] as const;
export type UrgencyGroup = (typeof URGENCY_GROUPS)[number];

export const URGENCY_GROUP_LABEL: Record<UrgencyGroup, string> = {
  overdue: "Overdue",
  due_soon: "This week",
  upcoming: "Upcoming",
  done: "Done",
};
