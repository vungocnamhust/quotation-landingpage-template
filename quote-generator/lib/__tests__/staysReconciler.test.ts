import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { staysReconciler, type CanonicalStay } from '../rules/staysReconciler.ts';
import type { CanonicalDay } from '../rules/tripReconciler.ts';

describe('staysReconciler pure domain rules', () => {
  describe('reconcileStaysFromItinerary', () => {
    it('returns empty array when itinerary has no hotels booked (land-only tour)', () => {
      const itinerary: CanonicalDay[] = [
        { day_number: 1, destination: 'Hanoi', overnight: 'Hanoi', display_date: '01 Nov', summary: 'Arrival' },
        { day_number: 2, destination: 'Hanoi', overnight: 'Hanoi', display_date: '02 Nov', summary: 'City tour' },
        { day_number: 3, destination: 'Ninh Binh', overnight: 'Ninh Binh', display_date: '03 Nov', summary: 'Boat trip' },
      ];

      const stays = staysReconciler.reconcileStaysFromItinerary(itinerary, '2026-11-01');
      assert.equal(stays.length, 0);
      const hotels = staysReconciler.toHotelFacts(stays);
      assert.equal(hotels.length, 0);
    });

    it('merges contiguous days with the same hotel into a single stay segment', () => {
      const itinerary: CanonicalDay[] = [
        {
          day_number: 1,
          destination: 'Hanoi',
          overnight: 'Hanoi',
          display_date: '01 Nov',
          summary: 'Arrival',
          accommodation_id: 'hotel-metropole',
          accommodation_name: 'Sofitel Legend Metropole',
          room_type: 'Grand Luxury',
        },
        {
          day_number: 2,
          destination: 'Hanoi',
          overnight: 'Hanoi',
          display_date: '02 Nov',
          summary: 'City tour',
          accommodation_id: 'hotel-metropole',
          accommodation_name: 'Sofitel Legend Metropole',
          room_type: 'Grand Luxury',
        },
        {
          day_number: 3,
          destination: 'Hanoi',
          overnight: 'Hanoi',
          display_date: '03 Nov',
          summary: 'Cooking class',
          accommodation_id: 'hotel-metropole',
          accommodation_name: 'Sofitel Legend Metropole',
          room_type: 'Grand Luxury',
        },
      ];

      const stays = staysReconciler.reconcileStaysFromItinerary(itinerary, '2026-11-01');
      assert.equal(stays.length, 1);
      assert.equal(stays[0].name, 'Sofitel Legend Metropole');
      assert.equal(stays[0].accommodation_id, 'hotel-metropole');
      assert.equal(stays[0].day_start, 1);
      assert.equal(stays[0].day_end, 3);
      assert.equal(stays[0].nights, 3);
      assert.equal(stays[0].check_in, '2026-11-01');
      assert.equal(stays[0].check_out, '2026-11-04');
    });

    it('handles non-contiguous stays with transit gaps (e.g. overnight sleeper train)', () => {
      const itinerary: CanonicalDay[] = [
        {
          day_number: 1,
          destination: 'Hanoi',
          overnight: 'Hanoi',
          display_date: '01 Nov',
          summary: 'Arrival',
          accommodation_id: 'hotel-metropole',
          accommodation_name: 'Sofitel Metropole',
          room_type: 'Luxury',
        },
        {
          day_number: 2,
          destination: 'Hanoi',
          overnight: 'Hanoi',
          display_date: '02 Nov',
          summary: 'City tour',
          accommodation_id: 'hotel-metropole',
          accommodation_name: 'Sofitel Metropole',
          room_type: 'Luxury',
        },
        {
          day_number: 3,
          destination: 'Lao Cai',
          overnight: 'Overnight Sleeper Train',
          display_date: '03 Nov',
          summary: 'Board night train',
          // No hotel assigned for transit night
          accommodation_id: null,
          accommodation_name: null,
        },
        {
          day_number: 4,
          destination: 'Sapa',
          overnight: 'Sapa',
          display_date: '04 Nov',
          summary: 'Arrive in Sapa, trekking',
          accommodation_id: 'hotel-de-la-coupole',
          accommodation_name: 'Hotel de la Coupole Sapa',
          room_type: 'Classic Room',
        },
        {
          day_number: 5,
          destination: 'Sapa',
          overnight: 'Sapa',
          display_date: '05 Nov',
          summary: 'Fansipan cable car',
          accommodation_id: 'hotel-de-la-coupole',
          accommodation_name: 'Hotel de la Coupole Sapa',
          room_type: 'Classic Room',
        },
      ];

      const stays = staysReconciler.reconcileStaysFromItinerary(itinerary, '2026-11-01');
      assert.equal(stays.length, 2);

      // Stay 1: Hanoi Metropole (Days 1-2, 2 nights)
      assert.equal(stays[0].name, 'Sofitel Metropole');
      assert.equal(stays[0].day_start, 1);
      assert.equal(stays[0].day_end, 2);
      assert.equal(stays[0].nights, 2);
      assert.equal(stays[0].check_in, '2026-11-01');
      assert.equal(stays[0].check_out, '2026-11-03');

      // Stay 2: Sapa Hotel de la Coupole (Days 4-5, 2 nights)
      assert.equal(stays[1].name, 'Hotel de la Coupole Sapa');
      assert.equal(stays[1].day_start, 4);
      assert.equal(stays[1].day_end, 5);
      assert.equal(stays[1].nights, 2);
      assert.equal(stays[1].check_in, '2026-11-04');
      assert.equal(stays[1].check_out, '2026-11-06');

      // Total booked nights = 4 <= 5 tour days
      const totalBooked = stays.reduce((acc, s) => acc + s.nights, 0);
      assert.equal(totalBooked, 4);
    });

    it('preserves previous hotel metadata (assets, phone, intro) when re-clustering', () => {
      const prevHotels = [
        {
          accommodation_id: 'hotel-metropole',
          destination: 'Hanoi',
          name: 'Sofitel Legend Metropole',
          room_type: 'Luxury',
          intro: 'Historic French colonial luxury landmark.',
          phone: '+84 24 3826 6919',
          display_city: 'Hanoi Historic French Quarter',
          hotel_asset: 'assets/metropole_facade.jpg',
          room_asset: 'assets/metropole_room.jpg',
        },
      ];

      const itinerary: CanonicalDay[] = [
        {
          day_number: 1,
          destination: 'Hanoi',
          overnight: 'Hanoi',
          display_date: '01 Nov',
          summary: null,
          accommodation_id: 'hotel-metropole',
          accommodation_name: 'Sofitel Legend Metropole',
          room_type: 'Luxury',
        },
      ];

      const stays = staysReconciler.reconcileStaysFromItinerary(itinerary, '2026-11-01', prevHotels);
      assert.equal(stays.length, 1);
      assert.equal(stays[0].intro, 'Historic French colonial luxury landmark.');
      assert.equal(stays[0].phone, '+84 24 3826 6919');
      assert.equal(stays[0].display_city, 'Hanoi Historic French Quarter');
      assert.equal(stays[0].hotel_asset, 'assets/metropole_facade.jpg');
      assert.equal(stays[0].room_asset, 'assets/metropole_room.jpg');
    });
  });

  describe('shiftStayDates', () => {
    it('shifts check_in and check_out dates cleanly when trip start date changes', () => {
      const initialStays: CanonicalStay[] = [
        {
          accommodation_id: 'hotel-1',
          name: 'Hotel 1',
          destination: 'Hanoi',
          room_type: 'Standard',
          day_start: 1,
          day_end: 2,
          nights: 2,
          check_in: '2026-11-01',
          check_out: '2026-11-03',
        },
        {
          accommodation_id: 'hotel-2',
          name: 'Hotel 2',
          destination: 'Hue',
          room_type: 'Deluxe',
          day_start: 3,
          day_end: 4,
          nights: 2,
          check_in: '2026-11-03',
          check_out: '2026-11-05',
        },
      ];

      const shifted = staysReconciler.shiftStayDates(initialStays, '2026-12-15');
      assert.equal(shifted[0].check_in, '2026-12-15');
      assert.equal(shifted[0].check_out, '2026-12-17');
      assert.equal(shifted[0].nights, 2);

      assert.equal(shifted[1].check_in, '2026-12-17');
      assert.equal(shifted[1].check_out, '2026-12-19');
      assert.equal(shifted[1].nights, 2);
    });
  });

  describe('syncItineraryFromStays', () => {
    it('hydrates accommodation information to itinerary days from stay dates', () => {
      const itinerary: CanonicalDay[] = [
        { day_number: 1, destination: 'Hanoi', overnight: 'Hanoi', display_date: null, summary: null },
        { day_number: 2, destination: 'Hanoi', overnight: 'Hanoi', display_date: null, summary: null },
        { day_number: 3, destination: 'Hue', overnight: 'Hue', display_date: null, summary: null },
      ];

      const stays: CanonicalStay[] = [
        {
          accommodation_id: 'hotel-metropole',
          name: 'Sofitel Metropole',
          destination: 'Hanoi',
          room_type: 'Luxury',
          day_start: 1,
          day_end: 2,
          nights: 2,
          check_in: '2026-11-01',
          check_out: '2026-11-03',
        },
      ];

      const hydrated = staysReconciler.syncItineraryFromStays(itinerary, stays, '2026-11-01');
      assert.equal(hydrated[0].accommodation_id, 'hotel-metropole');
      assert.equal(hydrated[0].accommodation_name, 'Sofitel Metropole');
      assert.equal(hydrated[1].accommodation_id, 'hotel-metropole');
      assert.equal(hydrated[1].accommodation_name, 'Sofitel Metropole');
      // Day 3 not covered
      assert.equal(hydrated[2].accommodation_id, null);
    });
  });

  describe('updateDayAccommodation smart cascade', () => {
    it('cascades hotel update to subsequent contiguous days in same destination', () => {
      const itinerary: CanonicalDay[] = [
        { day_number: 1, destination: 'Hanoi', overnight: 'Hanoi', display_date: null, summary: null },
        { day_number: 2, destination: 'Hanoi', overnight: 'Hanoi', display_date: null, summary: null },
        { day_number: 3, destination: 'Hue', overnight: 'Hue', display_date: null, summary: null },
      ];

      const result = staysReconciler.updateDayAccommodation(
        itinerary,
        0,
        {
          accommodation_id: 'hotel-metropole',
          accommodation_name: 'Sofitel Legend Metropole',
          room_type: 'Heritage Wing Suite',
        },
        '2026-11-01'
      );

      assert.equal(result.itinerary[0].accommodation_id, 'hotel-metropole');
      assert.equal(result.itinerary[1].accommodation_id, 'hotel-metropole');
      assert.equal(result.itinerary[2].accommodation_id ?? null, null);

      assert.equal(result.stays.length, 1);
      assert.equal(result.stays[0].day_start, 1);
      assert.equal(result.stays[0].day_end, 2);
      assert.equal(result.stays[0].nights, 2);
    });
  });
});
