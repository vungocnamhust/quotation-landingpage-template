import assert from 'node:assert/strict';

console.log('🧪 Starting Comprehensive Post-Refactor Verification Suite...\n');

let passedTests = 0;
let totalTests = 0;

function test(name, fn) {
  totalTests++;
  try {
    fn();
    console.log(`  ✅ PASS: ${name}`);
    passedTests++;
  } catch (error) {
    console.error(`  ❌ FAIL: ${name}`);
    console.error(`     Error: ${error.message}`);
    if (error.stack) {
      console.error(error.stack.split('\n').slice(1, 4).join('\n'));
    }
  }
}

// ==========================================
// 1. Prefill Rules & Pure Derivations Tests
// ==========================================
console.log('📦 1. Testing Prefill Rules (lib/prefillRules.ts)...');

import {
  inferPartyLabel,
  inferGreetingName,
  inferCommercialTotal,
  inferCommercialPerTraveler,
  validateHotelDates,
  getDefaultMealsForLang,
  inferOvernightDestination,
  inferDefaultCurrency,
} from '../lib/prefillRules.ts';

test('inferPartyLabel: generates accurate labels for various customer combinations', () => {
  assert.equal(inferPartyLabel('John Doe', 2, 0), 'John Doe & Party (2 Adults)');
  assert.equal(inferPartyLabel('Family Smith', 2, 2), 'Family Smith & Party (2 Adults, 2 Children)');
  assert.equal(inferPartyLabel(null, 1, 0), '1 Adult');
  assert.equal(inferPartyLabel(null, 3, 2), '3 Adults, 2 Children');
});

test('inferGreetingName: extracts clean greeting from customer name', () => {
  assert.equal(inferGreetingName('Mr. John Doe'), 'Dear Mr. John Doe');
  assert.equal(inferGreetingName('Dr. Jane Smith & Family'), 'Dear Dr. Jane Smith & Family');
  assert.equal(inferGreetingName(null), null);
});

test('inferCommercialTotal & inferCommercialPerTraveler: accurate minor calculation', () => {
  // 100 USD (10000 minor) * 2 adults = 20000 minor
  assert.equal(inferCommercialTotal(10000, 2), 20000);
  assert.equal(inferCommercialPerTraveler(20000, 2), 10000);
  assert.equal(inferCommercialTotal(null, 2), null);
  assert.equal(inferCommercialPerTraveler(null, 2), null);
});

test('validateHotelDates: validates check-in/out boundaries correctly', () => {
  const valid = validateHotelDates('2026-10-01', '2026-10-05', '2026-10-01', '2026-10-10');
  assert.equal(valid.valid, true);

  const invalidOrder = validateHotelDates('2026-10-05', '2026-10-01', '2026-10-01', '2026-10-10');
  assert.equal(invalidOrder.valid, false);

  const outOfTrip = validateHotelDates('2026-09-28', '2026-10-05', '2026-10-01', '2026-10-10');
  assert.equal(outOfTrip.valid, false);
});

test('getDefaultMealsForLang: provides localized default meals for EN, VI, AR', () => {
  assert.deepEqual(getDefaultMealsForLang('en'), ['Breakfast']);
  assert.deepEqual(getDefaultMealsForLang('vi'), ['Bữa sáng']);
  assert.deepEqual(getDefaultMealsForLang('ar'), ['الإفطار']);
});

test('inferOvernightDestination: handles destination overnight transitions', () => {
  assert.equal(inferOvernightDestination('Hanoi', null), 'Hanoi');
  assert.equal(inferOvernightDestination('Halong Bay', null), 'Halong Bay');
  assert.equal(inferOvernightDestination('Halong Bay', 'Hanoi'), 'Hanoi');
});

test('inferDefaultCurrency: returns appropriate default currency per brand & market', () => {
  assert.equal(inferDefaultCurrency('vietnam_safar', 'Vietnam'), 'VND');
  assert.equal(inferDefaultCurrency('capella_travel', 'US'), 'USD');
});


// ==========================================
// 2. Prefill Engine Atomic Updaters Tests
// ==========================================
console.log('\n⚙️ 2. Testing Prefill Engine (lib/prefillEngine.ts)...');

import {
  updateCustomerName,
  updateCustomerCounts,
  applyRouteDates,
  syncHotelsFromItineraryOvernights,
  createItineraryDayWithDefaults,
} from '../lib/prefillEngine.ts';
import { ensureFactsDefaults, emptyFacts } from '../components/quotation-workspace/factsTypes.ts';

