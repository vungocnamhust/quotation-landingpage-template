import type { Metadata } from 'next';
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

async function resolvePageProps(locale: string, slug: string) {
  const headerStore = await headers();
  const hostname = (headerStore.get('x-forwarded-host') ?? headerStore.get('host') ?? '')
    .split(',')[0]!
    .trim()
    .replace(/:\d+$/, '')
    .toLowerCase();
  if (!LANGUAGE_CODES.includes(locale as LanguageCode) || !hostname) return null;
  return resolvePublicQuotation({ hostname, locale: locale as LanguageCode, slug });
}

// Plan 16.2 D9: brochure pages are per-brand, canonical public documents —
// title/OG/canonical must reflect the resolving brand's own hostname, not a
// static app-wide default.
export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}): Promise<Metadata> {
  const { locale, slug } = await params;
  const payload = await resolvePageProps(locale, slug);
  if (!payload) return {};
  const trip = payload.document.trip as { title?: string; lede?: string } | undefined;
  const title = trip?.title || payload.brandProfile.displayName;
  const description = trip?.lede || undefined;
  const canonical = `https://${payload.brandProfile.hostname}/${locale}/q/${slug}`;
  return {
    title,
    description,
    alternates: { canonical },
    openGraph: { title, description, url: canonical, siteName: payload.brandProfile.displayName },
  };
}

export default async function PublicQuotationPage({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}) {
  const { locale, slug } = await params;
  const payload = await resolvePageProps(locale, slug);
  if (!payload) notFound();
  return <DisplayPage documentModel={buildDisplayDocumentFromQuoteDocument({
    document: payload.document,
    brandProfile: payload.brandProfile,
    lang: locale as LanguageCode,
    viewMode: 'desktop',
  })} />;
}
