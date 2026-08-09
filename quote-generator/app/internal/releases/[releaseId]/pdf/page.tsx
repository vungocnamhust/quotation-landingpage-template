import { notFound } from 'next/navigation';
import DisplayPage from '../../../../../components/DisplayPage';
import { buildDisplayDocumentFromQuoteDocument } from '../../../../../display/runtimePageBuilder';
import { resolvePublicationRelease } from '../../../../../lib/publicQuotationApi';

/** Nginx exposes this route only to the internal PDF worker. */
export const dynamic = 'force-dynamic';

export default async function ReleasePdfPage({ params }: { params: Promise<{ releaseId: string }> }) {
  const { releaseId } = await params;
  const payload = await resolvePublicationRelease(releaseId);
  if (!payload) notFound();
  return <div data-render-ready="true"><DisplayPage documentModel={buildDisplayDocumentFromQuoteDocument({
    document: payload.document,
    brandProfile: payload.brandProfile,
    lang: payload.locale,
    viewMode: 'pdf',
  })} /></div>;
}
