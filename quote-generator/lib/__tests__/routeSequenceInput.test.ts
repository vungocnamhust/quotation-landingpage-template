import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
  isConsecutiveDuplicateDestination,
  collapseConsecutiveTokens,
  getDestinationChipKey,
  addDestinationWithGuard,
  pasteDestinationsWithGuard,
} from "../../components/destination/routeSequenceRules.ts";
import type { DestinationRef } from "../../components/destination/types.ts";

test("RouteSequenceInput: Consecutive adjacent duplicates are rejected and trigger the warning toast callback", () => {
  const toastCalls: Array<{ message: string; type?: string }> = [];
  const mockToast = (message: string, type?: string) => {
    toastCalls.push({ message, type });
  };

  const initialList: DestinationRef[] = [
    { id: "dst_ha_noi", name: "Hanoi", slug: "ha-noi" },
  ];

  // 1. Direct same-name addition
  const duplicateCandidate: DestinationRef = {
    id: "dst_ha_noi",
    name: "Hanoi",
    slug: "ha-noi",
  };

  // 0. Direct pure rule evaluation
  assert.equal(
    isConsecutiveDuplicateDestination(duplicateCandidate, initialList[0]),
    true,
    "Pure rule must detect exact duplicate"
  );
  assert.equal(
    isConsecutiveDuplicateDestination("Hanoi", "Hanoi"),
    true,
    "String token duplicate must be detected"
  );
  assert.equal(
    isConsecutiveDuplicateDestination("Da Nang", "Hanoi"),
    false,
    "Different destinations must not be flagged as duplicates"
  );
  assert.equal(
    isConsecutiveDuplicateDestination("Hanoi", null),
    false,
    "Null previous destination must evaluate to false"
  );



  const result1 = addDestinationWithGuard(duplicateCandidate, initialList, mockToast);
  assert.equal(result1.success, false, "Consecutive duplicate addition must be rejected");
  assert.equal(result1.nextList.length, 1, "List length must not change");
  assert.equal(toastCalls.length, 1, "Toast callback must be triggered once");
  assert.equal(toastCalls[0].type, "warning", "Toast type must be 'warning'");
  assert.match(
    toastCalls[0].message,
    /Cannot add consecutive duplicate destination "Hanoi"/,
    "Toast message must explain consecutive duplicate destination rejection"
  );

  // 2. Case-insensitive and whitespace-insensitive matching
  const mixedCaseCandidate: DestinationRef = {
    id: "dst_custom_hanoi",
    name: "  hAnOi  ",
    slug: "hanoi",
  };

  const result2 = addDestinationWithGuard(mixedCaseCandidate, initialList, mockToast);
  assert.equal(result2.success, false, "Case and whitespace variations must be rejected");
  assert.equal(result2.nextList.length, 1);
  assert.equal(toastCalls.length, 2);

  // 3. Slug / diacritic variation matching (e.g. 'Hà Nội' vs 'Hanoi')
  const diacriticCandidate: DestinationRef = {
    id: "dst_hanoivn",
    name: "Hà Nội",
    slug: "ha-noi",
  };

  const result3 = addDestinationWithGuard(diacriticCandidate, initialList, mockToast);
  assert.equal(result3.success, false, "Diacritic variation matching must be rejected");
  assert.equal(result3.nextList.length, 1);
  assert.equal(toastCalls.length, 3);
});

test("RouteSequenceInput: Non-consecutive duplicate destinations (round trips) are accepted and preserved", () => {
  const toastCalls: Array<{ message: string; type?: string }> = [];
  const mockToast = (message: string, type?: string) => {
    toastCalls.push({ message, type });
  };

  // Start with Hanoi -> Da Nang
  const currentList: DestinationRef[] = [
    { id: "dst_ha_noi", name: "Hanoi", slug: "ha-noi" },
    { id: "dst_da_nang", name: "Da Nang", slug: "da-nang" },
  ];

  // Add Hanoi again (legitimate round trip)
  const roundTripCandidate: DestinationRef = {
    id: "dst_ha_noi",
    name: "Hanoi",
    slug: "ha-noi",
  };

  const result = addDestinationWithGuard(roundTripCandidate, currentList, mockToast);
  assert.equal(result.success, true, "Round trip duplicate must be accepted");
  assert.equal(result.nextList.length, 3, "List must now have 3 destinations");
  assert.deepEqual(
    result.nextList.map((d) => d.name),
    ["Hanoi", "Da Nang", "Hanoi"],
    "Route sequence must be Hanoi -> Da Nang -> Hanoi"
  );
  assert.equal(toastCalls.length, 0, "No warning toast should fire for legitimate round trips");

  // Further add another leg: Hanoi -> Da Nang -> Hanoi -> Hue -> Hanoi
  const hueCandidate: DestinationRef = { id: "dst_hue", name: "Hue", slug: "hue" };
  const result2 = addDestinationWithGuard(hueCandidate, result.nextList, mockToast);
  assert.equal(result2.success, true);

  const finalReturn = addDestinationWithGuard(roundTripCandidate, result2.nextList, mockToast);
  assert.equal(finalReturn.success, true);
  assert.deepEqual(
    finalReturn.nextList.map((d) => d.name),
    ["Hanoi", "Da Nang", "Hanoi", "Hue", "Hanoi"]
  );
  assert.equal(toastCalls.length, 0);
});

