import { resolvePublicationPdf } from '../../../../lib/publicQuotationApi';

// Release-keyed PDF door (Plan 16.2 F-02/D3): the release id never changes
// meaning for an already-issued URL, so this is the only PDF response
// allowed to carry `immutable`. The slug-keyed `/pdf/download` doors are a
// stable entry point that 302s here — never cache-frozen themselves.
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ releaseId: string }> },
) {
  const { releaseId } = await params;
  const pdf = await resolvePublicationPdf(releaseId);
  if (!pdf) return new Response(null, { status: 404 });
  return new Response(pdf, {
    headers: {
      'Content-Type': 'application/pdf',
      'Content-Disposition': `attachment; filename="quotation-${releaseId}.pdf"`,
      'Cache-Control': 'public, max-age=31536000, immutable',
      // Excluded from proxy.ts's matcher (starts with `media`), so this
      // route sets its own defense-in-depth cache-isolation header (F-21).
      Vary: 'Host',
    },
  });
}