test('updateCustomerName: updates party_label and greeting_name atomically when default', () => {
  const initial = ensureFactsDefaults(emptyFacts());
  const updated = updateCustomerName(initial, 'Alice Wonderland');
  assert.equal(updated.customer_facts.customer_name, 'Alice Wonderland');
  assert.equal(updated.customer_facts.greeting_name, 'Dear Alice Wonderland');
  assert.match(updated.customer_facts.party_label || '', /Alice Wonderland/);
});

test('updateCustomerCounts: updates adults/children and derived party_label', () => {
  const initial = ensureFactsDefaults(emptyFacts());
  const updated = updateCustomerCounts(initial, { adults: 4, children: 1 });
  assert.equal(updated.customer_facts.adults, 4);
  assert.equal(updated.customer_facts.children, 1);
  assert.match(updated.customer_facts.party_label || '', /4 Adults, 1 Child/);
});

test('applyRouteDates: updates duration and itinerary dates seamlessly', () => {
  const initial = ensureFactsDefaults(emptyFacts());
  const updated = applyRouteDates(initial, '2026-11-01', '2026-11-05', 5);
  assert.equal(updated.trip_facts.start_date, '2026-11-01');
  assert.equal(updated.trip_facts.end_date, '2026-11-05');
  assert.equal(updated.trip_facts.itinerary.length, 5);
  assert.equal(updated.trip_facts.itinerary[0].day_number, 1);
  assert.equal(updated.trip_facts.itinerary[4].day_number, 5);
});

test('syncHotelsFromItineraryOvernights: consolidates hotels from route itinerary', () => {
  const base = ensureFactsDefaults(emptyFacts());
  const withItinerary = {
    ...base,
    trip_facts: {
      ...base.trip_facts,
      start_date: '2026-11-01',
      end_date: '2026-11-04',
      itinerary: [
        { ...createItineraryDayWithDefaults({ index: 0, startDate: '2026-11-01', lang: 'en' }), destination: 'Hanoi', overnight: 'Hanoi' },
        { ...createItineraryDayWithDefaults({ index: 1, startDate: '2026-11-01', lang: 'en' }), destination: 'Hanoi', overnight: 'Hanoi' },
        { ...createItineraryDayWithDefaults({ index: 2, startDate: '2026-11-01', lang: 'en' }), destination: 'Halong Bay', overnight: 'Halong Bay' },
        { ...createItineraryDayWithDefaults({ index: 3, startDate: '2026-11-01', lang: 'en' }), destination: 'Hanoi', overnight: 'Hanoi' },
      ],
    },
    service_facts: {
      ...base.service_facts,
      hotels: [],
    },
  };

  const synced = syncHotelsFromItineraryOvernights(withItinerary);
  assert.equal(synced.service_facts.hotels.length >= 2, true);
  assert.equal(synced.service_facts.hotels[0].destination, 'Hanoi');
});


// ==========================================
// 3. Request to Facts Handoff Tests
// ==========================================
console.log('\n🔄 3. Testing Request-to-Facts Handoff (lib/requestToFactsHandoff.ts)...');

import { buildInitialFactsFromRequest } from '../lib/requestToFactsHandoff.ts';

test('buildInitialFactsFromRequest: maps Lead Request fields into valid QuotationFacts', () => {
  const mockRequest = {
    id: 'req-123',
    role: 'advisor',
    status: 'new',
    customer_name: 'Robert Stark',
    email: 'robert@winterfell.com',
    phone: '+123456789',
    company_name: 'North Advisors',
    market: 'US',
    preferred_contact: 'email',
    destinations: ['Hanoi', 'Hue', 'Hoi An'],
    start_date: '2026-12-01',
    end_date: '2026-12-07',
    raw_dates_text: 'Dec 1 - Dec 7, 2026',
    adults: 2,
    children: 1,
    kid_ages: [8],
    children_details: '1 child age 8',
    travel_style: 'Luxury / Cultural Immersion',
    special_requirements: 'Require ground floor rooms',
    payload_json: {
      client_name: 'Robert Stark',
      advisor: { name: 'Eddard Stark', agency_name: 'Winterfell Travel' },
      dietary: ['Vegetarian'],
      budget: 15000,
      currency: 'USD',
    },
    created_by_profile_id: 'prof-1',
    partner_id: 'partner-1',
    linked_quotation_id: null,
    created_at: '2026-08-17T00:00:00Z',
    updated_at: '2026-08-17T00:00:00Z',
  };

  const facts = buildInitialFactsFromRequest(mockRequest, ensureFactsDefaults(emptyFacts()));
  assert.equal(facts.customer_facts.customer_name, 'Robert Stark');
  assert.equal(facts.customer_facts.adults, 2);
  assert.equal(facts.customer_facts.children, 1);
  assert.deepEqual(facts.customer_facts.kid_ages, [8]);
  assert.equal(facts.trip_facts.destinations.length >= 1, true);
  assert.equal(facts.presentation_options.travel_designer_id, 'prof-1');
});


