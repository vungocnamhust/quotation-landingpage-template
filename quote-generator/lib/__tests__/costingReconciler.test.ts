import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  costingReconciler,
  previewLineCostMinor,
  previewLineSellMinor,
  resolveLineDisplayTotals,
  groupRowsByDay,
  splitSellTotalPerPerson,
  type CostingLineDraft,
  type CostingGroupRow,
} from '../rules/costingReconciler.ts';

function draft(overrides: Partial<CostingLineDraft> = {}): CostingLineDraft {
  return {
    unitCostMinor: 100,
    qtyUnit: 1,
    qtyTime: 1,
    fxRatePpm: null,
    sellOverrideMinor: null,
    markupRateBps: 0,
    roundingIncrementMinor: 0,
    ...overrides,
  };
}

describe('costingReconciler pure display rules', () => {
  describe('previewLineCostMinor', () => {
    it('multiplies unit cost by qty_unit and qty_time', () => {
      const cost = previewLineCostMinor(draft({ unitCostMinor: 500_000, qtyUnit: 2, qtyTime: 3 }));
      assert.equal(cost, 3_000_000);
    });

    it('applies fx_rate_ppm when present', () => {
      const cost = previewLineCostMinor(draft({ unitCostMinor: 100, fxRatePpm: 500_000 }));
      assert.equal(cost, 50);
    });
  });

  describe('previewLineSellMinor', () => {
    it('returns the override untouched when present', () => {
      const sell = previewLineSellMinor(draft({ sellOverrideMinor: 999, markupRateBps: 2_000 }), 1_000_000);
      assert.equal(sell, 999);
    });

    it('applies markup and rounds up to the increment', () => {
      const sell = previewLineSellMinor(draft({ markupRateBps: 1_000, roundingIncrementMinor: 10_000 }), 333);
      assert.equal(sell, 10_000);
    });
  });

  describe('resolveLineDisplayTotals — server always wins', () => {
    it('prefers server totals over a client preview', () => {
      const totals = resolveLineDisplayTotals(draft({ unitCostMinor: 100 }), { costMinor: 999, sellMinor: 1_500 });
      assert.equal(totals.costMinor, 999);
      assert.equal(totals.sellMinor, 1_500);
      assert.equal(totals.isPreview, false);
    });

    it('falls back to a preview when no server totals exist yet', () => {
      const totals = resolveLineDisplayTotals(draft({ unitCostMinor: 100, qtyUnit: 2 }));
      assert.equal(totals.costMinor, 200);
      assert.equal(totals.isPreview, true);
    });
  });

  describe('groupRowsByDay', () => {
    const row = (overrides: Partial<CostingGroupRow>): CostingGroupRow => ({
      id: 'row',
      dayNumber: 1,
      category: 'accommodation',
      costMinor: 0,
      sellMinor: 0,
      ...overrides,
    });

    it('groups by day ascending and puts trip-level lines in a null bucket last', () => {
      const rows: CostingGroupRow[] = [
        row({ id: 'a', dayNumber: 2, costMinor: 100, sellMinor: 120 }),
        row({ id: 'b', dayNumber: 1, costMinor: 50, sellMinor: 60 }),
        row({ id: 'c', dayNumber: null, category: 'visa', costMinor: 10, sellMinor: 15 }),
      ];
      const groups = groupRowsByDay(rows);
      assert.equal(groups.length, 3);
      assert.equal(groups[0].dayNumber, 1);
      assert.equal(groups[1].dayNumber, 2);
      assert.equal(groups[2].dayNumber, null);
      assert.equal(groups[2].rows[0].id, 'c');
    });

    it('sums cost/sell per bucket', () => {
      const rows: CostingGroupRow[] = [
        row({ id: 'a', dayNumber: 1, costMinor: 100, sellMinor: 120 }),
        row({ id: 'b', dayNumber: 1, costMinor: 50, sellMinor: 60 }),
      ];
      const groups = groupRowsByDay(rows);
      assert.equal(groups[0].costMinor, 150);
      assert.equal(groups[0].sellMinor, 180);
    });

    it('returns an empty array for no rows', () => {
      assert.deepEqual(groupRowsByDay([]), []);
    });
  });

  describe('splitSellTotalPerPerson', () => {
    it('delegates to pricingReconciler.inferOptionRatesFromTotal', () => {
      const split = splitSellTotalPerPerson(1_100_000, 2, 1, 0.75);
      assert.equal(split.perAdultMinor, 400_000);
      assert.equal(split.perChildMinor, 300_000);
    });
  });

  it('exposes the same functions via the costingReconciler aggregate', () => {
    assert.equal(costingReconciler.previewLineCostMinor, previewLineCostMinor);
    assert.equal(costingReconciler.groupRowsByDay, groupRowsByDay);
  });
});
