import test from 'node:test';
import assert from 'node:assert/strict';
import {
  matchDestinationSlug,
  resolveDestination,
  removeDiacritics,
} from '../rules/destinationRules.ts';

test('removeDiacritics correctly strips Vietnamese accents', () => {
  assert.equal(removeDiacritics('Hạ Long'), 'Ha Long');
  assert.equal(removeDiacritics('Đà Nẵng'), 'Da Nang');
  assert.equal(removeDiacritics('Hồ Chí Minh'), 'Ho Chi Minh');
  assert.equal(removeDiacritics('Vịnh Hạ Long'), 'Vinh Ha Long');
});

test('matchDestinationSlug resolves all aliases of Ha Long Bay to quang-ninh', () => {
  const halongAliases = [
    'halong',
    'Ha Long',
    'ha long',
    'Hạ Long',
    'hạ long',
    'Halong Bay',
    'ha long bay',
    'Vịnh Hạ Long',
    'vinh ha long',
    'quang-ninh',
    'quang ninh',
    'Quảng Ninh',
    'cát bà',
    'cat ba',
    'lan hạ',
    'lan ha bay',
    'bái tử long',
  ];

  for (const alias of halongAliases) {
    const slug = matchDestinationSlug(alias);
    assert.equal(slug, 'quang-ninh', `Failed to match alias '${alias}' to 'quang-ninh'`);
  }
});

test('resolveDestination returns full canonical profile and exact GPS coordinates for Ha Long Bay', () => {
  const dest = resolveDestination('Halong');
  assert.ok(dest);
  assert.equal(dest.slug, 'quang-ninh');
  assert.equal(dest.canonicalName, 'Ha Long Bay');
  assert.equal(dest.country, 'vietnam');
  assert.equal(dest.region, 'north');
  assert.equal(dest.province, 'quang-ninh');
  assert.deepEqual(dest.coordinates, [20.9599, 107.0436]);
});

test('resolveDestination correctly resolves key nationwide gateways and excursion destinations', () => {
  // Ho Chi Minh City / Saigon
  const hcm = resolveDestination('Saigon');
  assert.ok(hcm);
  assert.equal(hcm.slug, 'ho-chi-minh');
  assert.equal(hcm.canonicalName, 'Ho Chi Minh City');

  // Hanoi
  const hanoi = resolveDestination('Hà Nội');
  assert.ok(hanoi);
  assert.equal(hanoi.slug, 'ha-noi');
  assert.equal(hanoi.canonicalName, 'Hanoi');

  // Ninh Binh / Trang An
  const nb = resolveDestination('Tràng An');
  assert.ok(nb);
  assert.equal(nb.slug, 'ninh-binh');
  assert.equal(nb.canonicalName, 'Ninh Binh');

  // Mekong Delta
  const mekong = resolveDestination('Đồng Bằng Sông Cửu Long');
  assert.ok(mekong);
  assert.equal(mekong.slug, 'mekong');
  assert.equal(mekong.canonicalName, 'Mekong Delta');

  // Hoi An / Quang Nam
  const hoian = resolveDestination('Hội An');
  assert.ok(hoian);
  assert.equal(hoian.slug, 'quang-nam');
  assert.equal(hoian.canonicalName, 'Hoi An');

  // Da Nang
  const danang = resolveDestination('Bà Nà Hills');
  assert.ok(danang);
  assert.equal(danang.slug, 'da-nang');
  assert.equal(danang.canonicalName, 'Da Nang');

  // Sapa
  const sapa = resolveDestination('Fansipan');
  assert.ok(sapa);
  assert.equal(sapa.slug, 'lao-cai');
  assert.equal(sapa.canonicalName, 'Sapa');
});