// ==========================================
// 4. Route Table Sync Tests
// ==========================================
console.log('\n🗺️ 4. Testing Route Table Sync (components/quotation-workspace/useRouteTableSync.ts)...');

import { deriveDayWithStays, syncRouteTableToFacts } from '../components/quotation-workspace/useRouteTableSync.ts';

test('deriveDayWithStays & syncRouteTableToFacts: roundtrip conversion', () => {
  const base = ensureFactsDefaults(emptyFacts());
  const withRoute = {
    ...base,
    trip_facts: {
      ...base.trip_facts,
      start_date: '2026-10-10',
      end_date: '2026-10-12',
      itinerary: [
        { ...createItineraryDayWithDefaults({ index: 0, startDate: '2026-10-10', lang: 'en' }), destination: 'Hanoi' },
        { ...createItineraryDayWithDefaults({ index: 1, startDate: '2026-10-10', lang: 'en' }), destination: 'Halong' },
        { ...createItineraryDayWithDefaults({ index: 2, startDate: '2026-10-10', lang: 'en' }), destination: 'Hanoi' },
      ],
    },
    service_facts: {
      ...base.service_facts,
      hotels: [
        { accommodation_id: 'hotel-1', destination: 'Hanoi', destination_ref: null, name: 'Sofitel Metropole', room_type: 'Luxury Room', check_in: null, check_out: null, intro: null, phone: null, display_city: null, display_date: null, hotel_asset: null, room_asset: null }
      ]
    }
  };

  const derived = deriveDayWithStays(withRoute);
  assert.equal(derived.length, 3);
  assert.equal(derived[0].destination, 'Hanoi');
  assert.equal(derived[0].accommodation_name, 'Sofitel Metropole');

  // Mutate second day stay
  const modified = [...derived];
  modified[1] = {
    ...modified[1],
    accommodation_id: 'hotel-2',
    accommodation_name: 'Paradise Cruise',
    room_type: 'Balcony Suite',
  };

  const syncedFacts = syncRouteTableToFacts(withRoute, modified);
  assert.equal(syncedFacts.trip_facts.itinerary.length, 3);
  assert.equal(syncedFacts.service_facts.hotels.length >= 2, true);
  assert.equal(syncedFacts.service_facts.hotels.some(h => h.name === 'Paradise Cruise'), true);
});


// ==========================================
// 5. Prompt Options Catalog Tests
// ==========================================
console.log('\n📚 5. Testing Prompt Options Catalog (components/content-studio/promptOptionsCatalog.ts)...');

import {
  BRAND_OPTIONS,
  MODE_OPTIONS,
  GROUND_RULE_OPTIONS,
  CONSTRAINT_OPTIONS,
} from '../components/content-studio/promptOptionsCatalog.ts';

test('promptOptionsCatalog: contains required structured entries', () => {
  assert.equal(BRAND_OPTIONS.length >= 3, true);
  assert.equal(BRAND_OPTIONS.some(b => b.id === 'capella_travel'), true);
  assert.equal(BRAND_OPTIONS.some(b => b.id === 'selvara'), true);
  assert.equal(BRAND_OPTIONS.some(b => b.id === 'vietnam_safar'), true);

  assert.equal(MODE_OPTIONS.length >= 2, true);
  assert.equal(MODE_OPTIONS.some(m => m.id === 'storytelling'), true);
  assert.equal(MODE_OPTIONS.some(m => m.id === 'detailed'), true);

  assert.equal(GROUND_RULE_OPTIONS.length >= 5, true);
  assert.equal(GROUND_RULE_OPTIONS.some(g => g.id === 'GR-7030'), true);
  assert.equal(GROUND_RULE_OPTIONS.some(g => g.id === 'GR-DAY-NAMING'), true);

  assert.equal(CONSTRAINT_OPTIONS.length >= 3, true);
  assert.equal(CONSTRAINT_OPTIONS.some(c => c.id === 'schema_validation'), true);
});


