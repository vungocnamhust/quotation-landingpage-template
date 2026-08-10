import { notFound } from 'next/navigation';
import DisplayPage from '../../../../components/DisplayPage';
import { buildDisplayDocumentFromQuoteDocument } from '../../../../display/runtimePageBuilder';
import { resolvePublicFallbackQuotation } from '../../../../lib/publicQuotationApi';

export const dynamic = 'force-dynamic';
export const revalidate = 0;
export const fetchCache = 'force-no-store';

export default async function PublicFallbackQuotationPdfPage({
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
    viewMode: 'pdf',
  })} />;
}
