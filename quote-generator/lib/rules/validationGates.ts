/**
 * Pure Validation Gates for Quote Generator (TypeScript / Frontend).
 * Mirrors Backend Gatekeeper Pipeline to provide immediate UI feedback.
 */

import type { DayWithStayItem } from "../../components/quotation-workspace/DayEmbeddedRouteTable.tsx";
import type { QuotationFacts } from "../../components/quotation-workspace/factsTypes.ts";

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

export function evaluateQuoteRequestReadiness(
  formState: {
    role?: string;
    first_name?: string;
    last_name?: string;
    client_name?: string;
    advisor_first_name?: string;
    advisor_last_name?: string;
    advisor_company?: string;
    email?: string;
    advisor_email?: string;
    travel_timing?: string;
    arrival_date?: string;
    departure_date?: string;
    adults?: number;
    destination?: string;
    destinations?: string[];
  },
  itineraryDays?: Array<{ destination?: string; day_number?: number }>
): ClientGateResult {
  const issues: ClientGateIssue[] = [];
  const isAdvisor = formState.role === "advisor";

  // 1. Identity Gate
  if (isAdvisor) {
    const clientName = (formState.client_name || "").trim();
    const advisorName = (formState.advisor_first_name || formState.advisor_last_name || "").trim();
    if (!clientName && !advisorName) {
      issues.push({
        field: "client_name",
        code: "CLIENT_OR_ADVISOR_NAME_REQUIRED",
        message: "End-client name or Advisor name is required.",
        severity: "error",
        suggestion: "Please enter the traveller's family name or lead name.",
      });
    }

    const email = (formState.advisor_email || formState.email || "").trim();
    if (!email) {
      issues.push({
        field: "advisor_email",
        code: "ADVISOR_EMAIL_REQUIRED",
        message: "Advisor email address is required.",
        severity: "error",
      });
    }
  } else {
    const fullName = `${formState.first_name || ""} ${formState.last_name || ""}`.trim() || (formState.client_name || "").trim();
    if (!fullName || fullName.length < 2) {
      issues.push({
        field: "first_name",
        code: "TRAVELLER_NAME_REQUIRED",
        message: "Traveller name is required (minimum 2 characters).",
        severity: "error",
        suggestion: "Please provide the lead traveller's first and last name.",
      });
    }

    const email = (formState.email || "").trim();
    if (!email) {
      issues.push({
        field: "email",
        code: "EMAIL_RECOMMENDED",
        message: "Contact email is recommended for follow-up notifications.",
        severity: "warning",
      });
    }
  }

  // 2. Party Size Gate
  const adults = formState.adults ?? 1;
  if (adults < 1) {
    issues.push({
      field: "adults",
      code: "INVALID_ADULTS",
      message: "At least 1 adult traveller is required.",
      severity: "error",
    });
  }

  // 3. Travel Dates Gate
  const arrival = formState.arrival_date;
  const departure = formState.departure_date;
  if (arrival && departure && departure < arrival) {
    issues.push({
      field: "departure_date",
      code: "INVALID_DATE_RANGE",
      message: "Departure date must be on or after arrival date.",
      severity: "error",
    });
  }

  // 4. Destinations Gate
  const hasDest = Boolean(
    (formState.destination && formState.destination.trim()) ||
    (formState.destinations && formState.destinations.length > 0) ||
    (itineraryDays && itineraryDays.some((d) => d.destination && d.destination.trim()))
  );

  if (!hasDest) {
    issues.push({
      field: "destination",
      code: "DESTINATION_RECOMMENDED",
      message: "Specifying at least one destination helps generate an accurate quote.",
      severity: "warning",
      suggestion: "Add a destination or route sequence to the itinerary.",
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
