import test from 'node:test';
import assert from 'node:assert/strict';
import { resolveMapTileProviders, resolveMapTileRasterTreatment } from '../mapTileStyles.ts';

test('PDF map style is pinned to a label-free raster', () => {
  const providers = resolveMapTileProviders('carto-parchment-nolabels-pdf-v1');

  assert.equal(providers?.length, 1);
  assert.equal(providers?.[0]?.id, 'carto-voyager-nolabels');
  assert.match(providers?.[0]?.url(6, 53, 28) ?? '', /rastertiles\/voyager_nolabels/);
  assert.equal(resolveMapTileRasterTreatment('carto-parchment-nolabels-pdf-v1'), 'parchment');
});

test('screen map style retains independent provider fallback', () => {
  const providers = resolveMapTileProviders('google-classic-v1');

  assert.deepEqual(providers?.map((provider) => provider.id), [
    'google-classic',
    'carto-voyager',
    'openstreetmap',
  ]);
  assert.equal(resolveMapTileRasterTreatment('google-classic-v1'), 'passthrough');
});

test('unsupported tile styles are rejected rather than silently substituted', () => {
  assert.equal(resolveMapTileProviders('carto-voyager-nolabels-pdf-v1'), null);
  assert.equal(resolveMapTileProviders('google-classic-pdf-v1'), null);
  assert.equal(resolveMapTileProviders(null), null);
});