// ==========================================
// 6. Tour Components Catalog & Accommodation Utilities Tests
// ==========================================
console.log('\n🏨 6. Testing Tour Components Catalog & Accommodation Manager...');

import { CATEGORIES } from '../components/staff-workspace/tourComponentsCatalog.ts';
import {
  blankAccommodationInput,
  profileToInput,
} from '../components/staff-workspace/accommodations/useAccommodationManager.ts';

test('CATEGORIES: contains 6 complete categories with emptyTitle and actionLabel', () => {
  assert.equal(CATEGORIES.length, 6);
  const keys = CATEGORIES.map((c) => c.key);
  assert.deepEqual(keys, [
    'accommodations',
    'travel_styles',
    'cars',
    'experiences',
    'tickets',
    'destinations',
  ]);
  for (const cat of CATEGORIES) {
    assert.equal(typeof cat.emptyTitle, 'string');
    assert.equal(typeof cat.emptyDescription, 'string');
    assert.equal(typeof cat.actionLabel, 'string');
    assert.equal(Boolean(cat.icon), true);
  }
});

test('blankAccommodationInput: creates a clean blank input', () => {
  const blank = blankAccommodationInput();
  assert.equal(blank.name, '');
  assert.equal(blank.destinationId, '');
  assert.equal(blank.room_type, null);
  assert.equal(blank.hotel_asset, null);
  assert.equal(blank.room_asset, null);
});

test('profileToInput: accurately converts AccommodationProfile to AccommodationProfileInput', () => {
  const mockProfile = {
    id: 'hotel-123',
    destination_id: 'dest-hanoi',
    destination: 'Hanoi',
    destination_ref: { id: 'dest-hanoi', name: 'Hanoi', region: 'North', is_primary: true },
    name: 'Sofitel Legend Metropole',
    room_type: 'Grand Luxury Suite',
    intro: 'Iconic luxury hotel in central Hanoi.',
    phone: '+84 24 3826 6919',
    display_city: 'Hanoi Capital',
    display_date: 'Oct 15, 2026',
    hotel_asset: 'r2-hotel-key',
    room_asset: 'r2-room-key',
    is_active: true,
    created_at: '2026-08-10',
    updated_at: '2026-08-17',
  };

  const input = profileToInput(mockProfile);
  assert.equal(input.destinationId, 'dest-hanoi');
  assert.equal(input.name, 'Sofitel Legend Metropole');
  assert.equal(input.room_type, 'Grand Luxury Suite');
  assert.equal(input.intro, 'Iconic luxury hotel in central Hanoi.');
  assert.equal(input.phone, '+84 24 3826 6919');
  assert.equal(input.hotel_asset, 'r2-hotel-key');
  assert.equal(input.room_asset, 'r2-room-key');
});


// ==========================================
// 7. Itinerary Day Standardization (3 Use Cases)
// ==========================================
console.log('🗓️  7. Testing Itinerary Day Standardization (Use Cases 1, 2, 3)...');

import {
  consolidateStaysFromDayItems,
  hydrateDayAccommodationsFromHotels,
} from '../lib/rules/staysRules.ts';
import {
  dateForItineraryDay,
  formatDisplayDate,
} from '../lib/rules/datesRules.ts';

// Use Case 1: QuoteRequest Summary Mode
test('UseCase 1: Basic Itinerary Day date projection & summary structure', () => {
  const startDate = '2026-11-09';
  const day1Date = dateForItineraryDay(startDate, 1);
  const day3Date = dateForItineraryDay(startDate, 3);
  assert.equal(day1Date, '2026-11-09');
  assert.equal(day3Date, '2026-11-11');
  assert.equal(formatDisplayDate(day1Date), 'Mon 09 Nov');

  const basicDay = {
    day_number: 1,
    destination: 'Hanoi',
    display_date: formatDisplayDate(day1Date),
    summary: 'Arrival in Hanoi, street food tasting tour',
    overnight: 'Hanoi',
  };
  assert.equal(basicDay.day_number, 1);
  assert.equal(basicDay.destination, 'Hanoi');
  assert.equal(typeof basicDay.summary, 'string');
});

