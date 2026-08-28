import assert from "node:assert/strict";
import test from "node:test";

import { mergeBookingDetailIntoBoard, optimisticallyCancelBooking, optimisticallyTransitionBoardLine } from "../../components/operations/operationsBoardCache.ts";
import { getNextStatus, normalizeOperationsView, urgencyGroupOf } from "../../components/operations/operationsView.ts";
import type { BookingBoardItem, BookingDetailResponse } from "../../components/operations/types.ts";

function item(overrides: Partial<BookingBoardItem["line"]> = {}): BookingBoardItem {
  return {
    booking_id: "booking-1",
    booking_code: "BK-001",
    booking_revision: 4,
    quotation_id: "quotation-1",
    party_label_snapshot: "The Nguyen family",
    travel_start_date: "2026-09-10",
    travel_end_date: "2026-09-14",
    customer_balance_due_date: "2026-09-01",
    cash_flow_warning: false,
    line: {
      id: "line-1",
      booking_id: "booking-1",
      source_service_line_id: "service-1",
      supplier_id_snapshot: "supplier-1",
      supplier_name_snapshot: "Lotus Travel",
      supplier_contact_snapshot_json: null,
      title_snapshot: "Halong Bay cruise",
      category: "cruise",
      service_date: "2026-09-12",
      unit: "trip",
      time_basis: "day",
      qty_unit: 1,
      qty_time: 1,
      unit_cost_minor_snapshot: 100,
      cost_currency_snapshot: "USD",
      fx_rate_ppm_snapshot: null,
      sell_minor_snapshot: 120,
      payment_terms_snapshot_json: null,
      cancellation_policy_snapshot_json: null,
      status: "to_request",
      request_by_date: "2026-09-01",
      penalty_free_until: null,
      deposit_due_date: null,
      balance_due_date: "2026-08-31",
      supplier_ref: null,
      voucher_ref: null,
      confirmed_at: null,
      cancelled_at: null,
      cancel_reason: null,
      cancel_penalty_minor: null,
      assignee_email: null,
      notes: null,
      sort_order: 1,
      created_at: "2026-08-01T00:00:00Z",
      updated_at: "2026-08-01T00:00:00Z",
      urgency: "due_soon",
      ...overrides,
    },
  };
}

test("normalizes Operations URLs to the Kanban default", () => {
  assert.equal(normalizeOperationsView(null), "kanban");
  assert.equal(normalizeOperationsView("grid"), "grid");
  assert.equal(normalizeOperationsView("table"), "table");
  assert.equal(normalizeOperationsView("invalid"), "kanban");
});

test("uses server-provided urgency while terminal lines always enter the done lane", () => {
  assert.equal(urgencyGroupOf(item({ urgency: "overdue" })), "overdue");
  assert.equal(urgencyGroupOf(item({ urgency: "due_soon" })), "due_soon");
  assert.equal(urgencyGroupOf(item({ urgency: "ok" })), "upcoming");
  assert.equal(urgencyGroupOf(item({ status: "delivered", urgency: "overdue" })), "done");
});

test("only exposes valid next lifecycle transitions", () => {
  assert.equal(getNextStatus("to_request"), "requested");
  assert.equal(getNextStatus("requested"), "confirmed");
  assert.equal(getNextStatus("confirmed"), "delivered");
  assert.equal(getNextStatus("delivered"), null);
  assert.equal(getNextStatus("cancelled"), null);
});

test("optimistic cache projections retain server deadline values and merge the authoritative response", () => {
  const current = { items: [item()] };
  const transitioned = optimisticallyTransitionBoardLine(current, "booking-1", "line-1", "requested");
  assert.equal(transitioned?.items[0].line.status, "requested");
  assert.equal(transitioned?.items[0].line.urgency, "due_soon");

  const cancelled = optimisticallyCancelBooking(current, "booking-1");
  assert.equal(cancelled?.items[0].line.status, "cancelled");

  const detail: BookingDetailResponse = {
    booking: { ...current.items[0], id: "booking-1", sheet_id: "sheet-1", status: "active", deposit_received_at: "2026-08-01", notes: null, created_at: "2026-08-01T00:00:00Z", updated_at: "2026-08-02T00:00:00Z" },
    lines: [{ ...current.items[0].line, status: "confirmed", voucher_ref: "VCH-1", urgency: "ok" }],
    cash_flow_warnings: ["line-1"],
  };
  const merged = mergeBookingDetailIntoBoard(current, detail);
  assert.equal(merged?.items[0].booking_revision, 4);
  assert.equal(merged?.items[0].line.status, "confirmed");
  assert.equal(merged?.items[0].line.voucher_ref, "VCH-1");
  assert.equal(merged?.items[0].cash_flow_warning, true);
});
