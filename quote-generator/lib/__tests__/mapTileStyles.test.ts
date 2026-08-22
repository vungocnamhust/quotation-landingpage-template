import test from 'node:test';
import assert from 'node:assert/strict';
import { resolveMapTileProviders } from '../mapTileStyles.ts';

test('PDF map style is pinned to the prototype Google classic raster', () => {
  const providers = resolveMapTileProviders('google-classic-pdf-v1');

  assert.equal(providers?.length, 1);
  assert.equal(providers?.[0]?.id, 'google-classic');
  assert.match(providers?.[0]?.url(6, 53, 28) ?? '', /mt1\.google\.com\/vt\/lyrs=m/);
});

test('screen map style retains independent provider fallback', () => {
  const providers = resolveMapTileProviders('google-classic-v1');

  assert.deepEqual(providers?.map((provider) => provider.id), [
    'google-classic',
    'carto-voyager',
    'openstreetmap',
  ]);
});

test('unsupported tile styles are rejected rather than silently substituted', () => {
  assert.equal(resolveMapTileProviders('luxury-editorial-v1'), null);
  assert.equal(resolveMapTileProviders(null), null);
});
