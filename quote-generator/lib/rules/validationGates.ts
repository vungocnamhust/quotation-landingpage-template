/**
 * Pure Validation Gates for Quote Generator (TypeScript / Frontend).
 * Mirrors Backend Gatekeeper Pipeline to provide immediate UI feedback.
 */

import type { DayWithStayItem } from "../../components/quotation-workspace/DayEmbeddedRouteTable";
import type { QuotationFacts } from "../../components/quotation-workspace/factsTypes";

export type GateSeverity = "error" | "warning" | "info";

export type ClientGateIssue = {
  field: string;
  code: string;
  message: string;
  severity: GateSeverity;
  suggestion?: string;
};

export type ClientGateResult = {
  passed: boolean;
  issues: ClientGateIssue[];
  errors: ClientGateIssue[];
  warnings: ClientGateIssue[];
};

export function evaluateQuotationDraftReadiness(
  facts: QuotationFacts,
  dayWithStays: DayWithStayItem[]
): ClientGateResult {
  const issues: ClientGateIssue[] = [];

  // 1. Client / Party Gate
  const customerName = (facts.customer_facts.customer_name || "").trim();
  if (!customerName || customerName.length < 2) {
    issues.push({
      field: "customer_facts.customer_name",
      code: "NAME_REQUIRED",
      message: "Client / Family name is required (minimum 2 characters).",
      severity: "error",
    });
  }

  const adults = facts.customer_facts.adults ?? 0;
  if (adults < 1) {
    issues.push({
      field: "customer_facts.adults",
      code: "INVALID_ADULTS",
      message: "At least 1 adult is required.",
      severity: "error",
    });
  }

  const children = facts.customer_facts.children ?? 0;
  if (children > 0) {
    const kidAges = facts.customer_facts.kid_ages ?? [];
    if (kidAges.length !== children) {
      issues.push({
        field: "customer_facts.kid_ages",
        code: "KID_AGES_MISMATCH",
        message: `Please set ages for all ${children} children (current: ${kidAges.length}).`,
        severity: "warning",
        suggestion: "Child ages are used for bedding & room policy derivation.",
      });
    }
  }

  // 2. Dates Gate
  const start = facts.trip_facts.start_date;
  const end = facts.trip_facts.end_date;
  if (!start) {
    issues.push({
      field: "trip_facts.start_date",
      code: "START_DATE_REQUIRED",
      message: "Start date is required.",
      severity: "error",
    });
  }
  if (!end) {
    issues.push({
      field: "trip_facts.end_date",
      code: "END_DATE_REQUIRED",
      message: "End date is required.",
      severity: "error",
    });
  }
  if (start && end && end < start) {
    issues.push({
      field: "trip_facts.end_date",
      code: "INVALID_DATE_RANGE",
      message: "End date must be on or after start date.",
      severity: "error",
    });
  }

  // 3. Route Completeness Gate
  if (!dayWithStays || dayWithStays.length === 0) {
    issues.push({
      field: "trip_facts.itinerary",
      code: "EMPTY_ITINERARY",
      message: "Itinerary must contain at least 1 day.",
      severity: "error",
    });
  } else {
    const emptyDestDays: number[] = [];
    dayWithStays.forEach((d, i) => {
      if (!d.destination || !d.destination.trim()) {
        emptyDestDays.push(d.day_number ?? i + 1);
      }
    });
    if (emptyDestDays.length > 0) {
      issues.push({
        field: "trip_facts.itinerary.destination",
        code: "MISSING_DAY_DESTINATION",
        message: `Destination missing on Day: ${emptyDestDays.join(", ")}.`,
        severity: "error",
        suggestion: "Assign a destination for each day of the journey.",
      });
    }
  }

  // 4. Commercial Pricing Gate
  const opt = facts.pricing_facts.options[0];
  const perAdult = opt?.per_adult_amount_minor ?? opt?.per_traveler_amount_minor ?? 0;
  const total = opt?.group_total_amount_minor ?? 0;
  if (perAdult <= 0 && total <= 0) {
    issues.push({
      field: "pricing_facts.options",
      code: "PRICING_REQUIRED",
      message: "Please enter a Price per Adult or Group Total Price greater than 0.",
      severity: "error",
    });
  }

  // 5. Brand & Ownership Gate
  if (!facts.brand_id) {
    issues.push({
      field: "brand_id",
      code: "BRAND_REQUIRED",
      message: "Please select a publishing brand.",
      severity: "error",
    });
  }

  const errors = issues.filter((i) => i.severity === "error");
  const warnings = issues.filter((i) => i.severity === "warning");

  return {
    passed: errors.length === 0,
    issues,
    errors,
    warnings,
  };
}
