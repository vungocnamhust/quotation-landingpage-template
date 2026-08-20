import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  pricingReconciler,
  currencyDivisor,
  minorToMajor,
  majorToMinor,
  convertCurrencyAmount,
  type CanonicalPricingOption,
  type CanonicalCommercialPricing,
} from '../rules/pricingReconciler.ts';

describe('pricingReconciler pure domain rules', () => {
  describe('currencyDivisor and unit converters', () => {
    it('returns 1 for VND and 100 for other currencies', () => {
      assert.equal(currencyDivisor('VND'), 1);
      assert.equal(currencyDivisor('vnd'), 1);
      assert.equal(currencyDivisor('USD'), 100);
      assert.equal(currencyDivisor('EUR'), 100);
      assert.equal(currencyDivisor('GBP'), 100);
      assert.equal(currencyDivisor('AUD'), 100);
    });

    it('converts minor <-> major accurately without float artifacts', () => {
      assert.equal(minorToMajor(400000, 'USD'), 4000);
      assert.equal(majorToMinor(4000, 'USD'), 400000);

      assert.equal(minorToMajor(50000000, 'VND'), 50000000);
      assert.equal(majorToMinor(50000000, 'VND'), 50000000);
    });
  });

  describe('calculateOptionTotal (forward invariant)', () => {
    it('calculates total for adults only when children = 0', () => {
      // 2 adults x $4,000 (400,000 cents) = $8,000 (800,000 cents)
      const total = pricingReconciler.calculateOptionTotal(400000, null, 2, 0);
      assert.equal(total, 800000);
    });

    it('calculates total for adults and children correctly', () => {
      // 2 adults x $4,000 (400,000) + 2 children x $3,000 (300,000) = $14,000 (1,400,000)
      const total = pricingReconciler.calculateOptionTotal(400000, 300000, 2, 2);
      assert.equal(total, 1400000);
    });

    it('returns null if perAdultMinor is invalid or zero', () => {
      assert.equal(pricingReconciler.calculateOptionTotal(null, 200000, 2, 1), null);
      assert.equal(pricingReconciler.calculateOptionTotal(0, 200000, 2, 1), null);
    });
  });

  describe('inferOptionRatesFromTotal (reverse invariant)', () => {
    it('infers adult rate directly when no children present', () => {
      // $8,000 total for 2 adults -> $4,000/adult
      const rates = pricingReconciler.inferOptionRatesFromTotal(800000, 2, 0, 0.75);
      assert.equal(rates.perAdultMinor, 400000);
      assert.equal(rates.perChildMinor, null);
    });

    it('infers adult and child rates with default 75% ratio', () => {
      // $11,000 total for 2 adults + 1 child (0.75 ratio)
      // Weighted units = 2 + 1*0.75 = 2.75
      // Adult = 1,100,000 / 2.75 = 400,000
      // Child = 400,000 * 0.75 = 300,000
      const rates = pricingReconciler.inferOptionRatesFromTotal(1100000, 2, 1, 0.75);
      assert.equal(rates.perAdultMinor, 400000);
      assert.equal(rates.perChildMinor, 300000);
    });
  });

  describe('applyChildPreset', () => {
    it('applies 50%, 75%, 100%, and 0% presets and updates total', () => {
      const option: CanonicalPricingOption = {
        id: 'opt-1',
        label: 'Luxury',
        currency: 'USD',
        perAdultMinor: 400000,
        perChildMinor: 300000,
        groupTotalMinor: 1100000,
      };

      // 50% preset (400,000 * 0.5 = 200,000) -> Total for 2 adults + 1 child = 800,000 + 200,000 = 1,000,000
      const opt50 = pricingReconciler.applyChildPreset(option, 0.5, 2, 1);
      assert.equal(opt50.perChildMinor, 200000);
      assert.equal(opt50.groupTotalMinor, 1000000);

      // 0% preset (Free kids) -> Total = 800,000
      const opt0 = pricingReconciler.applyChildPreset(option, 0, 2, 1);
      assert.equal(opt0.perChildMinor, 0);
      assert.equal(opt0.groupTotalMinor, 800000);

      // 100% preset -> Child = 400,000 -> Total = 1,200,000
      const opt100 = pricingReconciler.applyChildPreset(option, 1.0, 2, 1);
      assert.equal(opt100.perChildMinor, 400000);
      assert.equal(opt100.groupTotalMinor, 1200000);
    });
  });

  describe('updateOption methods', () => {
    it('updateOptionPerAdult recomputes total', () => {
      const option: CanonicalPricingOption = {
        id: 'opt-1',
        label: 'Luxury',
        currency: 'USD',
        perAdultMinor: 400000,
        perChildMinor: 300000,
        groupTotalMinor: 1100000,
      };

      const updated = pricingReconciler.updateOptionPerAdult(option, 500000, 2, 1);
      assert.equal(updated.perAdultMinor, 500000);
      assert.equal(updated.groupTotalMinor, 1300000); // 2*500k + 300k
    });

    it('updateOptionTotal reverse infers adult and child rates', () => {
      const option: CanonicalPricingOption = {
        id: 'opt-1',
        label: 'Luxury',
        currency: 'USD',
        perAdultMinor: 400000,
        perChildMinor: 300000,
        groupTotalMinor: 1100000,
        childRatio: 0.75,
      };

      const updated = pricingReconciler.updateOptionTotal(option, 1375000, 2, 1);
      // 1,375,000 / 2.75 = 500,000 (adult), 375,000 (child)
      assert.equal(updated.perAdultMinor, 500000);
      assert.equal(updated.perChildMinor, 375000);
      assert.equal(updated.groupTotalMinor, 1375000);
    });
  });

  describe('syncPaxCounts invariant', () => {
    it('automatically scales group totals when Pax counts change', () => {
      const pricing: CanonicalCommercialPricing = {
        currency: 'USD',
        adults: 2,
        children: 0,
        options: [
          {
            id: 'opt-1',
            label: 'Option 1',
            currency: 'USD',
            perAdultMinor: 400000, // $4,000
            perChildMinor: null,
            groupTotalMinor: 800000, // $8,000
            childRatio: 0.75,
          },
        ],
      };

      // Change from 2 adults -> 4 adults + 2 children
      const synced = pricingReconciler.syncPaxCounts(pricing, 4, 2);
      assert.equal(synced.adults, 4);
      assert.equal(synced.children, 2);
      // Option 1: perAdult = 400,000, perChild inferred as 400,000 * 0.75 = 300,000
      // Total = 4 * 400,000 + 2 * 300,000 = 2,200,000 ($22,000)
      assert.equal(synced.options[0].perAdultMinor, 400000);
      assert.equal(synced.options[0].perChildMinor, 300000);
      assert.equal(synced.options[0].groupTotalMinor, 2200000);
    });

    it('infers rates from total first if option had only group total without rates', () => {
      const pricing: CanonicalCommercialPricing = {
        currency: 'USD',
        adults: 2,
        children: 0,
        options: [
          {
            id: 'opt-legacy',
            label: 'Fixed Package',
            currency: 'USD',
            perAdultMinor: null,
            perChildMinor: null,
            groupTotalMinor: 600000, // $6,000 for 2 adults -> $3,000/adult
            childRatio: 0.75,
          },
        ],
      };

      const synced = pricingReconciler.syncPaxCounts(pricing, 3, 0);
      assert.equal(synced.options[0].perAdultMinor, 300000);
      assert.equal(synced.options[0].groupTotalMinor, 900000); // 3 * 300,000
    });
  });

  describe('3-Tier FX Rate & Currency Conversion', () => {
    it('converts USD to VND accurately with divisor 100 -> 1', () => {
      // $4,000 USD (400,000 cents) at 1 USD = 25,400 VND
      // 4000 * 25400 = 101,600,000 VND
      const vramt = convertCurrencyAmount(400000, 'USD', 'VND');
      assert.equal(vramt, 101600000);
    });

    it('converts VND to USD accurately with divisor 1 -> 100', () => {
      // 101,600,000 VND at 1 USD = 25,400 VND -> $4,000 USD (400,000 cents)
      const usdamt = convertCurrencyAmount(101600000, 'VND', 'USD');
      assert.equal(usdamt, 400000);
    });

    it('converts option currency with smart amount conversion', () => {
      const option: CanonicalPricingOption = {
        id: 'opt-1',
        label: 'Luxury',
        currency: 'USD',
        perAdultMinor: 400000, // $4,000
        perChildMinor: 300000, // $3,000
        groupTotalMinor: 1100000, // $11,000 for 2A + 1C
      };

      const inVnd = pricingReconciler.convertOptionCurrency(option, 'VND', {
        convertAmounts: true,
        adults: 2,
        children: 1,
      });

      assert.equal(inVnd.currency, 'VND');
      assert.equal(inVnd.perAdultMinor, 101600000); // 4000 * 25400
      assert.equal(inVnd.perChildMinor, 76200000);  // 3000 * 25400
      assert.equal(inVnd.groupTotalMinor, 279400000); // 2*101.6M + 76.2M
    });

    it('supports unit switch mode without changing raw numbers', () => {
      const option: CanonicalPricingOption = {
        id: 'opt-1',
        label: 'Luxury',
        currency: 'USD',
        perAdultMinor: 400000,
        perChildMinor: null,
        groupTotalMinor: 800000,
      };

      const switched = pricingReconciler.convertOptionCurrency(option, 'EUR', {
        convertAmounts: false,
      });

      assert.equal(switched.currency, 'EUR');
      assert.equal(switched.perAdultMinor, 400000);
      assert.equal(switched.groupTotalMinor, 800000);
      assert.equal(switched.exchangeRateMeta?.source, 'unit_switch');
    });
  });

  describe('option management (add, remove, update)', () => {
    it('adds option up to MAX_COMMERCIAL_OPTIONS', () => {
      let pricing: CanonicalCommercialPricing = {
        currency: 'USD',
        adults: 2,
        children: 0,
        options: [pricingReconciler.createDefaultPricingOption(1, 'USD')],
      };

      pricing = pricingReconciler.addOption(pricing, 'Premium Option');
      assert.equal(pricing.options.length, 2);
      assert.equal(pricing.options[1].label, 'Premium Option');

      pricing = pricingReconciler.addOption(pricing, 'Villa Option');
      assert.equal(pricing.options.length, 3);

      // Attempt adding 4th option -> blocked by limit
      pricing = pricingReconciler.addOption(pricing, 'Excess Option');
      assert.equal(pricing.options.length, 3);
    });

    it('removes option safely', () => {
      const pricing: CanonicalCommercialPricing = {
        currency: 'USD',
        adults: 2,
        children: 0,
        options: [
          { id: '1', label: 'Opt 1', currency: 'USD', perAdultMinor: 100, perChildMinor: null, groupTotalMinor: 200 },
          { id: '2', label: 'Opt 2', currency: 'USD', perAdultMinor: 200, perChildMinor: null, groupTotalMinor: 400 },
        ],
      };

      const afterRemove = pricingReconciler.removeOption(pricing, 0);
      assert.equal(afterRemove.options.length, 1);
      assert.equal(afterRemove.options[0].id, '2');
    });
  });
});
