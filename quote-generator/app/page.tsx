import { headers } from 'next/headers';
import { notFound, redirect } from 'next/navigation';
import DisplayPage from '../components/DisplayPage';
import { buildDisplayDocumentFromQuoteDocument } from '../display/runtimePageBuilder';
import { LANGUAGE_CODES, type LanguageCode } from '../display/contracts';
import { resolvePublicQuotation } from '../lib/publicQuotationApi';

export const dynamic = 'force-dynamic';
export const revalidate = 0;
export const fetchCache = 'force-no-store';

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const headerStore = await headers();
  const locale = (typeof params.lang === 'string' ? params.lang : 'en') as LanguageCode;
  const slug = typeof params.slug === 'string' ? params.slug : '';
  if (!slug) {
    redirect('/workspace');
  }
  const hostname = (headerStore.get('x-forwarded-host') ?? headerStore.get('host') ?? '')
    .split(',')[0]!.trim().replace(/:\d+$/, '').toLowerCase();
  if (!hostname || !LANGUAGE_CODES.includes(locale)) notFound();
  const payload = await resolvePublicQuotation({ hostname, locale, slug });
  if (!payload) notFound();
  const documentModel = buildDisplayDocumentFromQuoteDocument({
    document: payload.document,
    brandProfile: payload.brandProfile,
    lang: locale,
    viewMode: 'desktop',
  });

  return <DisplayPage documentModel={documentModel} />;
}
