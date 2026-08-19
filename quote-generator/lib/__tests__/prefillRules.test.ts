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
} from '../prefillRules';
import {
  createBrochureFacts,
} from '../../components/quotation-workspace/factsTypes';
import {
  updateCustomerName,
  updateCustomerCounts,
  createItineraryDayWithDefaults,
} from '../prefillEngine';

describe('prefillRules pure business rules', () => {
  describe('inferGreetingName', () => {
    it('extracts first name from full name', () => {
      assert.equal(inferGreetingName('John Smith'), 'John');
      assert.equal(inferGreetingName('Nguyen Van A'), 'Nguyen');
    });

    it('returns empty string or null for empty name', () => {
      assert.equal(inferGreetingName(''), '');
      assert.equal(inferGreetingName(null), null);
    });
  });

  describe('inferPartyLabel', () => {
    it('formats party label based on customer name and headcounts', () => {
      assert.equal(inferPartyLabel('Smith', 2, 0), 'The Smith Party');
      assert.equal(inferPartyLabel('John Smith', 2, 2), 'The Smith Family');
    });

    it('handles fallback when name is missing', () => {
      assert.equal(inferPartyLabel(null, 1, 0), 'Solo Traveller');
      assert.equal(inferPartyLabel(null, 2, 0), 'Travelling Couple');
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
      assert.deepEqual(getDefaultMealsForLang('en'), ['B']);
      assert.deepEqual(getDefaultMealsForLang('vi'), ['S']);
      assert.deepEqual(getDefaultMealsForLang('ar'), ['إ']);
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
      const segments = deriveStaySegmentsFromItinerary(days as any, '2026-10-01', '2026-10-04');
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
      // 2 adults ($100 each), 1 child ($50 each)
      const total = inferCommercialTotal(10000, 5000, 2, 1);
      assert.equal(total, 25000);
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
    assert.equal(updated.customer_facts.greeting_name, 'David');
    assert.equal(updated.customer_facts.party_label, 'The Miller Party');
  });

  it('updateCustomerCounts updates party label when counts change', () => {
    const initialFacts = createBrochureFacts();
    const withName = updateCustomerName(initialFacts, 'David Miller');
    const withFamily = updateCustomerCounts(withName, { adults: 2, children: 2 });
    assert.equal(withFamily.customer_facts.adults, 2);
    assert.equal(withFamily.customer_facts.children, 2);
    assert.equal(withFamily.customer_facts.party_label, 'The Miller Family');
  });

  it('createItineraryDayWithDefaults sets localized meal defaults', () => {
    const dayVi = createItineraryDayWithDefaults({ index: 0, startDate: '2026-10-01', lang: 'vi' });
    assert.deepEqual(dayVi.meals, ['S']);

    const dayEn = createItineraryDayWithDefaults({ index: 0, startDate: '2026-10-01', lang: 'en' });
    assert.deepEqual(dayEn.meals, ['B']);
  });
});
