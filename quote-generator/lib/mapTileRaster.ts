import sharp from 'sharp';

import type { MapTileRasterTreatment } from './mapTileStyles.ts';

export const PARCHMENT_TILE_CONTENT_TYPE = 'image/png';

/**
 * Produces a deterministic warm-neutral raster before Leaflet or Chromium
 * compose it. CARTO's cyan water is therefore never part of the PDF input.
 */
export async function prepareMapTileRaster(
  source: ArrayBuffer,
  contentType: string,
  treatment: MapTileRasterTreatment,
): Promise<{ body: ArrayBuffer; contentType: string }> {
  if (treatment === 'passthrough') {
    return { body: source, contentType };
  }

  const output = await sharp(Buffer.from(source))
    .grayscale()
    .linear(1.12, -15)
    .recomb([
      [1, 0, 0],
      [0, 0.965, 0],
      [0, 0, 0.88],
    ])
    .png()
    .toBuffer();

  const body = new ArrayBuffer(output.byteLength);
  new Uint8Array(body).set(output);
  return { body, contentType: PARCHMENT_TILE_CONTENT_TYPE };
}
