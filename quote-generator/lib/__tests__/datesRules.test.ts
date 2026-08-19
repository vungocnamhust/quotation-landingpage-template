import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  parseIsoDate,
  isValidIsoDate,
  addDaysToIsoDate,
  formatDisplayDate,
  calculateDuration,
  dateForItineraryDay,
  formatTravelDatesLabel,
  calculateValidityExpiry,
} from "../rules/datesRules.ts";

describe("datesRules domain pure functions", () => {
  describe("parseIsoDate", () => {
    it("parses valid ISO string to Date object", () => {
      const parsed = parseIsoDate("2026-10-15");
      assert.ok(parsed instanceof Date);
      assert.equal(parsed?.toISOString().split("T")[0], "2026-10-15");
    });

    it("returns null for invalid inputs", () => {
      assert.equal(parseIsoDate("invalid"), null);
      assert.equal(parseIsoDate(null), null);
    });
  });

  describe("isValidIsoDate", () => {
    it("validates standard ISO YYYY-MM-DD dates", () => {
      assert.equal(isValidIsoDate("2026-10-15"), true);
      assert.equal(isValidIsoDate("2026-02-28"), true);
    });

    it("rejects invalid dates or invalid formats", () => {
      assert.equal(isValidIsoDate("2026-02-31"), false);
      assert.equal(isValidIsoDate("15/10/2026"), false);
      assert.equal(isValidIsoDate(""), false);
      assert.equal(isValidIsoDate(null), false);
      assert.equal(isValidIsoDate(undefined), false);
    });
  });

  describe("addDaysToIsoDate", () => {
    it("adds days correctly crossing month boundaries", () => {
      assert.equal(addDaysToIsoDate("2026-10-30", 3), "2026-11-02");
      assert.equal(addDaysToIsoDate("2026-01-01", 0), "2026-01-01");
    });

    it("returns null for invalid input", () => {
      assert.equal(addDaysToIsoDate(null, 5), null);
    });
  });

  describe("formatDisplayDate", () => {
    it("formats ISO date to human readable string", () => {
      const formatted = formatDisplayDate("2026-11-09", "en");
      assert.equal(typeof formatted, "string");
      assert.ok(formatted.includes("Nov") || formatted.includes("09"));
    });

    it("returns empty string for null / empty input", () => {
      assert.equal(formatDisplayDate(null), "");
      assert.equal(formatDisplayDate(""), "");
    });
  });

  describe("calculateDuration", () => {
    it("calculates duration days and nights accurately", () => {
      const result = calculateDuration("2026-10-01", "2026-10-05");
      assert.equal(result.durationDays, 5);
      assert.equal(result.durationNights, 4);
    });

    it("returns nulls if start or end date is missing or invalid", () => {
      const result = calculateDuration("2026-10-05", "2026-10-01");
      assert.equal(result.durationDays, null);
      assert.equal(result.durationNights, null);
    });
  });

  describe("dateForItineraryDay", () => {
    it("projects date for specific day number", () => {
      assert.equal(dateForItineraryDay("2026-11-01", 1), "2026-11-01");
      assert.equal(dateForItineraryDay("2026-11-01", 3), "2026-11-03");
    });

    it("returns null if start date or day number is invalid", () => {
      assert.equal(dateForItineraryDay(null, 1), null);
      assert.equal(dateForItineraryDay("2026-11-01", 0), null);
    });
  });

  describe("calculateValidityExpiry", () => {
    it("calculates expiry date from reference date", () => {
      assert.equal(calculateValidityExpiry("2026-10-01", 14), "2026-10-15");
    });
  });

  describe("formatTravelDatesLabel", () => {
    it("formats range of dates", () => {
      const label = formatTravelDatesLabel("2026-10-01", "2026-10-05");
      assert.ok(label.includes("Oct"));
    });

    it("uses fallback text when dates are missing", () => {
      assert.equal(formatTravelDatesLabel(null, null, "Flexible Autumn 2026"), "Flexible Autumn 2026");
    });
  });
});
