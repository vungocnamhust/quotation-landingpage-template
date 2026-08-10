import { resolvePublicationPdf, resolvePublicFallbackQuotation } from '../../../../../lib/publicQuotationApi';

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ fallbackSlug: string }> },
) {
  const { fallbackSlug } = await params;
  const quotation = await resolvePublicFallbackQuotation(fallbackSlug);
  if (!quotation) return new Response(null, { status: 404 });
  const pdf = await resolvePublicationPdf(quotation.release.id);
  if (!pdf) return new Response(null, { status: 404 });
  return new Response(pdf, {
    headers: {
      'Content-Type': 'application/pdf',
      'Content-Disposition': `attachment; filename="quotation-${fallbackSlug}.pdf"`,
      'Cache-Control': 'public, max-age=31536000, immutable',
    },
  });
}