// Use Case 2: NewQuote Intake Blueprint Mode (Route & Stays Consolidation)
test('UseCase 2: Stays Consolidation from DayWithStayItems', () => {
  const startDate = '2026-11-10';
  const intakeDays = [
    { day_number: 1, destination: 'Hanoi', accommodation_id: 'acc-metropole', accommodation_name: 'Sofitel Legend Metropole', room_type: 'Luxury Room', summary: 'Arrival' },
    { day_number: 2, destination: 'Hanoi', accommodation_id: 'acc-metropole', accommodation_name: 'Sofitel Legend Metropole', room_type: 'Luxury Room', summary: 'City tour' },
    { day_number: 3, destination: 'Hanoi', accommodation_id: 'acc-metropole', accommodation_name: 'Sofitel Legend Metropole', room_type: 'Luxury Room', summary: 'Museums' },
    { day_number: 4, destination: 'Halong Bay', accommodation_id: 'acc-heritage-cruise', accommodation_name: 'Heritage Line Cruise', room_type: 'Captain Suite', summary: 'Boarding cruise' },
    { day_number: 5, destination: 'Hanoi', accommodation_id: null, accommodation_name: null, summary: 'Transfer & Departure' },
  ];

  const stays = consolidateStaysFromDayItems(intakeDays, startDate);
  assert.equal(stays.length, 2);

  // Metropole stay: 3 nights (Day 1, 2, 3) -> check-in: 2026-11-10, check-out: 2026-11-13
  assert.equal(stays[0].name, 'Sofitel Legend Metropole');
  assert.equal(stays[0].accommodation_id, 'acc-metropole');
  assert.equal(stays[0].check_in, '2026-11-10');
  assert.equal(stays[0].check_out, '2026-11-13');

  // Heritage Cruise: 1 night (Day 4) -> check-in: 2026-11-13, check-out: 2026-11-14
  assert.equal(stays[1].name, 'Heritage Line Cruise');
  assert.equal(stays[1].accommodation_id, 'acc-heritage-cruise');
  assert.equal(stays[1].check_in, '2026-11-13');
  assert.equal(stays[1].check_out, '2026-11-14');
});

// Use Case 3: Quotation Workspace Detail Mode & Bi-directional Synchronization
test('UseCase 3: Bi-directional sync & hydration between Itinerary Days and Hotels', () => {
  const startDate = '2026-11-10';
  const initialFacts = {
    ...emptyFacts(),
    trip_facts: {
      ...emptyFacts().trip_facts,
      start_date: startDate,
      itinerary: [
        { day_number: 1, destination: 'Hanoi', summary: 'Day 1 in Hanoi', meals: ['Breakfast'], highlights: [], notes: [], display_date: '2026-11-10', overnight: 'Hanoi', sense_of_pace: 'balanced' },
        { day_number: 2, destination: 'Hanoi', summary: 'Day 2 in Hanoi', meals: ['Breakfast'], highlights: [], notes: [], display_date: '2026-11-11', overnight: 'Hanoi', sense_of_pace: 'balanced' },
        { day_number: 3, destination: 'Hue', summary: 'Fly to Hue', meals: ['Breakfast'], highlights: [], notes: [], display_date: '2026-11-12', overnight: 'Hue', sense_of_pace: 'balanced' },
      ],
    },
    service_facts: {
      ...emptyFacts().service_facts,
      hotels: [
        { accommodation_id: 'acc-metropole', name: 'Sofitel Legend Metropole', destination: 'Hanoi', room_type: 'Luxury Room', check_in: '2026-11-10', check_out: '2026-11-12', intro: 'Breakfast included.', phone: null, display_city: 'Hanoi', display_date: null, hotel_asset: null, room_asset: null },
        { accommodation_id: 'acc-azerai', name: 'Azerai La Residence Hue', destination: 'Hue', room_type: 'Superior Suite', check_in: '2026-11-12', check_out: '2026-11-13', intro: 'Breakfast included.', phone: null, display_city: 'Hue', display_date: null, hotel_asset: null, room_asset: null },
      ],
    },
  };

  // Test 3.1: Hydrate days from hotels
  const hydratedItinerary = hydrateDayAccommodationsFromHotels(
    initialFacts.trip_facts.itinerary,
    initialFacts.service_facts.hotels,
    startDate
  );
  assert.equal(hydratedItinerary[0].accommodation_name, 'Sofitel Legend Metropole');
  assert.equal(hydratedItinerary[1].accommodation_name, 'Sofitel Legend Metropole');
  assert.equal(hydratedItinerary[2].accommodation_name, 'Azerai La Residence Hue');

  // Test 3.2: Sync modified route table to facts
  const modifiedDays = [
    { day_number: 1, destination: 'Hanoi', accommodation_id: 'acc-capella', accommodation_name: 'Capella Hanoi', room_type: 'Opera Suite', summary: 'Day 1' },
    { day_number: 2, destination: 'Hanoi', accommodation_id: 'acc-capella', accommodation_name: 'Capella Hanoi', room_type: 'Opera Suite', summary: 'Day 2' },
  ];
  const syncedFacts = syncRouteTableToFacts(initialFacts, modifiedDays);
  assert.equal(syncedFacts.trip_facts.itinerary[0].accommodation_name, 'Capella Hanoi');
  assert.equal(syncedFacts.service_facts.hotels[0].name, 'Capella Hanoi');
  assert.equal(syncedFacts.service_facts.hotels[0].check_in, '2026-11-10');
  assert.equal(syncedFacts.service_facts.hotels[0].check_out, '2026-11-12');
});

