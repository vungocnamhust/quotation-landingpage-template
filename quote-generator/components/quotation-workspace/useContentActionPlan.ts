'use client';

import useSWR from 'swr';
import { quotationFetch } from '../../lib/apiError.ts';

const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? '';

export type ContentAutomationPolicy = 'manual' | 'auto' | 'bypass';
export type ContentActionState = 'pending' | 'draft_created' | 'applied' | 'skipped' | 'failed';

export type ContentAction = {
  id: string;
  scope: string;
  entityKey: string;
  reasonCode: string;
  automationPolicy: ContentAutomationPolicy;
  state: ContentActionState;
  inheritedReferenceStatus: string;
  draftId: string | null;
  appliedDocumentRevision: number | null;
  metadata: Record<string, unknown>;
};

export type ContentActionPlan = {
  id: string;
  quotationId: string;
  predecessorQuotationId: string | null;
  factsHash: string;
  status: 'pending' | 'accepted';
  acceptanceNote: string | null;
  actions: ContentAction[];
};

function fetchPlan(url: string): Promise<ContentActionPlan> {
  return quotationFetch<ContentActionPlan>(url, undefined, 'The Content change plan could not be loaded.');
}

export function useContentActionPlan(quotationId: string, enabled: boolean) {
  const url = enabled ? `${API_BASE}/api/v2/quotations/${quotationId}/content-actions` : null;
  return useSWR<ContentActionPlan>(url, fetchPlan, {
    shouldRetryOnError: (error: unknown) => {
      const status = typeof error === 'object' && error && 'status' in error
        ? Number((error as { status?: number }).status)
        : 0;
      return ![401, 403, 404].includes(status);
    },
    errorRetryCount: 2,
  });
}
