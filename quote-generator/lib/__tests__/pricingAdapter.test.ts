import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { pricingAdapter } from '../rules/pricingAdapter.ts';
import { pricingReconciler } from '../rules/pricingReconciler.ts';
import { createBrochureFacts } from '../../components/quotation-workspace/factsTypes.ts';
import { getInitialQuoteRequestFormState } from '../quoteRequestPayload.ts';
import { addPricingOptionInFacts, removePricingOptionInFacts } from '../prefillEngine.ts';

describe('pricingAdapter bidirectional schema mapping', () => {
  describe('QuotationFacts <-> CanonicalCommercialPricing', () => {
    it('adapts QuotationFacts back and forth cleanly', () => {
      const facts = createBrochureFacts();
      facts.customer_facts.adults = 2;
      facts.customer_facts.children = 1;
      facts.pricing_facts.options = [
        {
          id: 'opt-1',
          label: 'Signature Option',
          currency: 'USD',
          per_adult_amount_minor: 400000, // $4,000
          per_child_amount_minor: 300000, // $3,000
          per_traveler_amount_minor: 400000,
          group_total_amount_minor: 1100000, // $11,000
        },
      ];

      const canonical = pricingAdapter.fromQuotationFacts(facts);
      assert.equal(canonical.adults, 2);
      assert.equal(canonical.children, 1);
      assert.equal(canonical.currency, 'USD');
      assert.equal(canonical.options.length, 1);
      assert.equal(canonical.options[0].perAdultMinor, 400000);
      assert.equal(canonical.options[0].perChildMinor, 300000);
      assert.equal(canonical.options[0].groupTotalMinor, 1100000);

      // Reconcile: change Pax to 4 adults + 2 children
      const syncedCanonical = pricingReconciler.syncPaxCounts(canonical, 4, 2);
      const updatedFacts = pricingAdapter.syncToQuotationFacts(syncedCanonical, facts);

      assert.equal(updatedFacts.customer_facts.adults, 4);
      assert.equal(updatedFacts.customer_facts.children, 2);
      assert.equal(updatedFacts.pricing_facts.options[0].per_adult_amount_minor, 400000);
      assert.equal(updatedFacts.pricing_facts.options[0].per_child_amount_minor, 300000);
      // Total = 4 * 400,000 + 2 * 300,000 = 2,200,000
      assert.equal(updatedFacts.pricing_facts.options[0].group_total_amount_minor, 2200000);
    });
  });

  describe('QuoteRequestFormState <-> CanonicalCommercialPricing', () => {
    it('adapts QuoteRequest with total group budget', () => {
      const formState = getInitialQuoteRequestFormState('traveller');
      formState.adults = 2;
      formState.children = 0;
      formState.currency = 'USD';
      formState.budget = 8000; // $8,000 total trip
      formState.budget_basis = 'Total trip';

      const canonical = pricingAdapter.fromQuoteRequest(formState);
      assert.equal(canonical.adults, 2);
      assert.equal(canonical.currency, 'USD');
      assert.equal(canonical.options[0].groupTotalMinor, 800000);
      assert.equal(canonical.options[0].perAdultMinor, 400000);

      // Convert to EUR and sync back to request
      const converted = pricingReconciler.convertOptionCurrency(canonical.options[0], 'EUR', {
        convertAmounts: false,
      });
      const updatedCanonical = { ...canonical, currency: 'EUR', options: [converted] };
      const updatedForm = pricingAdapter.syncToQuoteRequest(updatedCanonical, formState);

      assert.equal(updatedForm.currency, 'EUR');
      assert.equal(updatedForm.budget, 8000);
    });

    it('adapts QuoteRequest with per person budget', () => {
      const formState = getInitialQuoteRequestFormState('traveller');
      formState.adults = 2;
      formState.children = 1;
      formState.currency = 'USD';
      formState.budget = 4000; // $4,000 per person
      formState.budget_basis = 'Per person';

      const canonical = pricingAdapter.fromQuoteRequest(formState);
      assert.equal(canonical.adults, 2);
      assert.equal(canonical.children, 1);
      assert.equal(canonical.options[0].perAdultMinor, 400000);
      assert.equal(canonical.options[0].perChildMinor, 300000); // 75%
      assert.equal(canonical.options[0].groupTotalMinor, 1100000); // 2*4k + 1*3k
    });
  });

  describe('TriPricing UI Props <-> CanonicalPricingOption', () => {
    it('converts back and forth seamlessly', () => {
      const tri = {
        label: 'Luxury Package',
        currency: 'USD',
        perAdultMinor: 500000,
        perChildMinor: 375000,
        groupTotalMinor: 1375000,
      };

      const canonicalOpt = pricingAdapter.fromTriPricing(tri, 2, 1);
      assert.equal(canonicalOpt.label, 'Luxury Package');
      assert.equal(canonicalOpt.perAdultMinor, 500000);
      assert.equal(canonicalOpt.perChildMinor, 375000);
      assert.equal(canonicalOpt.groupTotalMinor, 1375000);
      assert.equal(canonicalOpt.childRatio, 0.75);

      const convertedTri = pricingAdapter.toTriPricing(canonicalOpt);
      assert.deepEqual(convertedTri, tri);
    });
  });

  describe('addPricingOptionInFacts & removePricingOptionInFacts', () => {
    it('adds and removes pricing options within 1 to 3 limit', () => {
      const facts = addPricingOptionInFacts(createBrochureFacts(), 'Standard Tier');
      assert.equal(facts.pricing_facts.options.length, 2);

      // Start with 1 default option
      const baseFacts = createBrochureFacts();
      baseFacts.pricing_facts.options = [
        {
          id: 'opt-1',
          label: 'Standard Option',
          currency: 'USD',
          per_adult_amount_minor: 350000,
          group_total_amount_minor: 700000,
        },
      ];
      assert.equal(baseFacts.pricing_facts.options.length, 1);

      // Add Option 2
      const withTwo = addPricingOptionInFacts(baseFacts, 'Premium Tier');
      assert.equal(withTwo.pricing_facts.options.length, 2);
      assert.equal(withTwo.pricing_facts.options[1].label, 'Premium Tier');

      // Add Option 3
      const withThree = addPricingOptionInFacts(withTwo, 'Deluxe Suite');
      assert.equal(withThree.pricing_facts.options.length, 3);
      assert.equal(withThree.pricing_facts.options[2].label, 'Deluxe Suite');

      // Add Option 4 - should stay at 3 (MAX_COMMERCIAL_OPTIONS limit)
      const withFour = addPricingOptionInFacts(withThree, 'Extra Tier');
      assert.equal(withFour.pricing_facts.options.length, 3);

      // Remove Option at index 1
      const afterRemove = removePricingOptionInFacts(withThree, 1);
      assert.equal(afterRemove.pricing_facts.options.length, 2);
      assert.equal(afterRemove.pricing_facts.options[0].label, 'Standard Option');
      assert.equal(afterRemove.pricing_facts.options[1].label, 'Deluxe Suite');

      // Remove down to 1
      const downToOne = removePricingOptionInFacts(afterRemove, 1);
      assert.equal(downToOne.pricing_facts.options.length, 1);

      // Attempt to remove the last remaining option - must preserve at least 1
      const attemptEmpty = removePricingOptionInFacts(downToOne, 0);
      assert.equal(attemptEmpty.pricing_facts.options.length, 1);
    });
  });
});
