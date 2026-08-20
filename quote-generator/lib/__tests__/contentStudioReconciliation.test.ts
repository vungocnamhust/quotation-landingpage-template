import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  contentReconciler,
  deriveBudgetType,
  validatePdfTextBudget,
} from '../rules/contentReconciler.ts';
import {
  emptyFacts,
  type QuotationFacts,
} from '../../components/quotation-workspace/factsTypes.ts';

describe('Content Studio Reconciliation & Live A4 Character Budget', () => {
  const baseFacts: QuotationFacts = {
    ...emptyFacts(),
    customer_facts: {
      ...emptyFacts().customer_facts,
      customer_name: 'Alice Wonder',
    },
    trip_facts: {
      ...emptyFacts().trip_facts,
      destinations: ['Hanoi', 'Ninh Binh', 'Halong Bay', 'Hue'],
      start_date: '2026-10-01',
      end_date: '2026-10-04',
      duration_days: 4,
      duration_nights: 3,
      itinerary: [
        {
          day_number: 1,
          destination: 'Hanoi',
          overnight: 'Hanoi',
          meals: ['Breakfast'],
          highlights: ['Old Quarter walk'],
          notes: [],
          sense_of_pace: 'balanced',
          display_date: 'Thu, 01 Oct',
        },
        {
          day_number: 2,
          destination: 'Ninh Binh',
          overnight: 'Ninh Binh',
          meals: ['Breakfast', 'Lunch'],
          highlights: ['Trang An boat trip'],
          notes: [],
          sense_of_pace: 'balanced',
          display_date: 'Fri, 02 Oct',
        },
        {
          day_number: 3,
          destination: 'Halong Bay',
          overnight: 'Halong Bay',
          meals: ['Breakfast', 'Lunch', 'Dinner'],
          highlights: ['Overnight Cruise'],
          notes: [],
          sense_of_pace: 'balanced',
          display_date: 'Sat, 03 Oct',
        },
        {
          day_number: 4,
          destination: 'Hue',
          overnight: 'Hue',
          meals: ['Breakfast'],
          highlights: ['Imperial Citadel'],
          notes: [],
          sense_of_pace: 'balanced',
          display_date: 'Sun, 04 Oct',
        },
      ],
    },
  };

  describe('Route Stops alignment with Facts', () => {
    it('reconciles candidate mapSegmentDescriptions to exactly match 4 stops from Facts', () => {
      // Suppose candidate originally had only 2 descriptions
      const existingCandidate = {
        route: {
          title: 'Vietnam Discovery Route',
          description: 'A journey across historic cities.',
          mapSegmentDescriptions: [
            'Hanoi: Explore the vibrant streets and bustling colonial quarter.',
            'Ninh Binh: Limestone karsts rising majestically from rice paddies.',
          ],
        },
      };

      const reconciled = contentReconciler.reconcileCandidateWithFacts(
        'route',
        existingCandidate,
        baseFacts,
        'en'
      );

      const routeObj = reconciled.route as {
        title: string;
        description: string;
        mapSegmentDescriptions: string[];
      };

      assert.equal(routeObj.title, 'Vietnam Discovery Route');
      assert.equal(routeObj.description, 'A journey across historic cities.');
      // Should now have exactly 4 stop descriptions
      assert.equal(routeObj.mapSegmentDescriptions.length, 4);
      // Existing 2 descriptions are preserved verbatim
      assert.equal(
        routeObj.mapSegmentDescriptions[0],
        'Hanoi: Explore the vibrant streets and bustling colonial quarter.'
      );
      assert.equal(
        routeObj.mapSegmentDescriptions[1],
        'Ninh Binh: Limestone karsts rising majestically from rice paddies.'
      );
      // Stops 3 and 4 are safely populated from default activity summaries
      assert.ok(typeof routeObj.mapSegmentDescriptions[2] === 'string');
      assert.ok(typeof routeObj.mapSegmentDescriptions[3] === 'string');
    });

    it('derives default candidate for route when initial candidate is empty', () => {
      const defaultCandidate = contentReconciler.deriveDefaultCandidate(
        'route',
        baseFacts,
        'en'
      );

      const routeObj = defaultCandidate.route as {
        title: string;
        description: string;
        mapSegmentDescriptions: string[];
      };

      assert.ok(routeObj.title.length > 0);
      assert.ok(routeObj.description.length > 0);
      assert.equal(routeObj.mapSegmentDescriptions.length, 4);
    });
  });

  describe('Live A4 Character Budget Meter validation', () => {
    it('validates day_title budget (limit: 170 characters)', () => {
      const validTitle = 'Day 1: Arrival in Hanoi and Street Food Discovery';
      const checkValid = validatePdfTextBudget('day_title', validTitle);
      assert.equal(checkValid.isValid, true);
      assert.equal(checkValid.max, 170);
      assert.equal(checkValid.overflow, 0);

      const excessiveTitle = 'A'.repeat(200);
      const checkExcessive = validatePdfTextBudget('day_title', excessiveTitle);
      assert.equal(checkExcessive.isValid, false);
      assert.equal(checkExcessive.current, 200);
      assert.equal(checkExcessive.max, 170);
      assert.equal(checkExcessive.overflow, 30);
    });

    it('validates day_description budget (limit: 1,150 characters)', () => {
      const validDesc = 'Welcome to Hanoi! Today we explore the French Quarter and Old Quarter.';
      const checkValid = validatePdfTextBudget('day_description', validDesc);
      assert.equal(checkValid.isValid, true);
      assert.equal(checkValid.max, 1150);
      assert.equal(checkValid.overflow, 0);

      const excessiveDesc = 'B'.repeat(1200);
      const checkExcessive = validatePdfTextBudget('itinerary:day:description', excessiveDesc);
      assert.equal(checkExcessive.isValid, false);
      assert.equal(checkExcessive.current, 1200);
      assert.equal(checkExcessive.max, 1150);
      assert.equal(checkExcessive.overflow, 50);
    });

    it('validates route_stop_description budget (limit: 500 characters)', () => {
      const validStop = 'Halong Bay cruise through limestone islets.';
      const checkValid = validatePdfTextBudget('route_stop_description', validStop);
      assert.equal(checkValid.isValid, true);
      assert.equal(checkValid.max, 500);

      const excessiveStop = 'C'.repeat(550);
      const checkExcessive = validatePdfTextBudget('route_stop_description', excessiveStop);
      assert.equal(checkExcessive.isValid, false);
      assert.equal(checkExcessive.overflow, 50);
    });

    it('derives correct budget metric keys from scope and field info', () => {
      assert.equal(
        deriveBudgetType('itinerary:day:1', 'day-title', ['title']),
        'itinerary:day:title'
      );
      assert.equal(
        deriveBudgetType('itinerary:day:1', 'day-description', ['description']),
        'itinerary:day:description'
      );
      assert.equal(
        deriveBudgetType('route', 'route-stop-descriptions', ['route', 'mapSegmentDescriptions']),
        'route_stop_description'
      );
      assert.equal(
        deriveBudgetType('hero', 'hero-trip-title', ['trip', 'title']),
        'hero_title'
      );
      assert.equal(
        deriveBudgetType('hero', 'hero-trip-lede', ['trip', 'lede']),
        'hero_lede'
      );
      assert.equal(
        deriveBudgetType('hotel_plan', 'hotel-intro', ['intro']),
        'hotel_intro'
      );
    });
  });
});
