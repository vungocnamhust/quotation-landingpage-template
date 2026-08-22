import { NextResponse } from 'next/server';
import { prepareMapTileRaster } from '../../../../../../lib/mapTileRaster.ts';
import { resolveMapTileProviders, resolveMapTileRasterTreatment } from '../../../../../../lib/mapTileStyles.ts';

export const runtime = 'nodejs';

function parseTileCoordinate(value: string, maximum: number) {
  if (!/^\d+$/.test(value)) {
    return null;
  }
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed >= 0 && parsed < maximum ? parsed : null;
}

export async function GET(
  request: Request,
  { params }: { params: Promise<{ z: string; x: string; y: string }> },
) {
  const style = new URL(request.url).searchParams.get('style');
  const providers = resolveMapTileProviders(style);
  const rasterTreatment = resolveMapTileRasterTreatment(style);
  if (!providers || !rasterTreatment) {
    return NextResponse.json({ message: 'Unsupported map tile style.' }, { status: 400 });
  }

  const { z: rawZoom, x: rawX, y: rawY } = await params;
  const zoom = parseTileCoordinate(rawZoom, 21);
  if (zoom === null) {
    return new NextResponse(null, { status: 404 });
  }

  const tileLimit = 2 ** zoom;
  const x = parseTileCoordinate(rawX, tileLimit);
  const y = parseTileCoordinate(rawY, tileLimit);
  if (x === null || y === null) {
    return new NextResponse(null, { status: 404 });
  }

  for (const provider of providers) {
    try {
      const upstream = await fetch(provider.url(zoom, x, y), {
        headers: { Accept: 'image/avif,image/webp,image/png,image/*;q=0.8' },
        signal: AbortSignal.timeout(5_000),
      });
      const contentType = upstream.headers.get('content-type') ?? '';
      if (!upstream.ok || !contentType.startsWith('image/')) {
        continue;
      }
      const raster = await prepareMapTileRaster(
        await upstream.arrayBuffer(),
        contentType,
        rasterTreatment,
      );
      return new NextResponse(raster.body, {
        headers: {
          'Content-Type': raster.contentType,
          'X-Map-Tile-Provider': provider.id,
          'Cache-Control': 'public, max-age=86400, s-maxage=604800, stale-while-revalidate=2592000',
        },
      });
    } catch {
      // Screen styles can continue with an independent provider. PDF style has
      // only CARTO no-label, so this exits with a visible 502 rather than drift.
    }
  }

  return NextResponse.json({ message: 'Map tiles are temporarily unavailable.' }, { status: 502 });
}
