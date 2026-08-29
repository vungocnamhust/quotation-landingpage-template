import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import DisplayPage from '../../../components/DisplayPage';
import { buildDisplayDocumentFromQuoteDocument } from '../../../display/runtimePageBuilder';
import { resolvePublicFallbackQuotation } from '../../../lib/publicQuotationApi';

export const dynamic = 'force-dynamic';
export const revalidate = 0;
export const fetchCache = 'force-no-store';

// Plan 16.2 D9: the fallback URL is a dispensable backup, not the canonical
// address — it must never outrank a brand's own domain in search results.
export async function generateMetadata({
  params,
}: {
  params: Promise<{ fallbackSlug: string }>;
}): Promise<Metadata> {
  const { fallbackSlug } = await params;
  const payload = await resolvePublicFallbackQuotation(fallbackSlug);
  if (!payload) return {};
  const trip = payload.document.trip as { title?: string; lede?: string } | undefined;
  const title = trip?.title || payload.brandProfile.displayName;
  return {
    title,
    description: trip?.lede || undefined,
    // The fallback API does not resolve the branded public_slug, so this
    // route cannot point `canonical` at the branded URL — noindex is the
    // load-bearing signal that keeps search engines off this dispensable door.
    robots: { index: false, follow: false },
  };
}

export default async function PublicFallbackQuotationPage({
  params,
}: {
  params: Promise<{ fallbackSlug: string }>;
}) {
  const { fallbackSlug } = await params;
  const payload = await resolvePublicFallbackQuotation(fallbackSlug);
  if (!payload) notFound();
  return <DisplayPage documentModel={buildDisplayDocumentFromQuoteDocument({
    document: payload.document,
    brandProfile: payload.brandProfile,
    lang: payload.locale,
    viewMode: 'desktop',
  })} />;
}
