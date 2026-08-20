import test from "node:test";
import assert from "node:assert/strict";
import {
  parseRouteTokens,
  formatRouteString,
  deriveRouteFromItinerary,
} from "../rules/routeRules.ts";
import { tripReconciler } from "../rules/tripReconciler.ts";
import { tripAdapter } from "../rules/tripAdapter.ts";
import type { CanonicalTrip } from "../rules/tripReconciler.ts";
import type { QuoteRequestFormState } from "../quoteRequestPayload.ts";

test("parseRouteTokens tokenizes multiple delimiter styles", () => {
  // Arrow delimiter
  assert.deepEqual(
    parseRouteTokens("Ho Chi Minh -> Mekong Delta -> Da Nang -> Hanoi"),
    ["Ho Chi Minh", "Mekong Delta", "Da Nang", "Hanoi"]
  );

  // Dash & hyphen delimiter
  assert.deepEqual(
    parseRouteTokens("Hanoi – Ninh Binh — Halong Bay - Hue"),
    ["Hanoi", "Ninh Binh", "Halong Bay", "Hue"]
  );

  // Comma, Ampersand & Newline delimiter
  assert.deepEqual(
    parseRouteTokens("Hanoi, Halong Bay & Hue\nHoi An\tSaigon"),
    ["Hanoi", "Halong Bay", "Hue", "Hoi An", "Saigon"]
  );

  // Empty string or null
  assert.deepEqual(parseRouteTokens(""), []);
  assert.deepEqual(parseRouteTokens(null), []);
});

test("formatRouteString formats clean standardized route text", () => {
  assert.equal(
    formatRouteString(["Hanoi", "Halong Bay", "Hue", "Hoi An"]),
    "Hanoi – Halong Bay – Hue – Hoi An"
  );

  // Object ref items with duplicates
  assert.equal(
    formatRouteString([
      { id: "1", name: "Hanoi", slug: "hanoi" },
      { id: "2", name: "Hanoi", slug: "hanoi" },
      { id: "3", name: "Hue", slug: "hue" },
    ]),
    "Hanoi – Hue"
  );
});

test("deriveRouteFromItinerary extracts arrival, departure and unique destinations in order", () => {
  const itinerary = [
    { day_number: 1, destination: "Ho Chi Minh City", overnight: "Ho Chi Minh City", display_date: null, summary: null },
    { day_number: 2, destination: "Mekong Delta", overnight: "Can Tho", display_date: null, summary: null },
    { day_number: 3, destination: "Da Nang", overnight: "Da Nang", display_date: null, summary: null },
    { day_number: 4, destination: "Hanoi", overnight: "Hanoi", display_date: null, summary: null },
  ];

  const meta = deriveRouteFromItinerary(itinerary);
  assert.equal(meta.arrivalCity, "Ho Chi Minh City");
  assert.equal(meta.departureCity, "Hanoi");
  assert.deepEqual(meta.destinations, ["Ho Chi Minh City", "Mekong Delta", "Da Nang", "Hanoi"]);
  assert.equal(meta.displayRouteText, "Ho Chi Minh City – Mekong Delta – Da Nang – Hanoi");
});

test("tripReconciler.applyRouteSequence expands itinerary and sets dates", () => {
  const initialTrip: CanonicalTrip = {
    startDate: "2026-11-01",
    endDate: null,
    durationDays: null,
    durationNights: null,
    itinerary: [],
    lang: "en",
  };

  const updated = tripReconciler.applyRouteSequence(initialTrip, [
    "Ho Chi Minh City",
    "Mekong Delta",
    "Da Nang",
    "Hanoi",
  ]);

  assert.equal(updated.itinerary.length, 4);
  assert.equal(updated.startDate, "2026-11-01");
  assert.equal(updated.endDate, "2026-11-04");
  assert.equal(updated.durationDays, 4);
  assert.equal(updated.durationNights, 3);
  assert.equal(updated.arrivalCity, "Ho Chi Minh City");
  assert.equal(updated.departureCity, "Hanoi");
  assert.deepEqual(updated.destinations, ["Ho Chi Minh City", "Mekong Delta", "Da Nang", "Hanoi"]);
  assert.equal(updated.displayRouteText, "Ho Chi Minh City – Mekong Delta – Da Nang – Hanoi");
});

test("tripAdapter bidirectional sync preserves route metadata", () => {
  const formState: QuoteRequestFormState = {
    role: "traveller",
    customer_name: "John Doe",
    email: "john@example.com",
    phone: "",
    market: "UK",
    preferred_contact: "email",
    destination: "Vietnam",
    destinations: ["Vietnam"],
    destination_refs: [],
    arrival_city: "Hanoi",
    departure_city: "Saigon",
    routing_constraints: "Fixed flight VN50 arriving 06:30",
    arrival_date: "2026-10-10",
    departure_date: "2026-10-12",
    raw_dates_text: "",
    date_flexibility: "exact",
    adults: 2,
    children: 0,
    children_details: "",
    kid_ages: [],
    travel_style: "Living Heritage",
    special_requirements: "",
    budget: "",
    currency: "USD",
    client_name: "",
    company_name: "",
    message: "",
  };

  const days = [
    { id: "1", day_number: 1, destination: "Hanoi", overnight: "Hanoi", display_date: "", summary: "", meals: [], highlights: [], notes: [] },
    { id: "2", day_number: 2, destination: "Halong Bay", overnight: "Halong Bay", display_date: "", summary: "", meals: [], highlights: [], notes: [] },
    { id: "3", day_number: 3, destination: "Saigon", overnight: "Saigon", display_date: "", summary: "", meals: [], highlights: [], notes: [] },
  ];

  const canonical = tripAdapter.fromQuoteRequest(formState, days);
  assert.equal(canonical.arrivalCity, "Hanoi");
  assert.equal(canonical.departureCity, "Saigon");
  assert.deepEqual(canonical.destinations, ["Hanoi", "Halong Bay", "Saigon"]);
  assert.equal(canonical.routingConstraints, "Fixed flight VN50 arriving 06:30");

  const synced = tripAdapter.syncToQuoteRequest(canonical, formState);
  assert.equal(synced.formState.arrival_city, "Hanoi");
  assert.equal(synced.formState.departure_city, "Saigon");
  assert.deepEqual(synced.formState.destinations, ["Hanoi", "Halong Bay", "Saigon"]);
  assert.equal(synced.formState.routing_constraints, "Fixed flight VN50 arriving 06:30");
});
