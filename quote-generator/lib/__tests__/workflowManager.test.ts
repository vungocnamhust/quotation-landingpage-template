import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { isFactsEquivalent } from '../../components/quotation-workspace/useQuotationWorkflowManager.ts';
import {
  createItineraryDay,
  emptyFacts,
  ensureFactsDefaults,
  type QuotationFacts,
} from '../../components/quotation-workspace/factsTypes.ts';
import { tripAdapter } from '../rules/tripAdapter.ts';
import { tripReconciler } from '../rules/tripReconciler.ts';
import {
  addHotelToFacts,
  applyRouteDates,
  updateCustomerCounts,
  updateCustomerName,
  updateTravelStyle,
} from '../prefillEngine.ts';

describe('Workflow Manager & Dirty State Invariants', () => {
  const baseFacts: QuotationFacts = {
    ...emptyFacts(),
    customer_facts: {
      ...emptyFacts().customer_facts,
      customer_name: 'Jane Doe',
      adults: 2,
      children: 0,
      travel_style: 'Luxury',
      party_label: 'Jane Doe Party',
      greeting_name: 'Dear Jane',
    },
    trip_facts: {
      ...emptyFacts().trip_facts,
      destinations: ['Hanoi', 'Halong Bay'],
      start_date: '2026-11-01',
      end_date: '2026-11-03',
      duration_days: 3,
      duration_nights: 2,
      itinerary: [
        {
          id: 'day_1_fixed_uuid',
          day_number: 1,
          destination: 'Hanoi',
          overnight: 'Hanoi',
          meals: ['Breakfast'],
          highlights: ['Old Quarter'],
          notes: [],
          sense_of_pace: 'balanced',
          display_date: 'Sun, 01 Nov',
        },
        {
          id: 'day_2_fixed_uuid',
          day_number: 2,
          destination: 'Halong Bay',
          overnight: 'Halong Bay',
          meals: ['Breakfast', 'Lunch'],
          highlights: ['Cruise'],
          notes: [],
          sense_of_pace: 'balanced',
          display_date: 'Mon, 02 Nov',
        },
        {
          id: 'day_3_fixed_uuid',
          day_number: 3,
          destination: 'Hanoi',
          overnight: 'Hanoi',
          meals: ['Breakfast'],
          highlights: ['Departure'],
          notes: [],
          sense_of_pace: 'balanced',
          display_date: 'Tue, 03 Nov',
        },
      ],
    },
  };

  it('isFactsEquivalent returns true for identical objects', () => {
    assert.equal(isFactsEquivalent(baseFacts, baseFacts), true);
    assert.equal(isFactsEquivalent(baseFacts, { ...baseFacts }), true);
  });

  it('isFactsEquivalent returns false when customer or trip is modified', () => {
    const modifiedName = updateCustomerName(baseFacts, 'John Smith');
    assert.equal(isFactsEquivalent(baseFacts, modifiedName), false);

    const modifiedCounts = updateCustomerCounts(baseFacts, { adults: 4 });
    assert.equal(isFactsEquivalent(baseFacts, modifiedCounts), false);

    const modifiedStyle = updateTravelStyle(baseFacts, 'Adventure');
    assert.equal(isFactsEquivalent(baseFacts, modifiedStyle), false);
  });

  describe('Stable Entity IDs', () => {
    it('createItineraryDay assigns unique stable id to new day', () => {
      const day1 = createItineraryDay({ index: 0, startDate: '2026-11-01' });
      const day2 = createItineraryDay({ index: 1, startDate: '2026-11-01' });

      assert.ok(typeof day1.id === 'string' && day1.id.startsWith('day_1_'));
      assert.ok(typeof day2.id === 'string' && day2.id.startsWith('day_2_'));
      assert.notEqual(day1.id, day2.id);
    });

    it('ensureFactsDefaults guarantees stable entity id on days and hotels', () => {
      const partialFacts: QuotationFacts = {
        ...emptyFacts(),
        trip_facts: {
          ...emptyFacts().trip_facts,
          itinerary: [
            {
              day_number: 1,
              destination: 'Hanoi',
              overnight: 'Hanoi',
              meals: [],
              highlights: [],
              notes: [],
              sense_of_pace: null,
              display_date: null,
            },
          ],
        },
        service_facts: {
          ...emptyFacts().service_facts,
          hotels: [
            {
              accommodation_id: null,
              destination: 'Hanoi',
              name: 'Hotel Metropole',
              room_type: null,
              check_in: null,
              check_out: null,
              intro: null,
              phone: null,
              display_city: null,
              display_date: null,
              hotel_asset: null,
              room_asset: null,
            },
          ],
        },
      };

      const defaulted = ensureFactsDefaults(partialFacts);
      assert.ok(typeof defaulted.trip_facts.itinerary[0].id === 'string');
      assert.ok(typeof defaulted.service_facts.hotels[0].id === 'string');
    });

    it('removes day in middle while preserving stable entity ids and data of surrounding days', () => {
      const canonical = tripAdapter.fromQuotationFacts(baseFacts);
      assert.equal(canonical.itinerary.length, 3);
      assert.equal(canonical.itinerary[0].id, 'day_1_fixed_uuid');
      assert.equal(canonical.itinerary[1].id, 'day_2_fixed_uuid');
      assert.equal(canonical.itinerary[2].id, 'day_3_fixed_uuid');

      // Remove Day 2 (index 1)
      const reconciled = tripReconciler.removeDay(canonical, 1);
      assert.equal(reconciled.itinerary.length, 2);

      // Day 1 retains id and day_number 1
      assert.equal(reconciled.itinerary[0].id, 'day_1_fixed_uuid');
      assert.equal(reconciled.itinerary[0].day_number, 1);
      assert.equal(reconciled.itinerary[0].destination, 'Hanoi');

      // Previous Day 3 retains its id 'day_3_fixed_uuid' and its highlights, but re-indexes to day_number 2
      assert.equal(reconciled.itinerary[1].id, 'day_3_fixed_uuid');
      assert.equal(reconciled.itinerary[1].day_number, 2);
      assert.deepEqual(reconciled.itinerary[1].highlights, ['Departure']);
    });

    it('addDay adds a new day with distinct stable id without disturbing existing days', () => {
      const canonical = tripAdapter.fromQuotationFacts(baseFacts);
      const reconciled = tripReconciler.addDay(canonical);

      assert.equal(reconciled.itinerary.length, 4);
      assert.equal(reconciled.itinerary[0].id, 'day_1_fixed_uuid');
      assert.equal(reconciled.itinerary[1].id, 'day_2_fixed_uuid');
      assert.equal(reconciled.itinerary[2].id, 'day_3_fixed_uuid');
      assert.ok(typeof reconciled.itinerary[3].id === 'string');
      assert.notEqual(reconciled.itinerary[3].id, 'day_3_fixed_uuid');
    });

    it('addHotelToFacts assigns a stable id to the new hotel', () => {
      const updated = addHotelToFacts(baseFacts);
      assert.equal(updated.service_facts.hotels.length, 1);
      assert.ok(typeof updated.service_facts.hotels[0].id === 'string');
      assert.ok(updated.service_facts.hotels[0].id!.startsWith('hotel_new_'));
    });

    it('applyRouteDates shifts dates while preserving existing day ids and data', () => {
      const updated = applyRouteDates(baseFacts, '2026-12-01', '2026-12-03', 3);
      assert.equal(updated.trip_facts.itinerary.length, 3);
      assert.equal(updated.trip_facts.itinerary[0].id, 'day_1_fixed_uuid');
      assert.equal(updated.trip_facts.itinerary[1].id, 'day_2_fixed_uuid');
      assert.equal(updated.trip_facts.itinerary[2].id, 'day_3_fixed_uuid');
      assert.equal(updated.trip_facts.itinerary[0].display_date, '2026-12-01');
    });
  });
});
