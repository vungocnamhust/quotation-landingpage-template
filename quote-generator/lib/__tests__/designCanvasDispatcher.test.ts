import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { contentReconciler } from '../rules/contentReconciler.ts';

function setDocumentPath(
  document: Record<string, unknown>,
  source: string,
  value: unknown
): Record<string, unknown> {
  const parts = source.startsWith('/') ? source.slice(1).split('/') : source.split('.');
  const clone = JSON.parse(JSON.stringify(document)) as Record<string, unknown>;
  let cursor: Record<string, unknown> | unknown[] = clone;

  for (let i = 0; i < parts.length; i++) {
    const part = parts[i];
    const isLast = i === parts.length - 1;
    const nextPart = parts[i + 1];
    const nextIsNumeric = nextPart !== undefined && /^\d+$/.test(nextPart);
    const key = /^\d+$/.test(part) ? Number(part) : part;

    if (isLast) {
      (cursor as Record<string | number, unknown>)[key] = value;
    } else {
      const currentVal = (cursor as Record<string | number, unknown>)[key];
      if (currentVal === undefined || currentVal === null || typeof currentVal !== 'object') {
        (cursor as Record<string | number, unknown>)[key] = nextIsNumeric ? [] : {};
      }
      cursor = (cursor as Record<string | number, unknown>)[key] as Record<string, unknown> | unknown[];
    }
  }

  return clone;
}

function readDocumentPath(document: Record<string, unknown>, source: string): unknown {
  const parts = source.startsWith('/') ? source.slice(1).split('/') : source.split('.');
  let current: unknown = document;
  for (const part of parts) {
    if (!current || typeof current !== 'object') return undefined;
    const key = /^\d+$/.test(part) ? Number(part) : part;
    current = (current as Record<string | number, unknown>)[key];
  }
  return current;
}

describe('DesignCanvas Write-Target Dispatcher & Document Path Engine', () => {
  it('updates nested object properties immutably', () => {
    const originalDoc = {
      narrative: {
        letterIntro: 'Original letter intro',
        letterSignOff: 'Best regards',
      },
    };

    const nextDoc = setDocumentPath(originalDoc, '/narrative/letterIntro', 'Updated letter intro');

    assert.equal(originalDoc.narrative.letterIntro, 'Original letter intro');
    assert.equal((nextDoc.narrative as Record<string, unknown>).letterIntro, 'Updated letter intro');
    assert.equal((nextDoc.narrative as Record<string, unknown>).letterSignOff, 'Best regards');
  });

  it('updates nested array item properties immutably', () => {
    const originalDoc = {
      itinerary: {
        days: [
          { dayNumber: 1, title: 'Day 1: Arrival in Hanoi', description: ['Explore old quarter'] },
          { dayNumber: 2, title: 'Day 2: Hanoi to Ninh Binh', description: ['Boat tour in Trang An'] },
        ],
      },
    };

    const nextDoc = setDocumentPath(
      originalDoc,
      '/itinerary/days/0/title',
      'Day 1: Arrival & Welcome Dinner in Hanoi'
    ) as { itinerary: { days: Array<{ dayNumber: number; title: string; description: string[] }> } };

    assert.equal(originalDoc.itinerary.days[0].title, 'Day 1: Arrival in Hanoi');
    assert.equal(nextDoc.itinerary.days[0].title, 'Day 1: Arrival & Welcome Dinner in Hanoi');
    assert.equal(nextDoc.itinerary.days[1].title, 'Day 2: Hanoi to Ninh Binh');
  });

  it('updates indexed array element strings immutably', () => {
    const originalDoc = {
      itinerary: {
        days: [
          {
            dayNumber: 1,
            description: ['Visit the Temple of Literature', 'Walk around Hoan Kiem Lake'],
          },
        ],
      },
    };

    const nextDoc = setDocumentPath(
      originalDoc,
      '/itinerary/days/0/description/1',
      'Walk around Hoan Kiem Lake and sample street food'
    ) as { itinerary: { days: Array<{ dayNumber: number; description: string[] }> } };

    assert.equal(originalDoc.itinerary.days[0].description[1], 'Walk around Hoan Kiem Lake');
    assert.equal(
      nextDoc.itinerary.days[0].description[1],
      'Walk around Hoan Kiem Lake and sample street food'
    );
    assert.equal(nextDoc.itinerary.days[0].description[0], 'Visit the Temple of Literature');
  });

  it('reads values correctly from nested paths', () => {
    const doc = {
      hero: {
        bannerImage: {
          r2Key: 'media/hero-banner-123.jpg',
          source: 'manual',
        },
      },
      route: {
        staySegments: [
          {
            destinationName: 'Hanoi',
            mapSegmentDesc: 'Capital city with rich culture',
          },
        ],
      },
    };

    assert.equal(readDocumentPath(doc, '/hero/bannerImage/r2Key'), 'media/hero-banner-123.jpg');
    assert.equal(
      readDocumentPath(doc, '/route/staySegments/0/mapSegmentDesc'),
      'Capital city with rich culture'
    );
    assert.equal(readDocumentPath(doc, '/non/existent/path'), undefined);
  });

  it('derives budget types and validates live PDF character budgets in Inspector', () => {
    // 1. Day description budget (max 1150 chars)
    const dayBudgetType = contentReconciler.deriveBudgetType('itinerary:day:1', 'itinerary.days.0.description');
    assert.equal(dayBudgetType, 'itinerary:day:description');
    const withinBudget = contentReconciler.validatePdfTextBudget(dayBudgetType, 'Short summary within budget');
    assert.equal(withinBudget.overflow, 0);
    assert.equal(withinBudget.max, 1150);

    const longSummary = 'A'.repeat(1200);
    const overBudget = contentReconciler.validatePdfTextBudget(dayBudgetType, longSummary);
    assert.equal(overBudget.overflow, 50);
    assert.equal(overBudget.current, 1200);

    // 2. Day title budget (max 170 chars)
    const titleBudgetType = contentReconciler.deriveBudgetType('itinerary:day:1', 'itinerary.days.0.title');
    assert.equal(titleBudgetType, 'itinerary:day:title');
    const titleResult = contentReconciler.validatePdfTextBudget(titleBudgetType, 'A'.repeat(180));
    assert.equal(titleResult.overflow, 10);
    assert.equal(titleResult.max, 170);

    // 3. Hotel intro budget (max 300 chars)
    const hotelBudgetType = contentReconciler.deriveBudgetType('hotel_plan', 'stays.hotels.0.hotelIntro');
    assert.equal(hotelBudgetType, 'hotel_intro');
    const hotelResult = contentReconciler.validatePdfTextBudget(hotelBudgetType, 'A'.repeat(320));
    assert.equal(hotelResult.overflow, 20);
    assert.equal(hotelResult.max, 300);
  });
});
