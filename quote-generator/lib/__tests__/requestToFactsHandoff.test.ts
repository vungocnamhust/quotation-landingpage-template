import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { buildInitialFactsFromRequest } from '../requestToFactsHandoff.ts';
import { deriveDayWithStays, syncRouteTableToFacts } from '../../components/quotation-workspace/useRouteTableSync.ts';
import { createBrochureFacts } from '../../components/quotation-workspace/factsTypes.ts';
import type { QuoteRequestItem } from '../../components/quotation-workspace/factsTypes.ts';

describe('Layer 2 & Layer 3: requestToFactsHandoff & useRouteTableSync', () => {
  it('preserves exact overnight destination from QuoteRequest when day destination is an excursion', () => {
    const fallback = createBrochureFacts();

    const mockQuoteRequest: QuoteRequestItem = {
      id: 'req_cdda12b423644000',
      customer_name: 'nam vu',
      email: 'vungocnam0409@gmail.com',
      phone: null,
      company_name: null,
      market: null,
      preferred_contact: null,
      raw_dates_text: null,
      children_details: null,
      travel_style: null,
      special_requirements: null,
      created_by_profile_id: null,
      partner_id: null,
      linked_quotation_id: null,
      role: 'traveller',
      adults: 10,
      children: 5,
      kid_ages: [6, 6, 6, 6, 6],
      start_date: '2026-09-26',
      end_date: '2026-09-28',
      destinations: ['Ho Chi Minh City'],
      status: 'new',
      created_at: '2026-09-01T00:00:00Z',
      updated_at: '2026-09-01T00:00:00Z',
      payload_json: {
        client_name: 'nam vu',
        itinerary_days: [
          {
            day_number: 1,
            destination: 'Ho Chi Minh City',
            overnight: 'Ho Chi Minh City',
            summary: 'Tham quan nhà thờ đức bà, bưu điện sài gòn, dinh độc lập',
          },
          {
            day_number: 2,
            destination: 'Mekong Delta',
            overnight: 'Ho Chi Minh City',
            summary: 'Chèo thuyền thúng',
          },
          {
            day_number: 3,
            destination: 'Ho Chi Minh City',
            overnight: 'Ho Chi Minh City',
            summary: 'Departure day',
          },
        ],
      },
    };

    // Layer 2: Handoff engine builds facts from QuoteRequest
    const initialFacts = buildInitialFactsFromRequest(mockQuoteRequest, fallback);

    assert.equal(initialFacts.trip_facts.itinerary.length, 3);
    assert.equal(initialFacts.trip_facts.itinerary[0].destination, 'Ho Chi Minh City');
    assert.equal(initialFacts.trip_facts.itinerary[0].overnight, 'Ho Chi Minh City');

    // Day 2 must have Day Destination = Mekong Delta, but Overnight = Ho Chi Minh City
    assert.equal(initialFacts.trip_facts.itinerary[1].destination, 'Mekong Delta');
    assert.equal(initialFacts.trip_facts.itinerary[1].overnight, 'Ho Chi Minh City');

    assert.equal(initialFacts.trip_facts.itinerary[2].destination, 'Ho Chi Minh City');
    assert.equal(initialFacts.trip_facts.itinerary[2].overnight, 'Ho Chi Minh City');

    // Layer 3: deriveDayWithStays extracts DayWithStayItem[] for Layer 4 UI
    const dayWithStays = deriveDayWithStays(initialFacts);
    assert.equal(dayWithStays.length, 3);
    assert.equal(dayWithStays[1].destination, 'Mekong Delta');
    assert.equal(dayWithStays[1].overnight, 'Ho Chi Minh City');

    // Layer 3: syncRouteTableToFacts preserves overnight back to QuotationFacts
    const syncedFacts = syncRouteTableToFacts(initialFacts, dayWithStays);
    assert.equal(syncedFacts.trip_facts.itinerary[1].destination, 'Mekong Delta');
    assert.equal(syncedFacts.trip_facts.itinerary[1].overnight, 'Ho Chi Minh City');
  });
});
