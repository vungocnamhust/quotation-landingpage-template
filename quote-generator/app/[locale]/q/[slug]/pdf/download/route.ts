import { headers } from 'next/headers';
import { LANGUAGE_CODES, type LanguageCode } from '../../../../../../display/contracts';
import { resolvePublicQuotation } from '../../../../../../lib/publicQuotationApi';

// Stable entry point (Plan 16.2 F-02/D3): the slug never changes across
// republishes, so this door must never carry `immutable` — a browser/CDN
// that cached it that way would keep serving a superseded release's PDF for
// up to a year. Always `no-store`, and redirect to the release-keyed door
// that is safe to cache forever.
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ locale: string; slug: string }> },
) {
  const [{ locale, slug }, headerStore] = await Promise.all([params, headers()]);
  if (!LANGUAGE_CODES.includes(locale as LanguageCode)) return new Response(null, { status: 404 });
  const hostname = (headerStore.get('x-forwarded-host') ?? headerStore.get('host') ?? '')
    .split(',')[0]!
    .trim()
    .replace(/:\d+$/, '')
    .toLowerCase();
  const quotation = hostname
    ? await resolvePublicQuotation({ hostname, locale: locale as LanguageCode, slug })
    : null;
  if (!quotation) return new Response(null, { status: 404 });
  return new Response(null, {
    status: 302,
    headers: {
      Location: `/media/${quotation.release.id}/pdf`,
      'Cache-Control': 'no-store',
    },
  });
}