// ==========================================
// 8. Temporal Trip Reconciler & Adapter Tests
// ==========================================
console.log('\n⏱️  8. Testing Temporal Trip Reconciler & Trip Adapter...');

import { tripReconciler } from '../lib/rules/tripReconciler.ts';
import { tripAdapter } from '../lib/rules/tripAdapter.ts';
import { getInitialQuoteRequestFormState } from '../lib/quoteRequestPayload.ts';

test('tripReconciler.addDay: auto-updates endDate, duration and projects display_date', () => {
  const initial = {
    startDate: '2026-11-01',
    endDate: null,
    durationDays: null,
    durationNights: null,
    itinerary: [],
  };

  const withDay1 = tripReconciler.addDay(initial, { destination: 'Hanoi' });
  assert.equal(withDay1.itinerary.length, 1);
  assert.equal(withDay1.endDate, '2026-11-01');
  assert.equal(withDay1.durationDays, 1);
  assert.equal(withDay1.durationNights, 0);
  assert.equal(withDay1.itinerary[0].day_number, 1);

  const withDay2 = tripReconciler.addDay(withDay1, { destination: 'Hanoi' });
  assert.equal(withDay2.itinerary.length, 2);
  assert.equal(withDay2.endDate, '2026-11-02');
  assert.equal(withDay2.durationDays, 2);
  assert.equal(withDay2.durationNights, 1);
});

test('tripReconciler.removeDay: pulls back endDate and re-indexes remaining days', () => {
  const initial = {
    startDate: '2026-11-01',
    endDate: '2026-11-03',
    durationDays: 3,
    durationNights: 2,
    itinerary: [
      { day_number: 1, destination: 'Hanoi', overnight: 'Hanoi', display_date: '01 Nov', summary: 'Day 1' },
      { day_number: 2, destination: 'Halong', overnight: 'Halong', display_date: '02 Nov', summary: 'Day 2' },
      { day_number: 3, destination: 'Hue', overnight: 'Hue', display_date: '03 Nov', summary: 'Day 3' },
    ],
  };

  const afterRemove = tripReconciler.removeDay(initial, 1);
  assert.equal(afterRemove.itinerary.length, 2);
  assert.equal(afterRemove.endDate, '2026-11-02');
  assert.equal(afterRemove.durationDays, 2);
  assert.equal(afterRemove.durationNights, 1);
  assert.equal(afterRemove.itinerary[0].day_number, 1);
  assert.equal(afterRemove.itinerary[1].day_number, 2);
  assert.equal(afterRemove.itinerary[1].destination, 'Hue');
});

test('tripReconciler.setStartDate: shifts display dates and updates endDate preserving duration', () => {
  const initial = {
    startDate: '2026-11-01',
    endDate: '2026-11-03',
    durationDays: 3,
    durationNights: 2,
    itinerary: [
      { day_number: 1, destination: 'Hanoi', overnight: 'Hanoi', display_date: null, summary: null },
      { day_number: 2, destination: 'Halong', overnight: 'Halong', display_date: null, summary: null },
      { day_number: 3, destination: 'Hue', overnight: 'Hue', display_date: null, summary: null },
    ],
  };

  const shifted = tripReconciler.setStartDate(initial, '2026-12-10');
  assert.equal(shifted.startDate, '2026-12-10');
  assert.equal(shifted.endDate, '2026-12-12');
  assert.equal(shifted.durationDays, 3);
  assert.equal(shifted.durationNights, 2);
});

