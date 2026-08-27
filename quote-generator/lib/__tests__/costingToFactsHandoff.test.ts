import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { buildFactsFromCostingWorkbench } from '../costingToFactsHandoff.ts';
import { createItineraryDay, emptyFacts } from '../../components/quotation-workspace/factsTypes.ts';
import type { QuotationFacts } from '../../components/quotation-workspace/factsTypes.ts';
import type { CostingWorkbenchResponse, ServiceLineProfile } from '../quotationApi.ts';

function fallbackWithDays(count: number): QuotationFacts {
  const base = emptyFacts();
  const itinerary = Array.from({ length: count }, (_, i) => createItineraryDay({ index: i, startDate: '2026-05-01' }));
  return { ...base, trip_facts: { ...base.trip_facts, itinerary } };
}

function line(overrides: Partial<ServiceLineProfile>): ServiceLineProfile {
  return {
    id: 'csl_1',
    sheet_id: 'cst_1',
    day_number: 1,
    service_date: null,
    category: 'accommodation',
    subcategory: 'hotel',
    title: 'La Siesta Old Quarter',
    supplier_id: 'sup_1',
    product_id: 'prd_1',
    tariff_id: 'rat_1',
    price_line_id: 1,
    unit: 'room',
    time_basis: 'night',
    qty_unit: 1,
    qty_time: 1,
    unit_cost_minor: 1_000_000,
    cost_currency: 'USD',
    fx_rate_ppm: null,
    sell_override_minor: null,
    booking_status: 'quoted',
    source: 'manual',
    note: null,
    sort_order: 0,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    cost_minor: 1_000_000,
    sell_minor: 1_200_000,
    product_ref: null,
    ...overrides,
  };
}

function workbench(overrides: Partial<CostingWorkbenchResponse> = {}): CostingWorkbenchResponse {
  return {
    sheet: {
      id: 'cst_1',
      quote_request_id: 'req_1',
      quotation_id: null,
      currency: 'USD',
      markup_rate_bps: 1000,
      rounding_increment_minor: 0,
      costing_revision: 1,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
    items: [],
    summary: { cost_total_minor: 0, sell_total_minor: 0, margin_minor: 0, margin_bps: 0, by_day: [], by_category: [] },
    ...overrides,
  };
}

describe('costingToFactsHandoff', () => {
  it('returns fallback untouched when workbench is null/undefined', () => {
    const fallback = fallbackWithDays(2);
    assert.equal(buildFactsFromCostingWorkbench(null, fallback), fallback);
    assert.equal(buildFactsFromCostingWorkbench(undefined, fallback), fallback);
  });

  it('returns fallback untouched for an empty sheet (no lines)', () => {
    const fallback = fallbackWithDays(2);
    const result = buildFactsFromCostingWorkbench(workbench(), fallback);
    assert.deepEqual(result.trip_facts.itinerary, fallback.trip_facts.itinerary);
    assert.deepEqual(result.pricing_facts.options, []);
  });

  it('clusters a contiguous 2-night accommodation line into one stay', () => {
    const fallback = fallbackWithDays(3);
    const wb = workbench({
      items: [
        line({
          id: 'l1',
          day_number: 1,
          qty_time: 2,
          product_ref: { property_id: 'acc_1', destination_id: 'dst_1', destination_name: 'Hanoi', iata_code: 'HAN' },
        }),
      ],
      summary: { cost_total_minor: 2_000_000, sell_total_minor: 2_400_000, margin_minor: 400_000, margin_bps: 1667, by_day: [], by_category: [] },
    });
    const result = buildFactsFromCostingWorkbench(wb, fallback);

    assert.equal(result.trip_facts.itinerary[0].destination, 'Hanoi');
    assert.equal(result.trip_facts.itinerary[1].destination, 'Hanoi');
    assert.equal(result.trip_facts.itinerary[0].accommodation_id, 'acc_1');
    assert.equal(result.trip_facts.itinerary[1].accommodation_id, 'acc_1');
    // day 3 (index 2) is untouched — the line only covered 2 nights
    assert.equal(result.trip_facts.itinerary[2].destination, null);

    assert.equal(result.service_facts.hotels.length, 1);
    assert.equal(result.service_facts.hotels[0].accommodation_id, 'acc_1');
  });

  it('splits a discontinuous stay (gap day) into two separate hotel clusters', () => {
    const fallback = fallbackWithDays(3);
    const wb = workbench({
      items: [
        line({ id: 'l1', day_number: 1, qty_time: 1, product_ref: { property_id: 'acc_1', destination_name: 'Hanoi' } }),
        line({ id: 'l2', day_number: 3, qty_time: 1, product_ref: { property_id: 'acc_2', destination_name: 'Sapa' } }),
      ],
      summary: { cost_total_minor: 100, sell_total_minor: 100, margin_minor: 0, margin_bps: 0, by_day: [], by_category: [] },
    });
    const result = buildFactsFromCostingWorkbench(wb, fallback);
    assert.equal(result.service_facts.hotels.length, 2);
  });

  it('never overwrites a destination the sale already set', () => {
    const fallback = fallbackWithDays(1);
    fallback.trip_facts.itinerary[0] = { ...fallback.trip_facts.itinerary[0], destination: 'Hoi An' };
    const wb = workbench({
      items: [
        line({
          id: 'l1',
          category: 'transportation',
          day_number: 1,
          product_ref: { destination_name: 'Da Nang' },
        }),
      ],
    });
    const result = buildFactsFromCostingWorkbench(wb, fallback);
    assert.equal(result.trip_facts.itinerary[0].destination, 'Hoi An');
  });

  it('fills a blank destination from a non-accommodation line', () => {
    const fallback = fallbackWithDays(1);
    const wb = workbench({
      items: [
        line({ id: 'l1', category: 'transportation', day_number: 1, product_ref: { destination_name: 'Da Nang' } }),
      ],
    });
    const result = buildFactsFromCostingWorkbench(wb, fallback);
    assert.equal(result.trip_facts.itinerary[0].destination, 'Da Nang');
  });

  it('sets pricing option group_total_amount_minor + currency, leaving per-person null', () => {
    const fallback = fallbackWithDays(1);
    const wb = workbench({
      items: [line({ id: 'l1', day_number: 1 })],
      summary: { cost_total_minor: 1_000_000, sell_total_minor: 1_200_000, margin_minor: 200_000, margin_bps: 1667, by_day: [], by_category: [] },
    });
    const result = buildFactsFromCostingWorkbench(wb, fallback);
    const option = result.pricing_facts.options[0];
    assert.equal(option.group_total_amount_minor, 1_200_000);
    assert.equal(option.currency, 'USD');
    assert.equal(option.per_adult_amount_minor, null);
    assert.equal(option.per_child_amount_minor, null);
  });

  it('never mutates the fallback input', () => {
    const fallback = fallbackWithDays(2);
    const snapshot = JSON.parse(JSON.stringify(fallback));
    const wb = workbench({
      items: [line({ id: 'l1', day_number: 1, product_ref: { property_id: 'acc_1', destination_name: 'Hanoi' } })],
      summary: { cost_total_minor: 1, sell_total_minor: 1, margin_minor: 0, margin_bps: 0, by_day: [], by_category: [] },
    });
    buildFactsFromCostingWorkbench(wb, fallback);
    assert.deepEqual(fallback, snapshot);
  });
});
