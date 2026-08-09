import { headers } from 'next/headers';
import { notFound } from 'next/navigation';
import DisplayPage from '../../../../components/DisplayPage';
import { buildDisplayDocumentFromQuoteDocument } from '../../../../display/runtimePageBuilder';
import { LANGUAGE_CODES, type LanguageCode } from '../../../../display/contracts';
import { resolvePublicQuotation } from '../../../../lib/publicQuotationApi';

export const dynamic = 'force-dynamic';
// Publication targets may be unpublished or brand-disabled between requests.
// Keep this route out of Next's full-route/data caches so FastAPI's active
// target lookup is the sole authority for public visibility.
export const revalidate = 0;
export const fetchCache = 'force-no-store';

export default async function PublicQuotationPage({
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
  if (!hostname) notFound();
  const payload = await resolvePublicQuotation({ hostname, locale: locale as LanguageCode, slug });
  if (!payload) notFound();
  return <DisplayPage documentModel={buildDisplayDocumentFromQuoteDocument({
    document: payload.document,
    brandProfile: payload.brandProfile,
    lang: locale as LanguageCode,
    viewMode: 'desktop',
  })} />;
}