test("RouteSequenceInput: Rendered keys are strictly unique across all chips even with repeated destinations", () => {
  // Simulate a round-trip route sharing identical ref.id values
  const roundTripItems: DestinationRef[] = [
    { id: "dst_ha_noi", name: "Hanoi", slug: "ha-noi" },
    { id: "dst_da_nang", name: "Da Nang", slug: "da-nang" },
    { id: "dst_ha_noi", name: "Hanoi", slug: "ha-noi" },
    { id: "dst_hue", name: "Hue", slug: "hue" },
    { id: "dst_ha_noi", name: "Hanoi", slug: "ha-noi" },
  ];

  const generatedKeys = roundTripItems.map((ref, index) =>
    getDestinationChipKey(ref, index)
  );

  assert.deepEqual(generatedKeys, [
    "dst_ha_noi-0",
    "dst_da_nang-1",
    "dst_ha_noi-2",
    "dst_hue-3",
    "dst_ha_noi-4",
  ]);

  const uniqueKeysSet = new Set(generatedKeys);
  assert.equal(
    uniqueKeysSet.size,
    roundTripItems.length,
    "Every rendered chip key must be strictly unique"
  );

  // Test with items having no id (fallback to slug or name)
  const itemsWithoutId: DestinationRef[] = [
    { id: "", name: "Hanoi", slug: "hanoi" },
    { id: "", name: "Saigon", slug: "saigon" },
    { id: "", name: "Hanoi", slug: "hanoi" },
  ];
  const fallbackKeys = itemsWithoutId.map((ref, index) =>
    getDestinationChipKey(ref, index)
  );
  assert.deepEqual(fallbackKeys, ["hanoi-0", "saigon-1", "hanoi-2"]);
  assert.equal(new Set(fallbackKeys).size, itemsWithoutId.length);

  // Static AST / source check on RouteSequenceInput.tsx: ensure legacy buggy key={ref.id || index} is gone
  const componentPath = resolve(
    import.meta.dirname,
    "../../components/destination/RouteSequenceInput.tsx"
  );
  const componentSource = readFileSync(componentPath, "utf-8");

  assert.doesNotMatch(
    componentSource,
    /key=\{ref\.id \|\| index\}/,
    "Buggy key={ref.id || index} must not exist in RouteSequenceInput.tsx"
  );
  assert.match(
    componentSource,
    /getDestinationChipKey\(ref,\s*index\)/,
    "RouteSequenceInput.tsx must use getDestinationChipKey(ref, index)"
  );
});

test("RouteSequenceInput: Paste parsing collapses consecutive adjacent duplicates while retaining non-consecutive duplicates", () => {
  const toastCalls: Array<{ message: string; type?: string }> = [];
  const mockToast = (message: string, type?: string) => {
    toastCalls.push({ message, type });
  };

  // 1. Raw pasted tokens containing multiple consecutive adjacent duplicates
  const rawTokens = [
    "Hanoi",
    "Hanoi",     // consecutive duplicate -> omit
    "Da Nang",
    "Da Nang",   // consecutive duplicate -> omit
    "Da Nang",   // consecutive duplicate -> omit
    "Hue",
    "Hanoi",     // non-consecutive duplicate (round trip) -> keep!
  ];

  const collapsed = collapseConsecutiveTokens(rawTokens);
  assert.deepEqual(
    collapsed.retainedTokens,
    ["Hanoi", "Da Nang", "Hue", "Hanoi"],
    "Adjacent duplicates must be stripped while non-consecutive round-trip stop is retained"
  );
  assert.equal(collapsed.omittedCount, 3, "Exactly 3 duplicates should be omitted");

  // 2. Integration paste with pasteDestinationsWithGuard on existing list
  const existingList: DestinationRef[] = [
    { id: "dst_ha_noi", name: "Hanoi", slug: "ha-noi" },
  ];

  // User pastes: "Hanoi -> Da Nang -> Hue -> Hue -> Hanoi"
  // Note: first token "Hanoi" matches existingList's last stop "Hanoi", so it must be omitted as consecutive duplicate
  const pasteString = "Hanoi -> Da Nang -> Hue -> Hue -> Hanoi";
  const pasteResult = pasteDestinationsWithGuard(pasteString, existingList, mockToast);

  assert.equal(pasteResult.success, true);
  assert.equal(pasteResult.omittedCount, 2, "First Hanoi and second Hue should be omitted");
  assert.deepEqual(
    pasteResult.nextList.map((d) => d.name),
    ["Hanoi", "Da Nang", "Hue", "Hanoi"],
    "Final list must be Hanoi (existing) -> Da Nang -> Hue -> Hanoi"
  );
  assert.equal(toastCalls.length, 1);
  assert.equal(toastCalls[0].type, "warning");
  assert.match(toastCalls[0].message, /omitted/i);

  // 3. Paste with pure round trips (no adjacent duplicates)
  toastCalls.length = 0;
  const cleanRoundTrip = "Hanoi -> Hue -> Hanoi";
  const cleanResult = pasteDestinationsWithGuard(cleanRoundTrip, [], mockToast);
  assert.equal(cleanResult.success, true);
  assert.equal(cleanResult.omittedCount, 0);
  assert.deepEqual(cleanResult.nextList.map((d) => d.name), ["Hanoi", "Hue", "Hanoi"]);
  assert.equal(toastCalls.length, 0, "No toast when no duplicates are omitted");
});
