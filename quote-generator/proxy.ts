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
 * as an HTTP 404 before any brochure response is streamed.
 */
export async function proxy(request: NextRequest) {
  const match = request.nextUrl.pathname.match(/^\/(en|vi|ar)\/q\/([^/]+)(?:\/.*)?$/);
  if (!match) return NextResponse.next();

  const [, locale, slug] = match;
  const hostname = request.headers.get('x-forwarded-host')?.split(',')[0]?.trim()
    ?? request.headers.get('host')?.split(',')[0]?.trim()
    ?? '';
  const resolvedHostname = hostname.replace(/:\d+$/, '').toLowerCase();
  if (!resolvedHostname) return new NextResponse(null, { status: 404 });

  const search = new URLSearchParams({ hostname: resolvedHostname, locale, slug });
  try {
    const response = await fetch(`${INTERNAL_API_BASE}/api/internal/v2/public-quotations/resolve?${search}`, {
      headers: serviceHeaders(),
      cache: 'no-store',
    });
    if (response.status === 404) return new NextResponse(null, { status: 404 });
    if (!response.ok) return new NextResponse(null, { status: 503 });
  } catch {
    return new NextResponse(null, { status: 503 });
  }
  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next|media|api|internal).*)'],
};
