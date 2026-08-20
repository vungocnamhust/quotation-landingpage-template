import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  contentReconciler,
  validatePdfTextBudget,
  deriveDefaultCandidate,
  reconcileCandidateWithFacts,
  checkDocumentPdfTextBudgets,
} from '../rules/contentReconciler.ts';
import { contentAdapter } from '../rules/contentAdapter.ts';
import type { CanonicalTrip } from '../rules/tripReconciler.ts';

describe('contentReconciler pure domain rules', () => {
  it('exposes facade object with all expected domain functions', () => {
    assert.equal(typeof contentReconciler.validatePdfTextBudget, 'function');
    assert.equal(typeof contentReconciler.deriveDefaultCandidate, 'function');
    assert.equal(typeof contentReconciler.reconcileCandidateWithFacts, 'function');
    assert.equal(typeof contentReconciler.checkDocumentPdfTextBudgets, 'function');
  });

  describe('validatePdfTextBudget A4 printable constraints', () => {
    it('validates day title within 170 characters budget', () => {
      const validTitle = 'Day 1 · Welcome to Hanoi and Historic Old Quarter Highlights';
      const result = validatePdfTextBudget('day_title', validTitle);
      assert.equal(result.isValid, true);
      assert.equal(result.max, 170);
      assert.equal(result.overflow, 0);
      assert.equal(result.current, validTitle.length);

      const exact170 = 'A'.repeat(170);
      const exactResult = validatePdfTextBudget('day_title', exact170);
      assert.equal(exactResult.isValid, true);
      assert.equal(exactResult.overflow, 0);

      const over170 = 'A'.repeat(171);
      const overResult = validatePdfTextBudget('day_title', over170);
      assert.equal(overResult.isValid, false);
      assert.equal(overResult.overflow, 1);
      assert.equal(overResult.current, 171);
    });

    it('validates day description within 1,150 characters budget', () => {
      const validText = 'Experience the timeless beauty of Halong Bay with a luxury cruise.';
      const res = validatePdfTextBudget('day_description', validText);
      assert.equal(res.isValid, true);
      assert.equal(res.max, 1150);
      assert.equal(res.overflow, 0);

      const exact1150 = 'X'.repeat(1150);
      assert.equal(validatePdfTextBudget('day_description', exact1150).isValid, true);

      const over1150 = 'X'.repeat(1155);
      const overRes = validatePdfTextBudget('day_description', over1150);
      assert.equal(overRes.isValid, false);
      assert.equal(overRes.overflow, 5);
      assert.equal(overRes.current, 1155);
    });

    it('handles string arrays by joining with space', () => {
      const paragraphs = ['First paragraph of day.', 'Second paragraph of day.'];
      const res = validatePdfTextBudget('day_description', paragraphs);
      assert.equal(res.isValid, true);
      assert.equal(res.current, 'First paragraph of day. Second paragraph of day.'.length);
    });

    it('handles null, undefined, and empty text gracefully', () => {
      assert.equal(validatePdfTextBudget('day_title', null).isValid, true);
      assert.equal(validatePdfTextBudget('day_title', undefined).isValid, true);
      assert.equal(validatePdfTextBudget('day_title', '').isValid, true);
    });

    it('validates hotel total copy within 2,100 characters', () => {
      const hotelCopy = 'Hotel de l\'Opera Hanoi offers boutique luxury in the heart of the capital.';
      const res = validatePdfTextBudget('hotel_total_copy', hotelCopy);
      assert.equal(res.isValid, true);
      assert.equal(res.max, 2100);

      const over2100 = 'H'.repeat(2150);
      const overRes = validatePdfTextBudget('hotel_total_copy', over2100);
      assert.equal(overRes.isValid, false);
      assert.equal(overRes.overflow, 50);
    });
  });

  describe('deriveDefaultCandidate multilingual generation', () => {
    const mockTrip: CanonicalTrip = {
      startDate: '2026-11-01',
      endDate: '2026-11-05',
      durationDays: 5,
      durationNights: 4,
      destinations: ['Hanoi', 'Halong Bay', 'Hue'],
      itinerary: [
        {
          day_number: 1,
          destination: 'Hanoi',
          overnight: 'Hanoi',
          display_date: 'Sun, 01 Nov',
          summary: 'Arrive in Hanoi and explore the French Quarter.',
          highlights: ['Old Quarter Walk', 'Street Food Tour'],
        },
        {
          day_number: 2,
          destination: 'Halong Bay',
          overnight: 'Halong Bay',
          display_date: 'Mon, 02 Nov',
          summary: 'Cruise along the limestone karsts.',
          highlights: ['Kayaking', 'Sunset Party'],
        },
      ],
      lang: 'en',
    };

    it('generates default candidate for hero scope in English, Vietnamese, and Arabic', () => {
      const heroEn = deriveDefaultCandidate('hero', mockTrip, 'en');
      assert.ok(typeof (heroEn.trip as Record<string, unknown>).title === 'string');
      assert.equal((heroEn.trip as Record<string, unknown>).title, 'Hanoi & Beyond');
      assert.equal((heroEn.narrative as Record<string, unknown>).coverKicker, 'JOURNEY OVERVIEW');
      assert.ok(((heroEn.narrative as Record<string, unknown>).heroMeta1 as string).includes('5 DAYS'));

      const heroVi = deriveDefaultCandidate('hero', mockTrip, 'vi');
      assert.equal((heroVi.narrative as Record<string, unknown>).coverKicker, 'TỔNG QUAN HÀNH TRÌNH');
      assert.ok(((heroVi.narrative as Record<string, unknown>).heroMeta1 as string).includes('5 NGÀY'));

      const heroAr = deriveDefaultCandidate('hero', mockTrip, 'ar');
      assert.equal((heroAr.narrative as Record<string, unknown>).coverKicker, 'نظرة عامة على الرحلة');
    });

    it('generates default candidate for route scope with segment descriptions aligned to destinations', () => {
      const routeCand = deriveDefaultCandidate('route', mockTrip, 'en');
      const routeObj = routeCand.route as Record<string, unknown>;
      assert.equal(routeObj.title, 'Your Journey, Mapped');
      assert.ok(Array.isArray(routeObj.mapSegmentDescriptions));
      assert.equal((routeObj.mapSegmentDescriptions as string[]).length, 3);
      assert.ok((routeObj.mapSegmentDescriptions as string[])[0].includes('Hanoi'));
    });

    it('generates default candidate for itinerary day scope', () => {
      const day1Cand = deriveDefaultCandidate('itinerary:day:1', mockTrip, 'en');
      assert.equal(day1Cand.dayNumber, 1);
      assert.equal(day1Cand.title, 'Day 1 · Hanoi');
      assert.deepEqual(day1Cand.description, ['Arrive in Hanoi and explore the French Quarter.']);
      assert.deepEqual(day1Cand.activities, ['Old Quarter Walk', 'Street Food Tour']);

      const day1Vi = deriveDefaultCandidate('itinerary:day:1', mockTrip, 'vi');
      assert.equal(day1Vi.title, 'Ngày 1 · Hanoi');
    });
  });

  describe('reconcileCandidateWithFacts alignment invariants', () => {
    const mockTrip: CanonicalTrip = {
      startDate: '2026-11-01',
      endDate: '2026-11-04',
      durationDays: 4,
      durationNights: 3,
      destinations: ['Hanoi', 'Ninh Binh', 'Halong Bay'],
      itinerary: [
        { day_number: 1, destination: 'Hanoi', overnight: 'Hanoi', display_date: '01 Nov', summary: 'Hanoi day 1' },
        { day_number: 2, destination: 'Ninh Binh', overnight: 'Ninh Binh', display_date: '02 Nov', summary: 'Ninh Binh day 2' },
        { day_number: 3, destination: 'Halong Bay', overnight: 'Halong Bay', display_date: '03 Nov', summary: 'Halong day 3' },
      ],
      lang: 'en',
    };

    it('preserves existing custom segment descriptions while padding newly added destinations', () => {
      const partialCandidate = {
        route: {
          title: 'Custom Route Title',
          description: 'Custom narrative description',
          mapSegmentDescriptions: ['Custom description for Hanoi.'],
        },
      };

      const reconciled = reconcileCandidateWithFacts('route', partialCandidate, mockTrip, 'en');
      const route = reconciled.route as Record<string, unknown>;
      assert.equal(route.title, 'Custom Route Title');
      assert.equal(route.description, 'Custom narrative description');

      const descriptions = route.mapSegmentDescriptions as string[];
      assert.equal(descriptions.length, 3);
      assert.equal(descriptions[0], 'Custom description for Hanoi.'); // Preserved!
      assert.ok(descriptions[1].includes('Ninh Binh')); // Padded default for Ninh Binh
      assert.ok(descriptions[2].includes('Halong Bay')); // Padded default for Halong Bay
    });

    it('reconciles day candidates with day facts', () => {
      const candidate = {
        title: 'Custom Day 2 Name',
        description: ['Custom day text'],
      };

      const reconciled = reconcileCandidateWithFacts('itinerary:day:2', candidate, mockTrip, 'en');
      assert.equal(reconciled.dayNumber, 2);
      assert.equal(reconciled.title, 'Custom Day 2 Name');
      assert.deepEqual(reconciled.description, ['Custom day text']);
    });
  });

  describe('checkDocumentPdfTextBudgets scanner', () => {
    it('detects violations in invalid documents', () => {
      const doc = {
        itinerary: {
          days: [
            { dayNumber: 1, title: 'Short Title', description: ['Valid description'] },
            { dayNumber: 2, title: 'T'.repeat(200), description: ['D'.repeat(1200)] },
          ],
        },
        stays: {
          hotels: [
            { name: 'Hotel 1', intro: 'Short intro' },
          ],
        },
      };

      const violations = checkDocumentPdfTextBudgets(doc);
      assert.equal(violations.length, 2);
      assert.equal(violations[0].path, '/itinerary/days/1/title');
      assert.equal(violations[0].result.overflow, 30);
      assert.equal(violations[1].path, '/itinerary/days/1/description');
      assert.equal(violations[1].result.overflow, 50);
    });
  });
});

