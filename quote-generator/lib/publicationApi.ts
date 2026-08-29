// Plan 16.2 D8/PB3.1: single home for publish/publication-target/job calls.
// Before this module the same three fetches were duplicated inline across
// QuotationWorkspaceClient.tsx and PublicationTargetManager.tsx.
import { quotationFetch } from './apiError.ts';

export const QUOTATION_API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? '';

export type PublishResponse = {
  status: 'queued' | 'published' | string;
  version?: number;
  published_url?: string;
  fallback_url?: string;
  pdfUrl?: string;
  targetId?: string;
  releaseId?: string;
  jobId?: string;
};

export type PublicationJob = {
  id: string;
  releaseId: string;
  type: string;
  status: 'queued' | 'running' | 'succeeded' | 'failed' | string;
  attempts: number;
  maxAttempts: number;
  lockedAt: string | null;
  lastError: string | null;
  brandId?: string;
};

export function publishQuotation(
  quotationId: string,
  lang: string,
  body: { baseRevision: number; brandId?: string },
): Promise<PublishResponse> {
  return quotationFetch<PublishResponse>(
    `${QUOTATION_API_BASE}/api/v2/quotations/${quotationId}/publish?lang=${encodeURIComponent(lang)}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
    'Publish failed.',
  );
}

export function getPublicationJob(jobId: string, signal?: AbortSignal): Promise<PublicationJob> {
  return quotationFetch<PublicationJob>(
    `${QUOTATION_API_BASE}/api/v2/publication-jobs/${jobId}`,
    { signal },
    'Unable to refresh publication status.',
  );
}

export function unpublishTarget(quotationId: string, targetId: string): Promise<{ status: string }> {
  return quotationFetch(
    `${QUOTATION_API_BASE}/api/v2/quotations/${quotationId}/publication-targets/${targetId}/unpublish`,
    { method: 'POST' },
    'Unpublish failed.',
  );
}

export function restoreRelease(
  quotationId: string,
  targetId: string,
  releaseNumber: number,
): Promise<{ status: string; release: number; publishedUrl: string; fallbackUrl: string }> {
  return quotationFetch(
    `${QUOTATION_API_BASE}/api/v2/quotations/${quotationId}/publication-targets/${targetId}/releases/${releaseNumber}/restore`,
    { method: 'POST' },
    'Restore failed.',
  );
}
