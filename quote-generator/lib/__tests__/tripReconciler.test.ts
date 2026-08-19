import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { tripReconciler, type CanonicalTrip } from '../rules/tripReconciler.ts';
import { tripAdapter } from '../rules/tripAdapter.ts';
import { getInitialQuoteRequestFormState } from '../quoteRequestPayload.ts';
import { createBrochureFacts } from '../../components/quotation-workspace/factsTypes.ts';

describe('tripReconciler temporal invariant rules', () => {
  describe('addDay', () => {
    it('initializes day 1 with matching endDate when startDate is set', () => {
      const initial: CanonicalTrip = {
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
      assert.equal(withDay1.itinerary[0].destination, 'Hanoi');
      assert.equal(withDay1.itinerary[0].overnight, 'Hanoi');
    });

    it('pushes endDate by 1 day for each additional day', () => {
      const initial: CanonicalTrip = {
        startDate: '2026-11-01',
        endDate: '2026-11-01',
        durationDays: 1,
        durationNights: 0,
        itinerary: [
          {
            day_number: 1,
            destination: 'Hanoi',
            overnight: 'Hanoi',
            display_date: 'Sun, 01 Nov',
            summary: null,
          },
        ],
      };

      const withDay2 = tripReconciler.addDay(initial, { destination: 'Hanoi' });
      assert.equal(withDay2.itinerary.length, 2);
      assert.equal(withDay2.endDate, '2026-11-02');
      assert.equal(withDay2.durationDays, 2);
      assert.equal(withDay2.durationNights, 1);
      assert.equal(withDay2.itinerary[1].day_number, 2);
    });

    it('auto-inherits hotel from previous day if same destination', () => {
      const initial: CanonicalTrip = {
        startDate: '2026-11-01',
        endDate: '2026-11-01',
        durationDays: 1,
        durationNights: 0,
        itinerary: [
          {
            day_number: 1,
            destination: 'Hanoi',
            overnight: 'Hanoi',
            display_date: 'Sun, 01 Nov',
            summary: null,
            accommodation_id: 'hotel-metropole',
            accommodation_name: 'Sofitel Legend Metropole',
            room_type: 'Grand Luxury Suite',
          },
        ],
      };

      const withDay2 = tripReconciler.addDay(initial, { destination: 'Hanoi' });
      assert.equal(withDay2.itinerary[1].accommodation_id, 'hotel-metropole');
      assert.equal(withDay2.itinerary[1].accommodation_name, 'Sofitel Legend Metropole');
    });
  });

  describe('removeDay', () => {
    it('pulls back endDate by 1 day and re-indexes days', () => {
      const initial: CanonicalTrip = {
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

      // Remove middle day (Halong)
      const afterRemove = tripReconciler.removeDay(initial, 1);
      assert.equal(afterRemove.itinerary.length, 2);
      assert.equal(afterRemove.endDate, '2026-11-02');
      assert.equal(afterRemove.durationDays, 2);
      assert.equal(afterRemove.durationNights, 1);
      assert.equal(afterRemove.itinerary[0].day_number, 1);
      assert.equal(afterRemove.itinerary[0].destination, 'Hanoi');
      assert.equal(afterRemove.itinerary[1].day_number, 2);
      assert.equal(afterRemove.itinerary[1].destination, 'Hue');
    });
  });

  describe('setStartDate', () => {
    it('shifts all display dates and updates endDate preserving duration', () => {
      const initial: CanonicalTrip = {
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
  });

  describe('setEndDate', () => {
    it('expands itinerary days when endDate is extended', () => {
      const initial: CanonicalTrip = {
        startDate: '2026-11-01',
        endDate: '2026-11-02',
        durationDays: 2,
        durationNights: 1,
        itinerary: [
          { day_number: 1, destination: 'Hanoi', overnight: 'Hanoi', display_date: null, summary: null },
          { day_number: 2, destination: 'Halong', overnight: 'Halong', display_date: null, summary: null },
        ],
      };

      const extended = tripReconciler.setEndDate(initial, '2026-11-04');
      assert.equal(extended.durationDays, 4);
      assert.equal(extended.durationNights, 3);
      assert.equal(extended.itinerary.length, 4);
      assert.equal(extended.itinerary[2].day_number, 3);
      assert.equal(extended.itinerary[3].day_number, 4);
    });

    it('truncates itinerary days when endDate is shortened', () => {
      const initial: CanonicalTrip = {
        startDate: '2026-11-01',
        endDate: '2026-11-05',
        durationDays: 5,
        durationNights: 4,
        itinerary: [
          { day_number: 1, destination: 'Hanoi', overnight: 'Hanoi', display_date: null, summary: null },
          { day_number: 2, destination: 'Hanoi', overnight: 'Hanoi', display_date: null, summary: null },
          { day_number: 3, destination: 'Halong', overnight: 'Halong', display_date: null, summary: null },
          { day_number: 4, destination: 'Hue', overnight: 'Hue', display_date: null, summary: null },
          { day_number: 5, destination: 'Hoi An', overnight: 'Hoi An', display_date: null, summary: null },
        ],
      };

      const shortened = tripReconciler.setEndDate(initial, '2026-11-03');
      assert.equal(shortened.durationDays, 3);
      assert.equal(shortened.durationNights, 2);
      assert.equal(shortened.itinerary.length, 3);
    });
  });

  describe('updateDay smart cascade', () => {
    it('cascades hotel change to contiguous subsequent days with same destination', () => {
      const initial: CanonicalTrip = {
        startDate: '2026-11-01',
        endDate: '2026-11-04',
        durationDays: 4,
        durationNights: 3,
        itinerary: [
          { day_number: 1, destination: 'Hanoi', overnight: 'Hanoi', display_date: null, summary: null },
          { day_number: 2, destination: 'Hanoi', overnight: 'Hanoi', display_date: null, summary: null },
          { day_number: 3, destination: 'Hanoi', overnight: 'Hanoi', display_date: null, summary: null },
          { day_number: 4, destination: 'Hue', overnight: 'Hue', display_date: null, summary: null },
        ],
      };

      const updated = tripReconciler.updateDay(initial, 0, {
        accommodation_id: 'hotel-metropole',
        accommodation_name: 'Sofitel Metropole',
        room_type: 'Luxury Room',
      });

      assert.equal(updated.itinerary[0].accommodation_id, 'hotel-metropole');
      assert.equal(updated.itinerary[1].accommodation_id, 'hotel-metropole');
      assert.equal(updated.itinerary[2].accommodation_id, 'hotel-metropole');
      // Day 4 is Hue -> not affected
      assert.equal(updated.itinerary[3].accommodation_id, null);
    });
  });
});

describe('tripAdapter bidirectional schema mapping', () => {
  it('adapts QuoteRequestFormState back and forth with CanonicalTrip', () => {
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
    assert.equal(canonical.itinerary.length, 3);

    // Add a day via reconciler
    const expanded = tripReconciler.addDay(canonical, { destination: 'Hue' });
    const synced = tripAdapter.syncToQuoteRequest(expanded, formState);

    assert.equal(synced.formState.arrival_date, '2026-11-01');
    assert.equal(synced.formState.departure_date, '2026-11-04');
    assert.equal(synced.itineraryDays.length, 4);
    assert.equal(synced.itineraryDays[3].day_number, 4);
    assert.equal(synced.itineraryDays[3].destination, 'Hue');
  });

  it('adapts QuotationFacts back and forth with CanonicalTrip', () => {
    const facts = createBrochureFacts();
    facts.trip_facts.start_date = '2026-10-01';
    facts.trip_facts.end_date = '2026-10-02';
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
        destination: 'Halong',
        destination_ref: null,
        overnight: 'Halong',
        display_date: '02 Oct',
        summary: 'Cruise',
        meals: ['Breakfast'],
        highlights: [],
        notes: [],
        sense_of_pace: 'balanced',
        accommodation_id: null,
        accommodation_name: null,
        room_type: null,
      },
    ];

    const canonical = tripAdapter.fromQuotationFacts(facts);
    assert.equal(canonical.startDate, '2026-10-01');
    assert.equal(canonical.endDate, '2026-10-02');
    assert.equal(canonical.durationDays, 2);

    const added = tripReconciler.addDay(canonical, { destination: 'Ninh Binh' });
    const updatedFacts = tripAdapter.syncToQuotationFacts(added, facts);

    assert.equal(updatedFacts.trip_facts.start_date, '2026-10-01');
    assert.equal(updatedFacts.trip_facts.end_date, '2026-10-03');
    assert.equal(updatedFacts.trip_facts.duration_days, 3);
    assert.equal(updatedFacts.trip_facts.itinerary.length, 3);
    assert.equal(updatedFacts.trip_facts.itinerary[2].destination, 'Ninh Binh');
    assert.deepEqual(updatedFacts.trip_facts.destinations, ['Hanoi', 'Halong', 'Ninh Binh']);
  });
});