describe('contentAdapter bidirectional mapping', () => {
  it('converts DocumentResponse to CanonicalContentState and back losslessly', () => {
    const docResponse = {
      currentRevision: 3,
      contentEditorState: {
        hero: {
          trip: { title: 'Grand Tour of Vietnam' },
        },
        route: {
          route: { title: 'Mapped Route' },
        },
      },
    };

    const canonical = contentAdapter.fromDocumentResponse(docResponse);
    assert.ok(canonical.scopes.hero);
    assert.equal((canonical.scopes.hero.candidate.trip as Record<string, unknown>).title, 'Grand Tour of Vietnam');

    const synced = contentAdapter.syncToContentEditorState(canonical);
    assert.deepEqual(synced, docResponse.contentEditorState);
  });

  it('merges candidates into complete document without corrupting untouched sections', () => {
    const document = {
      trip: { title: 'Old Title', priceBasis: 'USD' },
      itinerary: { days: [{ dayNumber: 1, title: 'Old Day 1', description: [] }] },
      presentation: { themeId: 'brochure' },
    };

    const merged = contentAdapter.mergeCandidateWithDocument(document, 'hero', {
      trip: { title: 'New Grand Journey' },
    });

    assert.equal((merged.trip as Record<string, unknown>).title, 'New Grand Journey');
    assert.equal((merged.trip as Record<string, unknown>).priceBasis, 'USD'); // Untouched!
    assert.equal((merged.presentation as Record<string, unknown>).themeId, 'brochure'); // Untouched!
  });
});
