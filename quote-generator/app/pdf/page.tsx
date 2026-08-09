import { notFound } from 'next/navigation';
import DisplayPage from '../../components/DisplayPage';
import { buildDisplayDocumentFromQuoteDocument } from '../../display/runtimePageBuilder';
import { resolvePublicationRelease } from '../../lib/publicQuotationApi';

export default async function PdfPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const releaseId = typeof params.releaseId === 'string' ? params.releaseId : '';
  if (!releaseId) notFound();
  const payload = await resolvePublicationRelease(releaseId);
  if (!payload) notFound();
  const documentModel = buildDisplayDocumentFromQuoteDocument({
    document: payload.document,
    brandProfile: payload.brandProfile,
    lang: payload.locale,
    viewMode: 'pdf',
  });

  return (
    <>
      <script
        id="route-state-sync-pdf"
        dangerouslySetInnerHTML={{
          __html: `document.documentElement.setAttribute('data-brand', ${JSON.stringify(payload.brandProfile.id)});document.documentElement.setAttribute('data-theme', 'brochure');document.documentElement.setAttribute('data-view-mode', 'pdf');document.documentElement.lang=${JSON.stringify(payload.locale)};`,
        }}
      />
      <DisplayPage documentModel={documentModel} />
    </>
  );
}
