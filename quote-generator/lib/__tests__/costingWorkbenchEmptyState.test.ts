import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { QuotationApiError } from "../apiError.ts";
import {
  extractSheetIdFromConflict,
  executeCreateSheetLifecycle,
} from "../../components/quotation-costing/useCostingWorkspace.ts";
import type { CostingWorkbenchResponse } from "../../components/quotation-costing/types.ts";

function createMockWorkbench(sheetId: string, requestId: string | null = "req_test"): CostingWorkbenchResponse {
  return {
    sheet: {
      id: sheetId,
      quote_request_id: requestId,
      quotation_id: requestId ? null : "q_test",
      currency: "USD",
      costing_revision: 1,
      markup_rate_bps: 1500,
      rounding_increment_minor: 1000,
      created_at: "2026-09-04T00:00:00Z",
      updated_at: "2026-09-04T00:00:00Z",
    },
    items: [],
    summary: {
      total_cost_minor: 0,
      total_sell_minor: 0,
      margin_minor: 0,
      margin_rate_bps: 0,
    },
    applications: [],
    drift: { has_drift: false, reasons: [] },
  };
}

describe("extractSheetIdFromConflict", () => {
  it("extracts sheet ID from request conflict error message", () => {
    const error = new QuotationApiError(
      "conflict",
      409,
      "quote_request 'req_123' already has an open costing sheet 'cs_req_409'.",
      { message: "quote_request 'req_123' already has an open costing sheet 'cs_req_409'." },
    );
    assert.equal(extractSheetIdFromConflict(error), "cs_req_409");
  });

  it("extracts sheet ID from quotation conflict error message", () => {
    const error = new QuotationApiError(
      "conflict",
      409,
      "quotation 'q_123' already has a costing sheet 'cs_quotation_409'.",
    );
    assert.equal(extractSheetIdFromConflict(error), "cs_quotation_409");
  });

  it("extracts sheet ID from structured detail payload when message is generic", () => {
    const error = new QuotationApiError(
      "conflict",
      409,
      "Conflict occurred.",
      { message: "quote_request 'req_456' already has an open costing sheet 'cs_detail_789'." },
    );
    assert.equal(extractSheetIdFromConflict(error), "cs_detail_789");
  });

  it("extracts sheet ID from plain object with double quotes", () => {
    const error = {
      status: 409,
      message: 'quote_request "req_abc" already has an open costing sheet "cs_quoted_123".',
    };
    assert.equal(extractSheetIdFromConflict(error), "cs_quoted_123");
  });

  it("returns null for non-conflict or unrelated errors", () => {
    assert.equal(extractSheetIdFromConflict(new Error("Network timeout")), null);
    assert.equal(
      extractSheetIdFromConflict(new QuotationApiError("validation", 422, "Invalid currency")),
      null,
    );
    assert.equal(extractSheetIdFromConflict(null), null);
    assert.equal(extractSheetIdFromConflict(undefined), null);
  });
});