test('tripAdapter: bidirectional sync between QuoteRequestFormState and CanonicalTrip', () => {
  const formState = getInitialQuoteRequestFormState('traveller');
  formState.arrival_date = '2026-11-01';
  formState.departure_date = '2026-11-03';

  const days = [
    { day_number: 1, destination: 'Hanoi', overnight: 'Hanoi', display_date: '01 Nov', summary: 'Arrival' },
    { day_number: 2, destination: 'Hanoi', overnight: 'Hanoi', display_date: '02 Nov', summary: 'City tour' },
    { day_number: 3, destination: 'Halong', overnight: 'Halong', display_date: '03 Nov', summary: 'Cruise' },
  ];

  const canonical = tripAdapter.fromQuoteRequest(formState, days);
  assert.equal(canonical.startDate, '2026-11-01');
  assert.equal(canonical.endDate, '2026-11-03');
  assert.equal(canonical.durationDays, 3);

  const expanded = tripReconciler.addDay(canonical, { destination: 'Hue' });
  const synced = tripAdapter.syncToQuoteRequest(expanded, formState);

  assert.equal(synced.formState.arrival_date, '2026-11-01');
  assert.equal(synced.formState.departure_date, '2026-11-04');
  assert.equal(synced.itineraryDays.length, 4);
  assert.equal(synced.itineraryDays[3].day_number, 4);
  assert.equal(synced.itineraryDays[3].destination, 'Hue');
});

// ==========================================
// 9. Route Rules & Route Sequence Synchronization
// ==========================================
console.log('\n🗺️  9. Testing Route Rules & Sequence Synchronization (lib/rules/routeRules.ts)...');

import {
  parseRouteTokens,
  formatRouteString,
  deriveRouteFromItinerary,
} from '../lib/rules/routeRules.ts';

test('routeRules.parseRouteTokens: accurately parses arrow, dash, comma, and newline delimiters', () => {
  const parsed1 = parseRouteTokens('Ho Chi Minh -> Mekong Delta -> Da Nang -> Hanoi');
  assert.deepEqual(parsed1, ['Ho Chi Minh', 'Mekong Delta', 'Da Nang', 'Hanoi']);

  const parsed2 = parseRouteTokens('Hanoi – Halong Bay — Hue, Hoi An\nSaigon');
  assert.deepEqual(parsed2, ['Hanoi', 'Halong Bay', 'Hue', 'Hoi An', 'Saigon']);
});

test('routeRules.formatRouteString: formats clean standardized brochure route string', () => {
  const formatted = formatRouteString(['Hanoi', 'Halong Bay', 'Hue']);
  assert.equal(formatted, 'Hanoi – Halong Bay – Hue');
});

test('routeRules.deriveRouteFromItinerary: extracts arrivalCity, departureCity, and unique destinations in order', () => {
  const days = [
    { day_number: 1, destination: 'Ho Chi Minh City', overnight: 'Ho Chi Minh City' },
    { day_number: 2, destination: 'Mekong Delta', overnight: 'Can Tho' },
    { day_number: 3, destination: 'Da Nang', overnight: 'Da Nang' },
    { day_number: 4, destination: 'Hanoi', overnight: 'Hanoi' },
  ];

  const meta = deriveRouteFromItinerary(days);
  assert.equal(meta.arrivalCity, 'Ho Chi Minh City');
  assert.equal(meta.departureCity, 'Hanoi');
  assert.deepEqual(meta.destinations, ['Ho Chi Minh City', 'Mekong Delta', 'Da Nang', 'Hanoi']);
  assert.equal(meta.displayRouteText, 'Ho Chi Minh City – Mekong Delta – Da Nang – Hanoi');
});

test('tripReconciler.applyRouteSequence: expands itinerary, recalculates dates and syncs route metadata', () => {
  const initial = {
    startDate: '2026-11-01',
    endDate: null,
    durationDays: null,
    durationNights: null,
    itinerary: [],
    lang: 'en',
  };

  const updated = tripReconciler.applyRouteSequence(initial, [
    'Ho Chi Minh City',
    'Mekong Delta',
    'Da Nang',
    'Hanoi',
  ]);

  assert.equal(updated.itinerary.length, 4);
  assert.equal(updated.startDate, '2026-11-01');
  assert.equal(updated.endDate, '2026-11-04');
  assert.equal(updated.durationDays, 4);
  assert.equal(updated.durationNights, 3);
  assert.equal(updated.arrivalCity, 'Ho Chi Minh City');
  assert.equal(updated.departureCity, 'Hanoi');
  assert.deepEqual(updated.destinations, ['Ho Chi Minh City', 'Mekong Delta', 'Da Nang', 'Hanoi']);
});


// ==========================================
// 10. New Quotation Add/Remove Day Reconciler & Handoff Tests
// ==========================================
console.log('\n✨ 10. Testing New Quotation Add/Remove Day Reconciler (useRouteTableSync.ts)...');

