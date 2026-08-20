import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { partyAdapter } from '../rules/partyAdapter.ts';
import type { QuoteRequestFormState } from '../quoteRequestPayload.ts';
import type { QuotationFacts } from '../../components/quotation-workspace/factsTypes.ts';
import { ensureFactsDefaults } from '../../components/quotation-workspace/factsTypes.ts';

describe('partyAdapter bidirectional schema mapping', () => {
  describe('QuoteRequestFormState <-> CanonicalParty', () => {
    it('adapts traveller persona quote request', () => {
      const formState: Partial<QuoteRequestFormState> = {
        role: 'traveller',
        first_name: 'David',
        last_name: 'Beck',
        adults: 2,
        children: 1,
        kid_ages: [9],
        infants: 0,
        room_configuration: '1 Double (King)',
      };

      const canonical = partyAdapter.fromQuoteRequest(formState as QuoteRequestFormState);
      assert.equal(canonical.customerName, 'David Beck');
      assert.equal(canonical.adults, 2);
      assert.equal(canonical.children, 1);
      assert.deepEqual(canonical.kidAges, [9]);
      assert.equal(canonical.roomConfiguration, '1 Double (King)');

      const synced = partyAdapter.syncToQuoteRequest(canonical, formState as QuoteRequestFormState);
      assert.equal(synced.first_name, 'David');
      assert.equal(synced.last_name, 'Beck');
      assert.equal(synced.adults, 2);
      assert.equal(synced.children, 1);
      assert.deepEqual(synced.kid_ages, [9]);
    });

    it('adapts advisor persona quote request with client name', () => {
      const formState: Partial<QuoteRequestFormState> = {
        role: 'advisor',
        client_name: 'The Vance Family',
        advisor_company: 'Luxury Travel Agency',
        advisor_first_name: 'Sarah',
        advisor_last_name: 'Connor',
        adults: 2,
        children: 2,
        kid_ages: [6, 12],
        room_configuration: '2 Interconnecting Rooms',
      };

      const canonical = partyAdapter.fromQuoteRequest(formState as QuoteRequestFormState);
      assert.equal(canonical.customerName, 'The Vance Family');
      assert.equal(canonical.role, 'advisor');
      assert.equal(canonical.adults, 2);
      assert.equal(canonical.children, 2);
      assert.deepEqual(canonical.kidAges, [6, 12]);

      const synced = partyAdapter.syncToQuoteRequest(canonical, formState as QuoteRequestFormState);
      assert.equal(synced.client_name, 'The Vance Family');
      assert.equal(synced.advisor_first_name, 'Sarah');
      assert.equal(synced.advisor_last_name, 'Connor');
    });
  });

  describe('QuotationFacts <-> CanonicalParty', () => {
    it('adapts QuotationFacts and synchronizes back losslessly', () => {
      const initialFacts = ensureFactsDefaults({
        customer_facts: {
          customer_name: 'Lord Hamilton',
          adults: 2,
          children: 2,
          kid_ages: [7, 10],
          party_label: 'Hamilton Family & Party (2 Adults, 2 Children)',
          greeting_name: 'Dear Lord Hamilton',
        },
        service_facts: {
          room_notes: 'High floor preferred, connecting rooms requested',
        },
      } as Partial<QuotationFacts> as QuotationFacts);

      const canonical = partyAdapter.fromQuotationFacts(initialFacts);
      assert.equal(canonical.customerName, 'Lord Hamilton');
      assert.equal(canonical.adults, 2);
      assert.equal(canonical.children, 2);
      assert.deepEqual(canonical.kidAges, [7, 10]);
      assert.equal(canonical.roomNotes, 'High floor preferred, connecting rooms requested');

      const syncedFacts = partyAdapter.syncToQuotationFacts(canonical, initialFacts);
      assert.equal(syncedFacts.customer_facts.customer_name, 'Lord Hamilton');
      assert.equal(syncedFacts.customer_facts.adults, 2);
      assert.equal(syncedFacts.customer_facts.children, 2);
      assert.deepEqual(syncedFacts.customer_facts.kid_ages, [7, 10]);
      assert.equal(syncedFacts.service_facts.room_notes, 'High floor preferred, connecting rooms requested');
    });
  });
});