describe("executeCreateSheetLifecycle", () => {
  it("manages loading state and notifies success on normal creation", async () => {
    const loadingStates: boolean[] = [];
    const errorStates: Array<string | null> = [];
    const toastCalls: Array<{ message: string; type: string }> = [];
    let successResult: CostingWorkbenchResponse | null = null;

    const mockWorkbench = createMockWorkbench("cs_new_1");

    const result = await executeCreateSheetLifecycle({
      anchor: { requestId: "req_1" },
      currency: "USD",
      createSheetFn: async () => ({ id: "cs_new_1" }),
      findSheetByRequestFn: async () => null,
      findSheetByQuotationFn: async () => null,
      getWorkbenchFn: async (id) => {
        assert.equal(id, "cs_new_1");
        return mockWorkbench;
      },
      onLoadingChange: (loading) => loadingStates.push(loading),
      onErrorChange: (err) => errorStates.push(err),
      onSuccess: (res) => {
        successResult = res;
      },
      notifyToast: (message, type) => toastCalls.push({ message, type }),
    });

    // Loading transition: starts true, ends false
    assert.deepEqual(loadingStates, [true, false]);
    // Error is reset to null initially and stays null
    assert.deepEqual(errorStates, [null]);
    // Success result applied
    assert.equal(result, mockWorkbench);
    assert.equal(successResult, mockWorkbench);
    // Success toast fired
    assert.equal(toastCalls.length, 1);
    assert.equal(toastCalls[0].type, "success");
    assert.match(toastCalls[0].message, /created successfully/i);
  });

  it("exposes actionError and triggers error toast when sheet creation fails", async () => {
    const loadingStates: boolean[] = [];
    const errorStates: Array<string | null> = [];
    const toastCalls: Array<{ message: string; type: string }> = [];
    let successCalled = false;

    const result = await executeCreateSheetLifecycle({
      anchor: { requestId: "req_fail" },
      createSheetFn: async () => {
        throw new QuotationApiError("validation", 422, "Invalid costing sheet parameters.");
      },
      findSheetByRequestFn: async () => null,
      findSheetByQuotationFn: async () => null,
      getWorkbenchFn: async () => createMockWorkbench("never_called"),
      onLoadingChange: (loading) => loadingStates.push(loading),
      onErrorChange: (err) => errorStates.push(err),
      onSuccess: () => {
        successCalled = true;
      },
      notifyToast: (message, type) => toastCalls.push({ message, type }),
    });

    // Returns null on failure
    assert.equal(result, null);
    assert.equal(successCalled, false);
    // Loading ends with false
    assert.deepEqual(loadingStates, [true, false]);
    // Error was cleared initially, then set to API error message
    assert.deepEqual(errorStates, [null, "Invalid costing sheet parameters."]);
    // Error toast fired
    assert.equal(toastCalls.length, 1);
    assert.equal(toastCalls[0].type, "error");
    assert.equal(toastCalls[0].message, "Invalid costing sheet parameters.");
  });

  it("auto-recovers from 409 conflict by extracting sheet ID from error message", async () => {
    const loadingStates: boolean[] = [];
    const errorStates: Array<string | null> = [];
    const toastCalls: Array<{ message: string; type: string }> = [];
    let successResult: CostingWorkbenchResponse | null = null;

    const recoveredWorkbench = createMockWorkbench("cs_recovered_409");

    const result = await executeCreateSheetLifecycle({
      anchor: { requestId: "req_conflict_1" },
      createSheetFn: async () => {
        throw new QuotationApiError(
          "conflict",
          409,
          "quote_request 'req_conflict_1' already has an open costing sheet 'cs_recovered_409'.",
        );
      },
      findSheetByRequestFn: async () => {
        assert.fail("findSheetByRequestFn should not be called when ID is parsed from message");
      },
      findSheetByQuotationFn: async () => null,
      getWorkbenchFn: async (id) => {
        assert.equal(id, "cs_recovered_409");
        return recoveredWorkbench;
      },
      onLoadingChange: (loading) => loadingStates.push(loading),
      onErrorChange: (err) => errorStates.push(err),
      onSuccess: (res) => {
        successResult = res;
      },
      notifyToast: (message, type) => toastCalls.push({ message, type }),
    });

    // Successfully transitioned to the recovered sheet
    assert.equal(result, recoveredWorkbench);
    assert.equal(successResult, recoveredWorkbench);
    assert.deepEqual(loadingStates, [true, false]);
    // Error was only reset to null at start, not populated with conflict error
    assert.deepEqual(errorStates, [null]);
    // Info toast notified user of existing sheet recovery
    assert.equal(toastCalls.length, 1);
    assert.equal(toastCalls[0].type, "info");
    assert.match(toastCalls[0].message, /already exists/i);
  });

  it("auto-recovers from 409 conflict via findSheetByRequest fallback when message lacks ID", async () => {
    const loadingStates: boolean[] = [];
    const errorStates: Array<string | null> = [];
    const toastCalls: Array<{ message: string; type: string }> = [];
    let successResult: CostingWorkbenchResponse | null = null;
    let findByRequestCalled = false;

    const fallbackWorkbench = createMockWorkbench("cs_via_find_query");

    const result = await executeCreateSheetLifecycle({
      anchor: { requestId: "req_conflict_find" },
      createSheetFn: async () => {
        throw new QuotationApiError("conflict", 409, "Slot already taken.");
      },
      findSheetByRequestFn: async (reqId) => {
        assert.equal(reqId, "req_conflict_find");
        findByRequestCalled = true;
        return { id: "cs_via_find_query" };
      },
      findSheetByQuotationFn: async () => null,
      getWorkbenchFn: async (id) => {
        assert.equal(id, "cs_via_find_query");
        return fallbackWorkbench;
      },
      onLoadingChange: (loading) => loadingStates.push(loading),
      onErrorChange: (err) => errorStates.push(err),
      onSuccess: (res) => {
        successResult = res;
      },
      notifyToast: (message, type) => toastCalls.push({ message, type }),
    });

    assert.equal(findByRequestCalled, true);
    assert.equal(result, fallbackWorkbench);
    assert.equal(successResult, fallbackWorkbench);
    assert.deepEqual(loadingStates, [true, false]);
    assert.deepEqual(errorStates, [null]);
    assert.equal(toastCalls.length, 1);
    assert.equal(toastCalls[0].type, "info");
  });

  it("auto-recovers from 409 conflict for quotation-anchored sheets", async () => {
    const toastCalls: Array<{ message: string; type: string }> = [];
    let successResult: CostingWorkbenchResponse | null = null;

    const quotationWorkbench = createMockWorkbench("cs_quotation_sheet", null);

    const result = await executeCreateSheetLifecycle({
      anchor: { quotationId: "q_409" },
      createSheetFn: async () => {
        throw new QuotationApiError(
          "conflict",
          409,
          "quotation 'q_409' already has a costing sheet 'cs_quotation_sheet'.",
        );
      },
      findSheetByRequestFn: async () => null,
      findSheetByQuotationFn: async () => null,
      getWorkbenchFn: async (id) => {
        assert.equal(id, "cs_quotation_sheet");
        return quotationWorkbench;
      },
      onLoadingChange: () => {},
      onErrorChange: () => {},
      onSuccess: (res) => {
        successResult = res;
      },
      notifyToast: (message, type) => toastCalls.push({ message, type }),
    });

    assert.equal(result, quotationWorkbench);
    assert.equal(successResult, quotationWorkbench);
    assert.equal(toastCalls.length, 1);
    assert.equal(toastCalls[0].type, "info");
  });

  it("exposes conflict error if 409 recovery cannot find any active sheet", async () => {
    const errorStates: Array<string | null> = [];
    const toastCalls: Array<{ message: string; type: string }> = [];
    let successCalled = false;

    const result = await executeCreateSheetLifecycle({
      anchor: { requestId: "req_irrecoverable" },
      createSheetFn: async () => {
        throw new QuotationApiError("conflict", 409, "Unspecified conflict without sheet ID.");
      },
      findSheetByRequestFn: async () => null,
      findSheetByQuotationFn: async () => null,
      getWorkbenchFn: async () => createMockWorkbench("never"),
      onLoadingChange: () => {},
      onErrorChange: (err) => errorStates.push(err),
      onSuccess: () => {
        successCalled = true;
      },
      notifyToast: (message, type) => toastCalls.push({ message, type }),
    });

    assert.equal(result, null);
    assert.equal(successCalled, false);
    assert.equal(errorStates.length, 2);
    assert.equal(errorStates[0], null);
    assert.match(errorStates[1] ?? "", /conflict|session|retrying/i);
    assert.equal(toastCalls.length, 1);
    assert.equal(toastCalls[0].type, "error");
  });
});
