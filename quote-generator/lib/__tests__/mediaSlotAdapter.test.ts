import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { derivePickerTarget, matchSlotDescriptor, type MediaSlotDescriptor } from '../rules/mediaSlotAdapter.ts';

const HERO_SLOT: MediaSlotDescriptor = {
  fieldTemplate: 'assets.hero',
  source: '/assets/hero',
  editorRoute: 'hero',
  pickerContext: 'library',
  minItems: 1,
  maxItems: 1,
  requiredForPublish: true,
};

const GALLERY_SLOT: MediaSlotDescriptor = {
  fieldTemplate: 'itinerary.days.*.gallery',
  source: '/itinerary/days/*/images/carousel',
  editorRoute: 'itinerary',
  pickerContext: 'destination',
  minItems: 3,
  maxItems: 3,
  requiredForPublish: true,
};

const HOTEL_IMAGE_SLOT: MediaSlotDescriptor = {
  fieldTemplate: 'stays.hotels.*.hotelImage',
  source: '/stays/hotels/*/hotelImage',
  editorRoute: 'stays',
  pickerContext: 'accommodation',
  minItems: 1,
  maxItems: 1,
  requiredForPublish: true,
};

const REGISTRY = [HERO_SLOT, GALLERY_SLOT, HOTEL_IMAGE_SLOT];

describe('mediaSlotAdapter.matchSlotDescriptor', () => {
  it('matches a non-wildcard field exactly', () => {
    const result = matchSlotDescriptor(REGISTRY, 'assets.hero', '/assets/hero');
    assert.deepEqual(result, { slot: HERO_SLOT, fieldId: 'assets.hero' });
  });

  it('concretizes a wildcard field from the resolved source', () => {
    const result = matchSlotDescriptor(REGISTRY, 'itinerary.days.*.gallery', '/itinerary/days/2/images/carousel');
    assert.deepEqual(result, { slot: GALLERY_SLOT, fieldId: 'itinerary.days.2.gallery' });
  });

  it('returns null for a selection that is not a registered media field — no hardcoded fallback slot', () => {
    const result = matchSlotDescriptor(REGISTRY, 'hero.bannerImage', '/hero/bannerImage');
    assert.equal(result, null);
  });
});

describe('mediaSlotAdapter.derivePickerTarget', () => {
  it('derives a destination context and prefix for a day gallery slot', () => {
    const document = {
      itinerary: { days: [{}, { destinationRef: { id: 'dst_hanoi', slug: 'ha-noi', mediaPrefix: 'vietnam/north/ha-noi' } }] },
    };
    const target = derivePickerTarget(document, 'itinerary.days.1.gallery');
    assert.equal(target.initialPrefix, 'vietnam/north/ha-noi');
    assert.deepEqual(target.context, { kind: 'destination', destinationId: 'dst_hanoi' });
  });

  it('falls back to destination/{slug} when no mediaPrefix is set', () => {
    const document = { itinerary: { days: [{ destinationRef: { id: 'dst_hanoi', slug: 'ha-noi' } }] } };
    const target = derivePickerTarget(document, 'itinerary.days.0.gallery');
    assert.equal(target.initialPrefix, 'destination/ha-noi');
  });

  it('derives an accommodation context with the hotel name for a hotel image slot', () => {
    const document = {
      stays: { hotels: [{ name: 'Metropole Hanoi', destinationRef: { id: 'dst_hanoi' } }] },
    };
    const target = derivePickerTarget(document, 'stays.hotels.0.hotelImage');
    assert.equal(target.initialPrefix, 'accommodations');
    assert.deepEqual(target.context, { kind: 'accommodation', destinationId: 'dst_hanoi', accommodationName: 'Metropole Hanoi' });
  });

  it('derives a prefix from the first day for a global asset slot', () => {
    const document = { itinerary: { days: [{ destinationRef: { mediaPrefix: 'vietnam/north/ha-noi' } }] } };
    const target = derivePickerTarget(document, 'assets.hero');
    assert.equal(target.initialPrefix, 'vietnam/north/ha-noi');
    assert.equal(target.context, undefined);
  });

  it('returns an empty target for an unrecognized fieldId', () => {
    assert.deepEqual(derivePickerTarget({}, 'unknown.field'), {});
  });
});
