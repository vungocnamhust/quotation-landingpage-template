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
  createItineraryDayWithDefaults,
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

  it('updateCustomerCounts updates party label when counts change', () => {
    const initialFacts = createBrochureFacts();
    const withName = updateCustomerName(initialFacts, 'David Miller');
    const withFamily = updateCustomerCounts(withName, { adults: 2, children: 2 });
    assert.equal(withFamily.customer_facts.adults, 2);
    assert.equal(withFamily.customer_facts.children, 2);
    assert.equal(withFamily.customer_facts.party_label, 'David Miller & Party (2 Adults, 2 Children)');
  });

  it('createItineraryDayWithDefaults sets localized meal defaults', () => {
    const dayVi = createItineraryDayWithDefaults({ index: 0, startDate: '2026-10-01', lang: 'vi' });
    assert.deepEqual(dayVi.meals, ['Bữa sáng']);

    const dayEn = createItineraryDayWithDefaults({ index: 0, startDate: '2026-10-01', lang: 'en' });
    assert.deepEqual(dayEn.meals, ['Breakfast']);
  });
});
