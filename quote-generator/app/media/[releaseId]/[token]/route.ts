import { headers } from 'next/headers';
import { resolvePublicMedia } from '../../../../lib/publicQuotationApi';

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ releaseId: string; token: string }> },
) {
  const [{ releaseId, token }, headerStore] = await Promise.all([params, headers()]);
  const hostname = (headerStore.get('x-forwarded-host') ?? headerStore.get('host') ?? '')
    .split(',')[0]!
    .trim()
    .replace(/:\d+$/, '')
    .toLowerCase();
  if (!hostname) return new Response(null, { status: 404 });
  const media = await resolvePublicMedia(releaseId, token, hostname);
  if (!media) return new Response(null, { status: 404 });
  return new Response(media.bytes, {
    headers: {
      'Content-Type': media.contentType,
      'Cache-Control': 'public, max-age=31536000, immutable',
      // Excluded from proxy.ts's matcher (starts with `media`), so this
      // route sets its own defense-in-depth cache-isolation header (F-21).
      Vary: 'Host',
    },
  });
}
