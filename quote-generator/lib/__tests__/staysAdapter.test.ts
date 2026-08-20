import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { staysAdapter } from '../rules/staysAdapter.ts';
import { staysReconciler } from '../rules/staysReconciler.ts';
import { createBrochureFacts } from '../../components/quotation-workspace/factsTypes.ts';

describe('staysAdapter bidirectional schema mapping', () => {
  it('adapts QuotationFacts back and forth with CanonicalTripWithStays', () => {
    const facts = createBrochureFacts();
    facts.trip_facts.start_date = '2026-11-01';
    facts.trip_facts.end_date = '2026-11-04';
    facts.trip_facts.itinerary = [
      {
        day_number: 1,
        destination: 'Hanoi',
        destination_ref: null,
        overnight: 'Hanoi',
        display_date: '01 Nov',
        summary: 'Arrival',
        meals: ['Breakfast'],
        highlights: [],
        notes: [],
        sense_of_pace: 'balanced',
        accommodation_id: 'hotel-metropole',
        accommodation_name: 'Sofitel Legend Metropole',
        room_type: 'Grand Luxury',
      },
      {
        day_number: 2,
        destination: 'Hanoi',
        destination_ref: null,
        overnight: 'Hanoi',
        display_date: '02 Nov',
        summary: 'City tour',
        meals: ['Breakfast'],
        highlights: [],
        notes: [],
        sense_of_pace: 'balanced',
        accommodation_id: 'hotel-metropole',
        accommodation_name: 'Sofitel Legend Metropole',
        room_type: 'Grand Luxury',
      },
      {
        day_number: 3,
        destination: 'Halong',
        destination_ref: null,
        overnight: 'Halong',
        display_date: '03 Nov',
        summary: 'Cruise',
        meals: ['Breakfast'],
        highlights: [],
        notes: [],
        sense_of_pace: 'balanced',
        accommodation_id: 'cruise-paradise',
        accommodation_name: 'Paradise Elegance Cruise',
        room_type: 'Executive Cabin',
      },
    ];

    const canonical = staysAdapter.fromQuotationFacts(facts);
    assert.equal(canonical.startDate, '2026-11-01');
    assert.equal(canonical.stays.length, 2);

    // Stay 1: Hanoi Metropole (2 nights)
    assert.equal(canonical.stays[0].name, 'Sofitel Legend Metropole');
    assert.equal(canonical.stays[0].nights, 2);
    assert.equal(canonical.stays[0].check_in, '2026-11-01');
    assert.equal(canonical.stays[0].check_out, '2026-11-03');

    // Stay 2: Halong Cruise (1 night)
    assert.equal(canonical.stays[1].name, 'Paradise Elegance Cruise');
    assert.equal(canonical.stays[1].nights, 1);
    assert.equal(canonical.stays[1].check_in, '2026-11-03');
    assert.equal(canonical.stays[1].check_out, '2026-11-04');

    // Shift trip dates via staysReconciler
    const shiftedStays = staysReconciler.shiftStayDates(canonical.stays, '2026-12-01', canonical.itinerary);
    const updatedCanonical = {
      ...canonical,
      startDate: '2026-12-01',
      endDate: '2026-12-04',
      stays: shiftedStays,
    };

    const syncedFacts = staysAdapter.syncToQuotationFacts(updatedCanonical, facts);
    assert.equal(syncedFacts.trip_facts.start_date, '2026-12-01');
    assert.equal(syncedFacts.service_facts.hotels.length, 2);
    assert.equal(syncedFacts.service_facts.hotels[0].check_in, '2026-12-01');
    assert.equal(syncedFacts.service_facts.hotels[0].check_out, '2026-12-03');
    assert.equal(syncedFacts.service_facts.hotels[1].check_in, '2026-12-03');
    assert.equal(syncedFacts.service_facts.hotels[1].check_out, '2026-12-04');
  });

  it('handles land-only tour without hotel bookings cleanly', () => {
    const facts = createBrochureFacts();
    facts.trip_facts.start_date = '2026-11-01';
    facts.trip_facts.end_date = '2026-11-03';
    facts.trip_facts.itinerary = [
      {
        day_number: 1,
        destination: 'Hanoi',
        destination_ref: null,
        overnight: 'Hanoi',
        display_date: '01 Nov',
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

    const canonical = staysAdapter.fromQuotationFacts(facts);
    assert.equal(canonical.stays.length, 0);

    const synced = staysAdapter.syncToQuotationFacts(canonical, facts);
    assert.equal(synced.service_facts.hotels.length, 0);
  });
});
