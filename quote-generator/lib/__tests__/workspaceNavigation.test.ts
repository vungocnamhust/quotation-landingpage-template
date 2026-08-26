import assert from "node:assert/strict";
import test from "node:test";
import {
  shouldStartWorkspaceNavigation,
  workspaceRouteKey,
} from "../workspaceNavigation.ts";

const plainClick = {
  button: 0,
  defaultPrevented: false,
  metaKey: false,
  ctrlKey: false,
  shiftKey: false,
  altKey: false,
};

test("workspace navigation accepts a same-origin workspace route", () => {
  assert.equal(workspaceRouteKey("/workspace/quotations?view=table"), "/workspace/quotations?view=table");
  assert.equal(shouldStartWorkspaceNavigation(plainClick, "/workspace/quotations"), true);
});

test("workspace navigation rejects non-navigation clicks and routes", () => {
  assert.equal(shouldStartWorkspaceNavigation({ ...plainClick, metaKey: true }, "/workspace/quotations"), false);
  assert.equal(shouldStartWorkspaceNavigation({ ...plainClick, button: 1 }, "/workspace/quotations"), false);
  assert.equal(shouldStartWorkspaceNavigation({ ...plainClick, defaultPrevented: true }, "/workspace/quotations"), false);
  assert.equal(shouldStartWorkspaceNavigation({ ...plainClick, target: "_blank" }, "/workspace/quotations"), false);
  assert.equal(shouldStartWorkspaceNavigation({ ...plainClick, download: true }, "/workspace/quotations"), false);
  assert.equal(shouldStartWorkspaceNavigation(plainClick, "/?theme=brochure"), false);
  assert.equal(shouldStartWorkspaceNavigation(plainClick, "https://example.com/workspace"), false);
  assert.equal(workspaceRouteKey("#details"), null);
});
