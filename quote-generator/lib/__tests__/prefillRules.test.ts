import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  inferGreetingName,
  inferPartyLabel,
  inferOvernightDestination,
  getDefaultMealsForLang,
  deriveStaySegmentsFromItinerary,
  inferCommercialTotal,
  inferCommercialPerTraveler,
} from '../prefillRules.ts';
import {
  createBrochureFacts,
  type ItineraryDayFact,
} from '../../components/quotation-workspace/factsTypes.ts';
import {
  updateCustomerName,
  updateCustomerCounts,
  updateCustomerKidAges,
  updateCustomerRoomNotes,
  updateTravelStyle,
  updateDesignerPresentationFacts,
  createItineraryDayWithDefaults,
  patchPricingOptionWithInference,
  updatePricingOptionAdultInFacts,
  applyChildPresetInFacts,
  updatePricingOptionTotalInFacts,
  convertOptionCurrencyInFacts,
  patchItineraryDayInFacts,
  addHotelToFacts,
  removeHotelFromFacts,
} from '../prefillEngine.ts';

describe('prefillRules pure business rules', () => {
  describe('inferGreetingName', () => {
    it('extracts greeting name from full name', () => {
      assert.equal(inferGreetingName('John Smith'), 'Dear John Smith');
      assert.equal(inferGreetingName('Nguyen Van A', 'vi'), 'Kính gửi Nguyen Van A');
    });

    it('returns empty string or null for empty name', () => {
      assert.equal(inferGreetingName(''), null);
      assert.equal(inferGreetingName(null), null);
    });
  });

  describe('inferPartyLabel', () => {
    it('formats party label based on customer name and headcounts', () => {
      assert.equal(inferPartyLabel('Smith', 2, 0), 'Smith & Party (2 Adults)');
      assert.equal(inferPartyLabel('John Smith', 2, 2), 'John Smith & Party (2 Adults, 2 Children)');
    });

    it('handles fallback when name is missing', () => {
      assert.equal(inferPartyLabel(null, 1, 0), '1 Adult');
      assert.equal(inferPartyLabel(null, 2, 0), '2 Adults');
    });
  });

  describe('inferOvernightDestination', () => {
    it('defaults overnight to destination if current is blank', () => {
      assert.equal(inferOvernightDestination('Hanoi', null), 'Hanoi');
      assert.equal(inferOvernightDestination('Hanoi', ''), 'Hanoi');
    });

    it('preserves existing custom overnight destination', () => {
      assert.equal(inferOvernightDestination('Halong Bay', 'Hanoi'), 'Hanoi');
    });
  });

  describe('getDefaultMealsForLang', () => {
    it('returns localized breakfast meal plans based on language code', () => {
      assert.deepEqual(getDefaultMealsForLang('en'), ['Breakfast']);
      assert.deepEqual(getDefaultMealsForLang('vi'), ['Bữa sáng']);
      assert.deepEqual(getDefaultMealsForLang('ar'), ['الإفطار']);
    });
  });

  describe('deriveStaySegmentsFromItinerary', () => {
    it('groups consecutive days with identical overnight location into a single stay segment', () => {
      const days = [
        { day_number: 1, destination: 'Hanoi', overnight: 'Hanoi' },
        { day_number: 2, destination: 'Hanoi', overnight: 'Hanoi' },
        { day_number: 3, destination: 'Ninh Binh', overnight: 'Hanoi' },
        { day_number: 4, destination: 'Hue', overnight: 'Hue' },
      ];
      const segments = deriveStaySegmentsFromItinerary(days as unknown as ItineraryDayFact[], '2026-10-01', '2026-10-04');
      assert.equal(segments.length, 2);
      assert.equal(segments[0].city, 'Hanoi');
      assert.equal(segments[0].dayStart, 1);
      assert.equal(segments[0].dayEnd, 3);
      assert.equal(segments[0].nights, 3);
      assert.equal(segments[1].city, 'Hue');
      assert.equal(segments[1].dayStart, 4);
      assert.equal(segments[1].dayEnd, 4);
      assert.equal(segments[1].nights, 1);
    });
  });

  describe('commercial pricing derivations', () => {
    it('calculates total group amount from per-traveler rates', () => {
      const total = inferCommercialTotal(10000, 2);
      assert.equal(total, 20000);
    });

    it('calculates per-traveler amount from total group amount', () => {
      const perTraveler = inferCommercialPerTraveler(20000, 2);
      assert.equal(perTraveler, 10000);
    });
  });
});

