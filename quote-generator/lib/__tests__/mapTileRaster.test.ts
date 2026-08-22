import test from 'node:test';
import assert from 'node:assert/strict';
import sharp from 'sharp';

import { PARCHMENT_TILE_CONTENT_TYPE, prepareMapTileRaster } from '../mapTileRaster.ts';

test('parchment PDF tile transform removes cyan while retaining an opaque PNG', async () => {
  const cyanTile = await sharp({
    create: {
      width: 2,
      height: 2,
      channels: 3,
      background: { r: 205, g: 229, b: 235 },
    },
  }).png().toBuffer();

  const transformed = await prepareMapTileRaster(
    cyanTile.buffer.slice(cyanTile.byteOffset, cyanTile.byteOffset + cyanTile.byteLength),
    'image/png',
    'parchment',
  );
  const decoded = await sharp(transformed.body).raw().toBuffer({ resolveWithObject: true });
  const [red, green, blue] = decoded.data;

  assert.equal(transformed.contentType, PARCHMENT_TILE_CONTENT_TYPE);
  assert.equal(decoded.info.channels, 3);
  assert.ok(red >= green && green >= blue, `Expected warm parchment RGB, received ${red}, ${green}, ${blue}`);
  assert.ok(red - blue >= 20, `Expected cyan to be materially removed, received ${red}, ${green}, ${blue}`);
});

test('screen tile transform is byte-preserving passthrough', async () => {
  const source = new Uint8Array([1, 2, 3, 4]);
  const transformed = await prepareMapTileRaster(source.buffer, 'image/webp', 'passthrough');

  assert.equal(transformed.contentType, 'image/webp');
  assert.deepEqual([...new Uint8Array(transformed.body)], [...source]);
});
