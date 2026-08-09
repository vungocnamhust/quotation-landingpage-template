import { headers } from 'next/headers';
import { notFound } from 'next/navigation';
import DisplayPage from '../../../../../components/DisplayPage';
import { buildDisplayDocumentFromQuoteDocument } from '../../../../../display/runtimePageBuilder';
import { LANGUAGE_CODES, type LanguageCode } from '../../../../../display/contracts';
import { resolvePublicQuotation } from '../../../../../lib/publicQuotationApi';

/** Internal Chromium worker prints this React route; it never falls back to Jinja. */
export const dynamic = 'force-dynamic';
// PDF rendering must resolve the active public target at request time too.
export const revalidate = 0;
export const fetchCache = 'force-no-store';

export default async function PublicQuotationPdfPage({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}) {
  const [{ locale, slug }, headerStore] = await Promise.all([params, headers()]);
  if (!LANGUAGE_CODES.includes(locale as LanguageCode)) notFound();
  const hostname = (headerStore.get('x-forwarded-host') ?? headerStore.get('host') ?? '')
    .split(',')[0]!
    .trim()
    .replace(/:\d+$/, '')
    .toLowerCase();
  const payload = hostname
    ? await resolvePublicQuotation({ hostname, locale: locale as LanguageCode, slug })
    : null;
  if (!payload) notFound();
  return <DisplayPage documentModel={buildDisplayDocumentFromQuoteDocument({
    document: payload.document,
    brandProfile: payload.brandProfile,
    lang: locale as LanguageCode,
    viewMode: 'pdf',
  })} />;
}
