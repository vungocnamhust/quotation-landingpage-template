import assert from "node:assert/strict";
import test from "node:test";
import { isQuotationStageLoading } from "../stageLoading.ts";

test("stage data loading begins only after the requested stage commits", () => {
  assert.equal(isQuotationStageLoading({ committedStage: "facts", requestedStage: "content", resourcesReady: true, hasLoadError: false }), false);
  assert.equal(isQuotationStageLoading({ committedStage: "content", requestedStage: "content", resourcesReady: true, hasLoadError: false }), false);
});

test("stage loading waits for required data but never masks an error", () => {
  assert.equal(isQuotationStageLoading({ committedStage: "design", requestedStage: "design", resourcesReady: false, hasLoadError: false }), true);
  assert.equal(isQuotationStageLoading({ committedStage: "design", requestedStage: "design", resourcesReady: false, hasLoadError: true }), false);
  assert.equal(isQuotationStageLoading({ committedStage: "facts", requestedStage: null, resourcesReady: false, hasLoadError: false }), false);
});
