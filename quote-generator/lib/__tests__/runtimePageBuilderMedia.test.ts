import test from 'node:test';
import assert from 'node:assert/strict';

import { BRANDS_DATA } from '../../data/brandsData.ts';
import { buildDisplayDocumentFromQuoteDocument } from '../../display/runtimePageBuilder.ts';

const brand = BRANDS_DATA['vietnam-safar'];

function build(document: Record<string, unknown>) {
  return buildDisplayDocumentFromQuoteDocument({
    document,
    brandProfile: {
      id: 'vietnam_safar',
      displayName: brand.name,
      hostname: 'quotation.test',
      logoUrl: '/assets/brands/vietnam_safar.png',
      themeId: 'brochure',
      layoutVersion: 1,
      palette: brand.themeTokens.palette,
      radii: brand.themeTokens.radii,
    },
    lang: 'en',
    viewMode: 'desktop',
  });
}

/**
 * Plan 16.1 §2.1/§3.1 (M3.1): one precedence rule for every media slot —
 * canonical fact media always wins; `presentation.mediaOverrides` is a
 * read-only fallback for documents written before the D1 single-store model,
 * never a competing source of truth. These tests cover the 6 slot families
 * that historically had inconsistent precedence.
 */

test('assets.hero: canonical wins over a legacy mediaOverrides value', () => {
  const model = build({
    assets: { hero: { url: 'canonical-hero.jpg' } },
    presentation: { mediaOverrides: { 'assets.hero': { url: 'legacy-hero.jpg' } } },
  });
  assert.equal(model.page.hero.backgroundImage, 'canonical-hero.jpg');
});

test('assets.hero: falls back to mediaOverrides when canonical is empty (published-snapshot compatibility)', () => {
  const model = build({
    presentation: { mediaOverrides: { 'assets.hero': { url: 'legacy-hero.jpg' } } },
  });
  assert.equal(model.page.hero.backgroundImage, 'legacy-hero.jpg');
});

test('assets.itineraryDivider: canonical wins over mediaOverrides', () => {
  const model = build({
    assets: { itineraryDivider: { url: 'canonical-divider.jpg' } },
    presentation: { mediaOverrides: { 'assets.itineraryDivider': { url: 'legacy-divider.jpg' } } },
  });
  assert.equal(model.page.itineraryDivider.image, 'canonical-divider.jpg');
});

test('assets.itineraryDivider: falls back to mediaOverrides when empty', () => {
  const model = build({
    presentation: { mediaOverrides: { 'assets.itineraryDivider': { url: 'legacy-divider.jpg' } } },
  });
  assert.equal(model.page.itineraryDivider.image, 'legacy-divider.jpg');
});

test('assets.staysDivider: canonical wins over mediaOverrides', () => {
  const model = build({
    assets: { staysDivider: { url: 'canonical-stays.jpg' } },
    presentation: { mediaOverrides: { 'assets.staysDivider': { url: 'legacy-stays.jpg' } } },
  });
  assert.equal(model.page.staysDivider.image, 'canonical-stays.jpg');
});

test('assets.staysDivider: falls back to mediaOverrides before the hotel-photo default', () => {
  const model = build({
    presentation: { mediaOverrides: { 'assets.staysDivider': { url: 'legacy-stays.jpg' } } },
    stays: { hotels: [{ hotelImage: { url: 'hotel-photo.jpg' } }] },
  });
  assert.equal(model.page.staysDivider.image, 'legacy-stays.jpg');
});

test('assets.hotelDivider: canonical wins over mediaOverrides', () => {
  const model = build({
    assets: { hotelDivider: { url: 'canonical-hotel-divider.jpg' } },
    presentation: { mediaOverrides: { 'assets.hotelDivider': { url: 'legacy-hotel-divider.jpg' } } },
  });
  assert.equal(model.page.journeyTogetherDivider.image, 'canonical-hotel-divider.jpg');
});

test('assets.hotelDivider: falls back to mediaOverrides when empty', () => {
  const model = build({
    presentation: { mediaOverrides: { 'assets.hotelDivider': { url: 'legacy-hotel-divider.jpg' } } },
  });
  assert.equal(model.page.journeyTogetherDivider.image, 'legacy-hotel-divider.jpg');
});

test('itinerary.days.*.gallery: canonical carousel wins over mediaOverrides', () => {
  const model = build({
    itinerary: {
      days: [{
        dayNumber: 1,
        images: { carousel: [{ url: 'canonical-1.jpg' }, { url: 'canonical-2.jpg' }, { url: 'canonical-3.jpg' }] },
      }],
    },
    presentation: { mediaOverrides: { 'itinerary.days.0.gallery': [{ url: 'legacy-1.jpg' }] } },
  });
  assert.deepEqual(model.page.itinerary.days[0].carouselImages, ['canonical-1.jpg', 'canonical-2.jpg', 'canonical-3.jpg']);
});

test('itinerary.days.*.gallery: falls back to mediaOverrides when the canonical carousel is empty', () => {
  const model = build({
    itinerary: { days: [{ dayNumber: 1 }] },
    presentation: { mediaOverrides: { 'itinerary.days.0.gallery': [{ url: 'legacy-1.jpg' }, { url: 'legacy-2.jpg' }] } },
  });
  assert.deepEqual(model.page.itinerary.days[0].carouselImages, ['legacy-1.jpg', 'legacy-2.jpg']);
});

test('stays.hotels.*.hotelImage and roomImage: canonical wins over mediaOverrides', () => {
  const model = build({
    stays: { hotels: [{ hotelImage: { url: 'canonical-hotel.jpg' }, roomImage: { url: 'canonical-room.jpg' } }] },
    presentation: {
      mediaOverrides: {
        'stays.hotels.0.hotelImage': { url: 'legacy-hotel.jpg' },
        'stays.hotels.0.roomImage': { url: 'legacy-room.jpg' },
      },
    },
  });
  assert.equal(model.page.hotels.cards[0].hotelImage, 'canonical-hotel.jpg');
  assert.equal(model.page.hotels.cards[0].roomImage, 'canonical-room.jpg');
});

test('stays.hotels.*.hotelImage: falls back to mediaOverrides when canonical is empty', () => {
  const model = build({
    stays: { hotels: [{}] },
    presentation: { mediaOverrides: { 'stays.hotels.0.hotelImage': { url: 'legacy-hotel.jpg' } } },
  });
  assert.equal(model.page.hotels.cards[0].hotelImage, 'legacy-hotel.jpg');
});

test('designer.image: canonical wins over mediaOverrides', () => {
  const model = build({
    designer: { image: { url: 'canonical-avatar.jpg' } },
    presentation: { mediaOverrides: { 'designer.image': { url: 'legacy-avatar.jpg' } } },
  });
  assert.equal(model.page.designer.avatar, 'canonical-avatar.jpg');
});

test('designer.image: falls back to mediaOverrides when empty', () => {
  const model = build({
    presentation: { mediaOverrides: { 'designer.image': { url: 'legacy-avatar.jpg' } } },
  });
  assert.equal(model.page.designer.avatar, 'legacy-avatar.jpg');
});
