import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import test from "node:test";

const workspaceRoot = resolve(import.meta.dirname, "../..");
const navigationSurfaces = [
  "app/workspace/page.tsx",
  "app/workspace/quotations/page.tsx",
  "app/workspace/requests/new/page.tsx",
  "components/staff-workspace/WorkspaceShell.tsx",
  "components/staff-workspace/WorkspaceQuotationOverview.tsx",
  "components/staff-workspace/WorkspaceQuotationTable.tsx",
  "components/staff-workspace/WorkspaceQuotationCard.tsx",
  "components/staff-workspace/WorkspaceRequestTable.tsx",
  "components/staff-workspace/WorkspaceRequestCard.tsx",
  "components/staff-workspace/DetailRequestView.tsx",
  "components/staff-workspace/NotificationCenterDrawer.tsx",
  "components/staff-workspace/useNotifications.ts",
  "components/quotation-workspace/NewQuotationClient.tsx",
  "components/quotation-workspace/QuotationWorkspaceClient.tsx",
];

test("staff workspace navigation surfaces use the shared loading contract", () => {
  for (const relativePath of navigationSurfaces) {
    const source = readFileSync(resolve(workspaceRoot, relativePath), "utf8");
    assert.doesNotMatch(source, /from ["']next\/link["']/);
    assert.doesNotMatch(source, /\brouter\.push\(/);
  }
});
