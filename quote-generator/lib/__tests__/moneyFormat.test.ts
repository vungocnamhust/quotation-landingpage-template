import test from "node:test";
import assert from "node:assert/strict";

import { formatMinorAmount } from "../moneyFormat.ts";

test("VND minor units are majors already — never divided by 100 (Plan 16.3 F-09)", () => {
  assert.equal(formatMinorAmount(50_000_000, "VND"), `${(50_000_000).toLocaleString(undefined, { maximumFractionDigits: 0 })} VND`);
});

test("two-decimal currencies divide minor units by 100", () => {
  assert.equal(formatMinorAmount(123_456, "USD"), `${(1234.56).toLocaleString(undefined, { maximumFractionDigits: 2 })} USD`);
});

test("zero amounts format for both divisor families", () => {
  assert.equal(formatMinorAmount(0, "VND"), "0 VND");
  assert.equal(formatMinorAmount(0, "EUR"), "0 EUR");
});
