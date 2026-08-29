import { NextResponse, type NextRequest } from 'next/server';

const INTERNAL_API_BASE = process.env.QUOTATION_INTERNAL_API_URL
  ?? process.env.NEXT_PUBLIC_QUOTATION_API_URL
  ?? 'http://localhost:8111';

function serviceHeaders(): Record<string, string> {
  const token = process.env.QUOTE_SERVICE_TOKEN;
  return token ? { 'X-Quote-Service-Token': token } : {};
}

/**
 * A streamed App Router `notFound()` can already have committed a 200 status
 * through an ancestor loading boundary. Public publication visibility cannot
 * rely on that rendering detail: unpublish and brand disable must take effect
 * as an HTTP 404 before any brochure response is streamed. This gate covers
 * both the branded `/{locale}/q/{slug}` route and the global fallback
 * `/p/{fallbackSlug}` route (Plan 16.2 F-19) — a quotation removed from
 * publication must 404 on both doors, not just the branded one.
 */
export async function proxy(request: NextRequest) {
  const match = request.nextUrl.pathname.match(/^\/(?:(en|vi|ar)\/q|p)\/([^/]+)(?:\/.*)?$/);
  if (!match) return NextResponse.next();

  const [, locale, slug] = match;
  const hostname = request.headers.get('x-forwarded-host')?.split(',')[0]?.trim()
    ?? request.headers.get('host')?.split(',')[0]?.trim()
    ?? '';
  const resolvedHostname = hostname.replace(/:\d+$/, '').toLowerCase();
  if (!resolvedHostname) return new NextResponse(null, { status: 404 });

  const preflightUrl = locale
    ? `${INTERNAL_API_BASE}/api/internal/v2/public-quotations/resolve?${new URLSearchParams({ hostname: resolvedHostname, locale, slug })}`
    : `${INTERNAL_API_BASE}/api/internal/v2/public-quotations/fallback/${encodeURIComponent(slug)}`;
  try {
    const response = await fetch(preflightUrl, {
      headers: serviceHeaders(),
      cache: 'no-store',
    });
    if (response.status === 404) return new NextResponse(null, { status: 404 });
    if (!response.ok) return new NextResponse(null, { status: 503 });
  } catch {
    return new NextResponse(null, { status: 503 });
  }
  const response = NextResponse.next();
  // Defense-in-depth cache isolation (F-21): a CDN/reverse-proxy that keys
  // its cache without the Host header could otherwise serve one brand's
  // brochure on another brand's domain.
  response.headers.set('Vary', 'Host');
  return response;
}

export const config = {
  matcher: ['/((?!_next|media|api|internal).*)'],
};
