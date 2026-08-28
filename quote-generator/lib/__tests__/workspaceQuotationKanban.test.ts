import assert from "node:assert/strict";
import test from "node:test";

import { formatCommercialTotal, normalizeWorkspaceQuotationView } from "../workspaceQuotationKanban.ts";

test("normalizes quotation views to a safe persisted mode", () => {
  assert.equal(normalizeWorkspaceQuotationView("kanban"), "kanban");
  assert.equal(normalizeWorkspaceQuotationView("table"), "table");
  assert.equal(normalizeWorkspaceQuotationView("unknown"), "grid");
  assert.equal(normalizeWorkspaceQuotationView(null), "grid");
});

test("formats commercial totals and keeps pending totals absent", () => {
  assert.equal(formatCommercialTotal({ currency: "VND", groupTotalAmountMinor: 2000000 }), "₫2,000,000");
  assert.equal(formatCommercialTotal({ currency: "USD", groupTotalAmountMinor: 123456 }), "$1,234.56");
  assert.equal(formatCommercialTotal({ currency: null, groupTotalAmountMinor: null }), null);
});
