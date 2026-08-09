import { headers } from 'next/headers';
import { LANGUAGE_CODES, type LanguageCode } from '../../../../../../display/contracts';
import { resolvePublicationPdf, resolvePublicQuotation } from '../../../../../../lib/publicQuotationApi';

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
  const pdf = await resolvePublicationPdf(quotation.release.id);
  if (!pdf) return new Response(null, { status: 404 });
  return new Response(pdf, {
    headers: {
      'Content-Type': 'application/pdf',
      'Content-Disposition': `attachment; filename="quotation-${slug}.pdf"`,
      'Cache-Control': 'public, max-age=31536000, immutable',
    },
  });
}
