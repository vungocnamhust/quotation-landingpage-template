import { cache } from 'react';
import type { LanguageCode } from '../display/contracts.ts';
import type { BrandRenderProfile } from '../display/types.ts';

const INTERNAL_API_BASE = process.env.QUOTATION_INTERNAL_API_URL
  ?? process.env.NEXT_PUBLIC_QUOTATION_API_URL
  ?? 'http://localhost:8111';

function serviceHeaders() {
  const token =
    process.env.QUOTE_SERVICE_TOKEN ??
    (process.env.NODE_ENV === 'development' ? 'local-ci-service-token' : '');
  if (!token) {
    throw new Error('QUOTE_SERVICE_TOKEN must be configured for public quotation rendering.');
  }
  return { 'X-Quote-Service-Token': token };
}

export type PublicQuotationPayload = {
  document: Record<string, unknown>;
  brandProfile: BrandRenderProfile;
  release: { id: string; number: number; documentRevision: number };
};

export type PublicFallbackQuotationPayload = PublicQuotationPayload & {
  locale: LanguageCode;
};

export type WorkspaceWorkflowBootstrap = {
  locale: LanguageCode;
  currentRevision: number;
};

export type EditorBrandBootstrap = {
  brandProfile: BrandRenderProfile;
};

export const resolveWorkspaceWorkflow = cache(async function resolveWorkspaceWorkflow(
  quotationId: string,
): Promise<WorkspaceWorkflowBootstrap | null> {
  const response = await fetch(
    `${INTERNAL_API_BASE}/api/internal/v2/quotations/${encodeURIComponent(quotationId)}/workflow`,
    { headers: serviceHeaders(), cache: 'no-store' },
  );
  if (response.status === 404) return null;
  if (!response.ok) throw new Error('Unable to resolve quotation workspace locale.');
  return response.json() as Promise<WorkspaceWorkflowBootstrap>;
});

export const resolveEditorBrandBootstrap = cache(async function resolveEditorBrandBootstrap(): Promise<EditorBrandBootstrap | null> {
  const response = await fetch(`${INTERNAL_API_BASE}/api/internal/v2/brands/editor-bootstrap`, {
    headers: serviceHeaders(),
    cache: 'no-store',
  });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error('Unable to resolve editor brand configuration.');
  return response.json() as Promise<EditorBrandBootstrap>;
});

// Public visibility can change through restore, unpublish, or brand disable.
// React's process-lifetime cache would keep an already-resolved release public
// even though the API correctly returns 404 after that state transition.
export async function resolvePublicQuotation({
  hostname,
  locale,
  slug,
}: {
  hostname: string;
  locale: LanguageCode;
  slug: string;
}): Promise<PublicQuotationPayload | null> {
  const search = new URLSearchParams({ hostname, locale, slug });
  const response = await fetch(`${INTERNAL_API_BASE}/api/internal/v2/public-quotations/resolve?${search}`, {
    headers: serviceHeaders(),
    cache: 'no-store',
  });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error('Unable to resolve published quotation.');
  return response.json() as Promise<PublicQuotationPayload>;
}

export async function resolvePublicFallbackQuotation(
  fallbackSlug: string,
): Promise<PublicFallbackQuotationPayload | null> {
  const response = await fetch(
    `${INTERNAL_API_BASE}/api/internal/v2/public-quotations/fallback/${encodeURIComponent(fallbackSlug)}`,
    { headers: serviceHeaders(), cache: 'no-store' },
  );
  if (response.status === 404) return null;
  if (!response.ok) throw new Error('Unable to resolve fallback published quotation.');
  return response.json() as Promise<PublicFallbackQuotationPayload>;
}

export const resolvePublicationRelease = cache(async function resolvePublicationRelease(releaseId: string): Promise<(PublicQuotationPayload & { locale: LanguageCode }) | null> {
  const response = await fetch(`${INTERNAL_API_BASE}/api/internal/v2/public-quotations/releases/${encodeURIComponent(releaseId)}`, {
    headers: serviceHeaders(),
    cache: 'no-store',
  });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error('Unable to resolve publication release.');
  return response.json() as Promise<PublicQuotationPayload & { locale: LanguageCode }>;
});

export async function resolvePublicMedia(releaseId: string, token: string, hostname: string) {
  const search = new URLSearchParams({ hostname });
  const response = await fetch(`${INTERNAL_API_BASE}/api/internal/v2/public-media/${encodeURIComponent(releaseId)}/${encodeURIComponent(token)}?${search}`, {
    headers: serviceHeaders(),
    cache: 'force-cache',
  });
  if (!response.ok) return null;
  return {
    bytes: await response.arrayBuffer(),
    contentType: response.headers.get('content-type') ?? 'application/octet-stream',
  };
}

export async function resolvePublicationPdf(releaseId: string) {
  const response = await fetch(`${INTERNAL_API_BASE}/api/internal/v2/public-pdfs/${encodeURIComponent(releaseId)}`, {
    headers: serviceHeaders(),
    cache: 'force-cache',
  });
  if (!response.ok) return null;
  return await response.arrayBuffer();
}
