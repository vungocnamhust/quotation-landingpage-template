import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { tripAdapter } from '../rules/tripAdapter.ts';
import { tripReconciler } from '../rules/tripReconciler.ts';
import { ensureFactsDefaults, type QuotationFacts } from '../../components/quotation-workspace/factsTypes.ts';
import { buildInitialFactsFromRequest } from '../requestToFactsHandoff.ts';
import type { QuoteRequestItem } from '../../components/quotation-workspace/factsTypes.ts';

describe('Daily Programme 4-Layer Round-Trip Data Integrity', () => {
  it('preserves title, meals, highlights, notes, sense_of_pace, and display_date across tripAdapter', () => {
    const initialFacts: QuotationFacts = ensureFactsDefaults({
      trip_facts: {
        start_date: '2026-09-26',
        end_date: '2026-09-28',
        duration_days: 3,
        duration_nights: 2,
        destinations: ['Ho Chi Minh City', 'Mekong Delta'],
        itinerary: [
          {
            id: 'day-1',
            day_number: 1,
            title: 'Arrival in Saigon & Street Food Tour',
            destination: 'Ho Chi Minh City',
            overnight: 'Ho Chi Minh City',
            summary: 'Tham quan nhà thờ đức bà, bưu điện sài gòn, dinh độc lập',
            highlights: ['Notre Dame Cathedral', 'Central Post Office', 'Street Food Tasting'],
            meals: ['Breakfast', 'Dinner'],
            notes: ['Guide pick up at 08:30 AM'],
            sense_of_pace: 'relaxed',
            display_date: 'Sat, 26 Sep 2026',
            accommodation_id: 'acc-caravelle',
            accommodation_name: 'Caravelle Saigon',
            room_type: 'Opera Room',
          },
        ],
      },
    });

    // Layer 2: QuotationFacts -> CanonicalTrip
    const canonical = tripAdapter.fromQuotationFacts(initialFacts);
    assert.equal(canonical.itinerary[0].title, 'Arrival in Saigon & Street Food Tour');
    assert.deepEqual(canonical.itinerary[0].highlights, ['Notre Dame Cathedral', 'Central Post Office', 'Street Food Tasting']);
    assert.deepEqual(canonical.itinerary[0].meals, ['Breakfast', 'Dinner']);
    assert.deepEqual(canonical.itinerary[0].notes, ['Guide pick up at 08:30 AM']);
    assert.equal(canonical.itinerary[0].sense_of_pace, 'relaxed');
    assert.equal(canonical.itinerary[0].accommodation_name, 'Caravelle Saigon');

    // Layer 1: Reconcile (e.g. update destination or add day)
    const updated = tripReconciler.updateDay(canonical, 0, {
      title: 'Arrival in Saigon & Historic Landmarks Tour',
    });
    assert.equal(updated.itinerary[0].title, 'Arrival in Saigon & Historic Landmarks Tour');
    assert.deepEqual(updated.itinerary[0].highlights, ['Notre Dame Cathedral', 'Central Post Office', 'Street Food Tasting']);

    // Layer 2: CanonicalTrip -> QuotationFacts
    const synced = tripAdapter.syncToQuotationFacts(updated, initialFacts);
    const day0 = synced.trip_facts.itinerary[0];
    assert.equal(day0.title, 'Arrival in Saigon & Historic Landmarks Tour');
    assert.deepEqual(day0.highlights, ['Notre Dame Cathedral', 'Central Post Office', 'Street Food Tasting']);
    assert.deepEqual(day0.meals, ['Breakfast', 'Dinner']);
    assert.deepEqual(day0.notes, ['Guide pick up at 08:30 AM']);
    assert.equal(day0.sense_of_pace, 'relaxed');
    assert.equal(day0.accommodation_name, 'Caravelle Saigon');
    assert.equal(day0.room_type, 'Opera Room');
  });

  it('preserves full day fields in buildInitialFactsFromRequest handoff', () => {
    const mockRequest: QuoteRequestItem = {
      id: 'req-123',
      customer_name: 'John Doe',
      start_date: '2026-09-26',
      end_date: '2026-09-28',
      destinations: ['Ho Chi Minh City'],
      payload_json: {
        itinerary_days: [
          {
            day_number: 1,
            title: 'Welcome to Saigon',
            destination: 'Ho Chi Minh City',
            summary: 'City sights and orientation',
            highlights: ['War Remnants Museum', 'Ben Thanh Market'],
            meals: ['Breakfast', 'Lunch'],
            notes: ['Private vehicle provided'],
            sense_of_pace: 'fast',
            display_date: '26 Sep 2026',
          },
        ],
      },
    };

    const fallback = ensureFactsDefaults();
    const facts = buildInitialFactsFromRequest(mockRequest, fallback);
    const day = facts.trip_facts.itinerary[0];

    assert.equal(day.title, 'Welcome to Saigon');
    assert.equal(day.destination, 'Ho Chi Minh City');
    assert.equal(day.summary, 'City sights and orientation');
    assert.deepEqual(day.highlights, ['War Remnants Museum', 'Ben Thanh Market']);
    assert.deepEqual(day.meals, ['Breakfast', 'Lunch']);
    assert.deepEqual(day.notes, ['Private vehicle provided']);
    assert.equal(day.sense_of_pace, 'fast');
  });
});