describe('prefillEngine single-pass facade updaters', () => {
  it('updateCustomerName updates party label and greeting automatically', () => {
    const initialFacts = createBrochureFacts();
    const updated = updateCustomerName(initialFacts, 'David Miller');
    assert.equal(updated.customer_facts.customer_name, 'David Miller');
    assert.equal(updated.customer_facts.greeting_name, 'Dear David Miller');
    assert.equal(updated.customer_facts.party_label, 'David Miller & Party (2 Adults)');
  });

  it('updateCustomerCounts updates party label and auto-syncs pricing options', () => {
    const initialFacts = createBrochureFacts();
    initialFacts.customer_facts.adults = 2;
    initialFacts.customer_facts.children = 0;
    initialFacts.pricing_facts.options = [
      {
        id: 'opt-1',
        label: 'Luxury Option',
        currency: 'USD',
        per_adult_amount_minor: 400000, // $4,000
        per_child_amount_minor: null,
        per_traveler_amount_minor: 400000,
        group_total_amount_minor: 800000, // $8,000
      },
    ];

    const withName = updateCustomerName(initialFacts, 'David Miller');
    const withFamily = updateCustomerCounts(withName, { adults: 4, children: 2 });
    assert.equal(withFamily.customer_facts.adults, 4);
    assert.equal(withFamily.customer_facts.children, 2);
    assert.equal(withFamily.customer_facts.party_label, 'David Miller & Party (4 Adults, 2 Children)');

    // Invariant: option group_total_amount_minor automatically updated!
    // 4 adults x $4,000 + 2 children x $3,000 = $22,000 (2,200,000 cents)
    assert.equal(withFamily.pricing_facts.options[0].per_adult_amount_minor, 400000);
    assert.equal(withFamily.pricing_facts.options[0].per_child_amount_minor, 300000);
    assert.equal(withFamily.pricing_facts.options[0].group_total_amount_minor, 2200000);
  });

  it('commercial pricing facade helpers update options and invariants', () => {
    const facts = createBrochureFacts();
    facts.customer_facts.adults = 2;
    facts.customer_facts.children = 1;
    facts.pricing_facts.options = [
      {
        id: 'opt-1',
        label: 'Standard Option',
        currency: 'USD',
        per_adult_amount_minor: 400000,
        per_child_amount_minor: 300000,
        per_traveler_amount_minor: 400000,
        group_total_amount_minor: 1100000,
      },
    ];

    // 1. update adult rate to $5,000 (500,000)
    const withAdult = updatePricingOptionAdultInFacts(facts, 0, 500000);
    assert.equal(withAdult.pricing_facts.options[0].per_adult_amount_minor, 500000);
    assert.equal(withAdult.pricing_facts.options[0].group_total_amount_minor, 1300000); // 2*5k + 3k

    // 2. apply 50% child preset -> child = 250,000
    const withPreset = applyChildPresetInFacts(withAdult, 0, 0.5);
    assert.equal(withPreset.pricing_facts.options[0].per_child_amount_minor, 250000);
    assert.equal(withPreset.pricing_facts.options[0].group_total_amount_minor, 1250000); // 2*5k + 2.5k

    // 3. update group total -> $10,000 (1,000,000)
    const withTotal = updatePricingOptionTotalInFacts(withPreset, 0, 1000000);
    assert.equal(withTotal.pricing_facts.options[0].group_total_amount_minor, 1000000);
    assert.ok((withTotal.pricing_facts.options[0].per_adult_amount_minor ?? 0) > 0);

    // 4. convert currency to VND
    const inVnd = convertOptionCurrencyInFacts(facts, 0, 'VND', true);
    assert.equal(inVnd.pricing_facts.options[0].currency, 'VND');
    assert.equal(inVnd.pricing_facts.options[0].per_adult_amount_minor, 101600000);
  });

  it('createItineraryDayWithDefaults sets localized meal defaults', () => {
    const dayVi = createItineraryDayWithDefaults({ index: 0, startDate: '2026-10-01', lang: 'vi' });
    assert.deepEqual(dayVi.meals, ['Bữa sáng']);

    const dayEn = createItineraryDayWithDefaults({ index: 0, startDate: '2026-10-01', lang: 'en' });
    assert.deepEqual(dayEn.meals, ['Breakfast']);
  });

  it('patchPricingOptionWithInference handles atomic single-field dispatches correctly', () => {
    const facts = createBrochureFacts();
    facts.customer_facts.adults = 2;
    facts.customer_facts.children = 1;
    facts.pricing_facts.options = [
      {
        id: 'opt-1',
        label: 'Luxury Option',
        currency: 'USD',
        per_adult_amount_minor: 400000,
        per_child_amount_minor: 300000,
        per_traveler_amount_minor: 400000,
        group_total_amount_minor: 1100000,
      },
    ];

    // 1. Atomic adult price change: dispatch only per_adult_amount_minor (600,000)
    // 2 adults x 600,000 + 1 child x 300,000 = 1,500,000
    const withAdult = patchPricingOptionWithInference(facts, 0, {
      per_adult_amount_minor: 600000,
      per_traveler_amount_minor: 600000,
    });
    assert.equal(withAdult.pricing_facts.options[0].per_adult_amount_minor, 600000);
    assert.equal(withAdult.pricing_facts.options[0].per_child_amount_minor, 300000);
    assert.equal(withAdult.pricing_facts.options[0].group_total_amount_minor, 1500000);

    // 2. Atomic total change: dispatch only group_total_amount_minor (2,000,000)
    const withTotal = patchPricingOptionWithInference(withAdult, 0, {
      group_total_amount_minor: 2000000,
    });
    assert.equal(withTotal.pricing_facts.options[0].group_total_amount_minor, 2000000);
    assert.ok((withTotal.pricing_facts.options[0].per_adult_amount_minor ?? 0) > 0);
  });

  it('updateCustomerKidAges and updateCustomerRoomNotes reconcile party & service facts', () => {
    let facts = createBrochureFacts();
    facts = updateCustomerCounts(facts, { adults: 2, children: 2 });
    assert.deepEqual(facts.customer_facts.kid_ages, [6, 6]);

    facts = updateCustomerKidAges(facts, [10, 14]);
    assert.deepEqual(facts.customer_facts.kid_ages, [10, 14]);

    facts = updateCustomerRoomNotes(facts, 'Connecting rooms on high floor requested');
    assert.equal(facts.service_facts.room_notes, 'Connecting rooms on high floor requested');
  });

  it('updateTravelStyle updates travel_style and guest_profile via partyAdapter', () => {
    let facts = createBrochureFacts();
    facts = updateTravelStyle(facts, 'Family, Luxury Adventure');
    assert.equal(facts.customer_facts.travel_style, 'Family, Luxury Adventure');
    assert.equal(facts.customer_facts.guest_profile, 'Family, Luxury Adventure');
  });

  it('updateDesignerPresentationFacts updates booking title, customer labels, market and designer facts', () => {
    let facts = createBrochureFacts();
    facts = updateCustomerName(facts, 'Alexander Vance');

    facts = updateDesignerPresentationFacts(facts, {
      booking_title: 'Grand Vietnam Journey',
      booking_description: 'An exclusive bespoke itinerary',
      customer_party_label: 'Vance Family VIP Delegation',
      customer_greeting_name: 'Dear Alexander and Family',
      customer_market: 'North America',
      hero_title: 'Unforgettable Indochina',
    });

    assert.equal(facts.booking_facts.title, 'Grand Vietnam Journey');
    assert.equal(facts.booking_facts.description, 'An exclusive bespoke itinerary');
  });

  it('patchItineraryDayInFacts updates destination, overnight and delegates accommodation cascade', () => {
    const facts = createBrochureFacts();
    facts.trip_facts.start_date = '2026-10-01';
    facts.trip_facts.itinerary = [
      {
        day_number: 1,
        destination: 'Hanoi',
        destination_ref: null,
        overnight: 'Hanoi',
        display_date: '01 Oct',
        summary: 'Arrival',
        meals: ['Breakfast'],
        highlights: [],
        notes: [],
        sense_of_pace: 'balanced',
        accommodation_id: null,
        accommodation_name: null,
        room_type: null,
      },
      {
        day_number: 2,
        destination: 'Hanoi',
        destination_ref: null,
        overnight: 'Hanoi',
        display_date: '02 Oct',
        summary: 'City exploration',
        meals: ['Breakfast'],
        highlights: [],
        notes: [],
        sense_of_pace: 'balanced',
        accommodation_id: null,
        accommodation_name: null,
        room_type: null,
      },
    ];

    // 1. Changing destination on Day 1 auto-updates overnight
    const withDest = patchItineraryDayInFacts(facts, 0, { destination: 'Hue' });
    assert.equal(withDest.trip_facts.itinerary[0].destination, 'Hue');
    assert.equal(withDest.trip_facts.itinerary[0].overnight, 'Hue');

    // 2. Changing accommodation cascades to Day 2 if same destination
    const withHotel = patchItineraryDayInFacts(facts, 0, {
      accommodation_id: 'hotel-metropole',
      accommodation_name: 'Sofitel Legend Metropole',
      room_type: 'Luxury Room',
    });
    assert.equal(withHotel.trip_facts.itinerary[0].accommodation_id, 'hotel-metropole');
    assert.equal(withHotel.trip_facts.itinerary[1].accommodation_id, 'hotel-metropole');
    assert.equal(withHotel.service_facts.hotels.length, 1);
    assert.equal(withHotel.service_facts.hotels[0].name, 'Sofitel Legend Metropole');
  });

  it('addHotelToFacts and removeHotelFromFacts maintain stays synchronization', () => {
    const facts = createBrochureFacts();
    facts.trip_facts.start_date = '2026-10-01';
    facts.trip_facts.itinerary = [
      {
        day_number: 1,
        destination: 'Hanoi',
        destination_ref: null,
        overnight: 'Hanoi',
        display_date: '01 Oct',
        summary: 'Arrival',
        meals: ['Breakfast'],
        highlights: [],
        notes: [],
        sense_of_pace: 'balanced',
        accommodation_id: null,
        accommodation_name: null,
        room_type: null,
      },
    ];

    // 1. Add hotel
    const withHotel = addHotelToFacts(facts);
    assert.equal(withHotel.service_facts.hotels.length, 1);
    assert.equal(withHotel.service_facts.hotels[0].check_in, '2026-10-01');
    assert.equal(withHotel.service_facts.hotels[0].check_out, '2026-10-02');

    // 2. Remove hotel
    const withoutHotel = removeHotelFromFacts(withHotel, 0);
    assert.equal(withoutHotel.service_facts.hotels.length, 0);
  });
});

