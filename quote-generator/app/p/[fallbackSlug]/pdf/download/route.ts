import { resolvePublicFallbackQuotation } from '../../../../../lib/publicQuotationApi';

// Stable entry point (Plan 16.2 F-02/D3) — see the branded `/q/.../pdf/download`
// route for the full rationale. Always `no-store`; redirect to the
// release-keyed door that is safe to cache forever.
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ fallbackSlug: string }> },
) {
  const { fallbackSlug } = await params;
  const quotation = await resolvePublicFallbackQuotation(fallbackSlug);
  if (!quotation) return new Response(null, { status: 404 });
  return new Response(null, {
    status: 302,
    headers: {
      Location: `/media/${quotation.release.id}/pdf`,
      'Cache-Control': 'no-store',
    },
  });
}