import { addDayToRouteTable, removeDayFromRouteTable } from '../components/quotation-workspace/useRouteTableSync.ts';
import { createBrochureFacts } from '../components/quotation-workspace/factsTypes.ts';

test('New Quotation: addDayToRouteTable expands itinerary, extends end_date and syncs hotels', () => {
  const baseFacts = createBrochureFacts();
  baseFacts.trip_facts.start_date = '2026-11-01';
  baseFacts.trip_facts.end_date = '2026-11-02';
  baseFacts.trip_facts.itinerary = [
    {
      day_number: 1,
      destination: 'Hanoi',
      overnight: 'Hanoi',
      display_date: '01 Nov',
      summary: 'Arrival',
      accommodation_id: 'acc_metropole',
      accommodation_name: 'Sofitel Metropole',
      room_type: 'Luxury',
      meals: ['Breakfast'],
      highlights: [],
      notes: [],
      sense_of_pace: 'balanced',
    },
    {
      day_number: 2,
      destination: 'Hanoi',
      overnight: 'Hanoi',
      display_date: '02 Nov',
      summary: 'City Tour',
      accommodation_id: 'acc_metropole',
      accommodation_name: 'Sofitel Metropole',
      room_type: 'Luxury',
      meals: ['Breakfast'],
      highlights: [],
      notes: [],
      sense_of_pace: 'balanced',
    },
  ];

  const expanded = addDayToRouteTable(baseFacts, {
    destination: 'Halong Bay',
    accommodation_id: 'acc_cruise',
    accommodation_name: 'Heritage Cruise',
  });

  assert.equal(expanded.trip_facts.itinerary.length, 3);
  assert.equal(expanded.trip_facts.start_date, '2026-11-01');
  assert.equal(expanded.trip_facts.end_date, '2026-11-03');
  assert.equal(expanded.trip_facts.duration_days, 3);
  assert.equal(expanded.trip_facts.itinerary[2].destination, 'Halong Bay');
  assert.equal(expanded.service_facts.hotels.length, 2);
  assert.equal(expanded.service_facts.hotels[0].name, 'Sofitel Metropole');
  assert.equal(expanded.service_facts.hotels[1].name, 'Heritage Cruise');
});

test('New Quotation: removeDayFromRouteTable pulls back end_date, re-indexes and consolidates stays', () => {
  const baseFacts = createBrochureFacts();
  baseFacts.trip_facts.start_date = '2026-11-01';
  baseFacts.trip_facts.end_date = '2026-11-03';
  baseFacts.trip_facts.itinerary = [
    {
      day_number: 1,
      destination: 'Hanoi',
      overnight: 'Hanoi',
      display_date: '01 Nov',
      summary: 'Day 1',
      meals: ['Breakfast'],
      highlights: [],
      notes: [],
      sense_of_pace: 'balanced',
    },
    {
      day_number: 2,
      destination: 'Halong',
      overnight: 'Halong',
      display_date: '02 Nov',
      summary: 'Day 2',
      meals: ['Breakfast'],
      highlights: [],
      notes: [],
      sense_of_pace: 'balanced',
    },
    {
      day_number: 3,
      destination: 'Hanoi',
      overnight: 'Hanoi',
      display_date: '03 Nov',
      summary: 'Day 3',
      meals: ['Breakfast'],
      highlights: [],
      notes: [],
      sense_of_pace: 'balanced',
    },
  ];

  const contracted = removeDayFromRouteTable(baseFacts, 1);
  assert.equal(contracted.trip_facts.itinerary.length, 2);
  assert.equal(contracted.trip_facts.start_date, '2026-11-01');
  assert.equal(contracted.trip_facts.end_date, '2026-11-02');
  assert.equal(contracted.trip_facts.duration_days, 2);
  assert.equal(contracted.trip_facts.itinerary[0].day_number, 1);
  assert.equal(contracted.trip_facts.itinerary[1].day_number, 2);
  assert.equal(contracted.trip_facts.itinerary[1].summary, 'Day 3');
});

// ==========================================
// Summary
// ==========================================
console.log('\n==========================================');
console.log(`📊 Test Results: ${passedTests}/${totalTests} Passed`);
if (passedTests === totalTests) {
  console.log('🎉 ALL UNIT & INTEGRATION ASSERTIONS PASSED WITH 0 ERRORS!');
  process.exit(0);
} else {
  console.error(`🚨 ${totalTests - passedTests} TESTS FAILED!`);
  process.exit(1);
}


