import type { BookingBoardItem, BookingBoardResponse, BookingDetailResponse, BookingLineStatus } from "./types.ts";

function mergeBookingDetail(items: BookingBoardItem[], detail: BookingDetailResponse): BookingBoardItem[] {
  const lineById = new Map(detail.lines.map((line) => [line.id, line]));
  const warningLineIds = new Set(detail.cash_flow_warnings);

  return items.map((item) => {
    if (item.booking_id !== detail.booking.id) return item;
    const line = lineById.get(item.line.id);
    if (!line) return item;
    return {
      ...item,
      line,
      booking_code: detail.booking.booking_code,
      booking_revision: detail.booking.booking_revision,
      quotation_id: detail.booking.quotation_id,
      party_label_snapshot: detail.booking.party_label_snapshot,
      travel_start_date: detail.booking.travel_start_date,
      travel_end_date: detail.booking.travel_end_date,
      customer_balance_due_date: detail.booking.customer_balance_due_date,
      cash_flow_warning: warningLineIds.has(line.id),
    };
  });
}

export function mergeBookingDetailIntoBoard(
  board: BookingBoardResponse | undefined,
  detail: BookingDetailResponse,
): BookingBoardResponse | undefined {
  if (!board) return board;
  return { ...board, items: mergeBookingDetail(board.items, detail) };
}

export function optimisticallyTransitionBoardLine(
  board: BookingBoardResponse | undefined,
  bookingId: string,
  lineId: string,
  to: BookingLineStatus,
): BookingBoardResponse | undefined {
  if (!board) return board;
  return {
    ...board,
    items: board.items.map((item) =>
      item.booking_id === bookingId && item.line.id === lineId
        ? { ...item, line: { ...item.line, status: to } }
        : item,
    ),
  };
}

export function optimisticallyCancelBooking(
  board: BookingBoardResponse | undefined,
  bookingId: string,
): BookingBoardResponse | undefined {
  if (!board) return board;
  return {
    ...board,
    items: board.items.map((item) =>
      item.booking_id === bookingId && item.line.status !== "delivered" && item.line.status !== "cancelled"
        ? { ...item, line: { ...item.line, status: "cancelled" } }
        : item,
    ),
  };
}
