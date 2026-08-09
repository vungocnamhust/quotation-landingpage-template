import { NextResponse } from 'next/server';

const TILE_PROVIDERS = [
  (z: number, x: number, y: number) => `https://mt1.google.com/vt/lyrs=m&x=${x}&y=${y}&z=${z}&hl=vi`,
  (z: number, x: number, y: number) => `https://a.basemaps.cartocdn.com/rastertiles/voyager/${z}/${x}/${y}.png`,
  (z: number, x: number, y: number) => `https://tile.openstreetmap.org/${z}/${x}/${y}.png`,
] as const;

function parseTileCoordinate(value: string, maximum: number) {
  if (!/^\d+$/.test(value)) {
    return null;
  }
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed >= 0 && parsed < maximum ? parsed : null;
}

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ z: string; x: string; y: string }> },
) {
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

  for (const provider of TILE_PROVIDERS) {
    try {
      const upstream = await fetch(provider(zoom, x, y), {
        headers: { Accept: 'image/avif,image/webp,image/png,image/*;q=0.8' },
        signal: AbortSignal.timeout(5_000),
      });
      const contentType = upstream.headers.get('content-type') ?? '';
      if (!upstream.ok || !contentType.startsWith('image/')) {
        continue;
      }
      return new NextResponse(upstream.body, {
        headers: {
          'Content-Type': contentType,
          'Cache-Control': 'public, max-age=86400, s-maxage=604800, stale-while-revalidate=2592000',
        },
      });
    } catch {
      // Try the independent provider below. Both failed hosts yield a 502.
    }
  }

  return NextResponse.json({ message: 'Map tiles are temporarily unavailable.' }, { status: 502 });
}
