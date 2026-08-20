import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { buildInitialFactsFromRequest } from '../requestToFactsHandoff.ts';
import { deriveDayWithStays, syncRouteTableToFacts } from '../../components/quotation-workspace/useRouteTableSync.ts';
import { createBrochureFacts } from '../../components/quotation-workspace/factsTypes.ts';
import type { QuoteRequestItem } from '../../components/quotation-workspace/factsTypes.ts';

describe('Layer 2 & Layer 3: requestToFactsHandoff & Reconcilers', () => {
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

  it('correctly reconciles per-person budget into adult rate, 75% child rate, and group total', () => {
    const fallback = createBrochureFacts();
    const mockRequest: QuoteRequestItem = {
      id: 'req_pricing_test',
      customer_name: 'Sarah Connor',
      email: 'sarah@example.com',
      phone: null,
      company_name: null,
      market: 'US',
      preferred_contact: null,
      raw_dates_text: null,
      children_details: null,
      travel_style: 'Luxury Wellness',
      special_requirements: null,
      created_by_profile_id: null,
      partner_id: null,
      linked_quotation_id: null,
      role: 'traveller',
      adults: 2,
      children: 1,
      kid_ages: [8],
      start_date: '2026-10-01',
      end_date: '2026-10-07',
      destinations: ['Hanoi', 'Halong Bay'],
      status: 'new',
      created_at: '2026-09-01T00:00:00Z',
      updated_at: '2026-09-01T00:00:00Z',
      payload_json: {
        budget: 4000,
        budget_basis: 'per person',
        currency: 'USD',
      },
    };

    const facts = buildInitialFactsFromRequest(mockRequest, fallback);
    const opt = facts.pricing_facts.options[0];

    assert.ok(opt);
    assert.equal(opt.currency, 'USD');
    // 4000 USD = 400000 minor
    assert.equal(opt.per_adult_amount_minor, 400000);
    // 75% of 400000 = 300000
    assert.equal(opt.per_child_amount_minor, 300000);
    // Total for 2 adults + 1 child = 2 * 400000 + 1 * 300000 = 1100000
    assert.equal(opt.group_total_amount_minor, 1100000);
  });

  it('correctly handles B2B advisor requests and infers party labels and greetings', () => {
    const fallback = createBrochureFacts();
    const mockB2BRequest: QuoteRequestItem = {
      id: 'req_b2b_test',
      customer_name: 'Emily Davis',
      email: 'emily@luxurydmc.com',
      phone: '+1-555-0199',
      company_name: 'Prestige Travel Advisory',
      market: 'UK',
      preferred_contact: null,
      raw_dates_text: null,
      children_details: null,
      travel_style: 'Family Adventure',
      special_requirements: null,
      created_by_profile_id: null,
      partner_id: null,
      linked_quotation_id: null,
      role: 'advisor',
      adults: 2,
      children: 2,
      kid_ages: [10, 12],
      start_date: '2026-11-10',
      end_date: '2026-11-18',
      destinations: ['Da Nang', 'Hoi An'],
      status: 'new',
      created_at: '2026-09-01T00:00:00Z',
      updated_at: '2026-09-01T00:00:00Z',
      payload_json: {
        client_name: 'Dr. Arthur Pendelton',
        country: 'United Kingdom',
        room_configuration: '2 Interconnecting Suites',
      },
    };

    const facts = buildInitialFactsFromRequest(mockB2BRequest, fallback);

    // End-client name resolved
    assert.equal(facts.customer_facts.customer_name, 'Dr. Arthur Pendelton');
    // Advisor fields preserved
    assert.equal(facts.customer_facts.advisor_name, 'Emily Davis');
    assert.equal(facts.customer_facts.advisor_agency, 'Prestige Travel Advisory');
    // Party label inferred
    assert.ok(facts.customer_facts.party_label?.includes('Arthur Pendelton') || facts.customer_facts.party_label?.includes('Party'));
    // Greeting name inferred
    assert.ok(facts.customer_facts.greeting_name?.includes('Arthur Pendelton') || facts.customer_facts.greeting_name?.includes('Pendelton'));
    // Room notes preserved
    assert.equal(facts.service_facts.room_notes, '2 Interconnecting Suites');
  });

  it('clusters multi-destination itinerary into discrete stay slots', () => {
    const fallback = createBrochureFacts();
    const mockTripRequest: QuoteRequestItem = {
      id: 'req_stays_test',
      customer_name: 'John Wick',
      email: 'john@wick.com',
      phone: null,
      company_name: null,
      market: 'US',
      preferred_contact: null,
      raw_dates_text: null,
      children_details: null,
      travel_style: null,
      special_requirements: null,
      created_by_profile_id: null,
      partner_id: null,
      linked_quotation_id: null,
      role: 'traveller',
      adults: 2,
      children: 0,
      kid_ages: [],
      start_date: '2026-12-01',
      end_date: '2026-12-06',
      destinations: ['Hanoi', 'Hue', 'Hoi An'],
      status: 'new',
      created_at: '2026-09-01T00:00:00Z',
      updated_at: '2026-09-01T00:00:00Z',
      payload_json: {
        itinerary_days: [
          { day_number: 1, destination: 'Hanoi', overnight: 'Hanoi' },
          { day_number: 2, destination: 'Hanoi', overnight: 'Hanoi' },
          { day_number: 3, destination: 'Hue', overnight: 'Hue' },
          { day_number: 4, destination: 'Hue', overnight: 'Hue' },
          { day_number: 5, destination: 'Hoi An', overnight: 'Hoi An' },
        ],
      },
    };

    const facts = buildInitialFactsFromRequest(mockTripRequest, fallback);

    // 3 distinct contiguous overnight cities -> 3 hotel stay slots
    assert.equal(facts.service_facts.hotels.length, 3);
    assert.equal(facts.service_facts.hotels[0].destination, 'Hanoi');
    assert.equal(facts.service_facts.hotels[0].check_in, '2026-12-01');
    assert.equal(facts.service_facts.hotels[0].check_out, '2026-12-03');

    assert.equal(facts.service_facts.hotels[1].destination, 'Hue');
    assert.equal(facts.service_facts.hotels[1].check_in, '2026-12-03');
    assert.equal(facts.service_facts.hotels[1].check_out, '2026-12-05');

    assert.equal(facts.service_facts.hotels[2].destination, 'Hoi An');
    assert.equal(facts.service_facts.hotels[2].check_in, '2026-12-05');
  });

  it('supports multilingual defaults for Vietnamese and Arabic', () => {
    const fallback = createBrochureFacts();
    const mockRequest: QuoteRequestItem = {
      id: 'req_lang_test',
      customer_name: 'Nguyễn Văn A',
      email: 'vana@example.vn',
      phone: null,
      company_name: null,
      market: 'VN',
      preferred_contact: null,
      raw_dates_text: null,
      children_details: null,
      travel_style: null,
      special_requirements: null,
      created_by_profile_id: null,
      partner_id: null,
      linked_quotation_id: null,
      role: 'traveller',
      adults: 2,
      children: 0,
      kid_ages: [],
      start_date: '2026-10-10',
      end_date: '2026-10-12',
      destinations: ['Phú Quốc'],
      status: 'new',
      created_at: '2026-09-01T00:00:00Z',
      updated_at: '2026-09-01T00:00:00Z',
      payload_json: {
        lang: 'vi',
      },
    };

    const viFacts = buildInitialFactsFromRequest(mockRequest, fallback, 'vi');
    assert.equal(viFacts.lang, 'vi');
    assert.ok(viFacts.trip_facts.itinerary[0].meals.includes('Bữa sáng'));

    const arFacts = buildInitialFactsFromRequest(mockRequest, fallback, 'ar');
    assert.equal(arFacts.lang, 'ar');
    assert.ok(arFacts.trip_facts.itinerary[0].meals.includes('الإفطار'));
  });
});

