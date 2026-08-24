'use client';

import { useCallback, useState } from 'react';
import { quotationFetch } from '../../lib/apiError.ts';
import type { ContentActionPlan } from './useContentActionPlan.ts';

const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? '';
type WritingStyle = 'storytelling' | 'detailed';

type ExecutionResult = {
  planId: string;
  actionIds: string[];
  draftIds: string[];
  documentRevision: number;
  mode: 'auto' | 'bypass';
};

function correlationId(): string {
  return `cap-ui-${crypto.randomUUID()}`;
}

export function useContentActionExecution(quotationId: string) {
  const [pendingMode, setPendingMode] = useState<'accept' | 'auto' | 'bypass' | null>(null);

  const accept = useCallback(async (note = 'Accepted in Impact Center.'): Promise<ContentActionPlan> => {
    setPendingMode('accept');
    try {
      return await quotationFetch<ContentActionPlan>(
        `${API_BASE}/api/v2/quotations/${quotationId}/content-actions/accept`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Correlation-ID': correlationId(),
          },
          body: JSON.stringify({ note }),
        },
        'The Content change plan could not be accepted.',
      );
    } finally {
      setPendingMode(null);
    }
  }, [quotationId]);

  const execute = useCallback(async (
    mode: 'auto' | 'bypass',
    planId: string,
    actionIds: string[],
    writingStyle: WritingStyle,
    expectedRevision?: number,
  ): Promise<ExecutionResult> => {
    setPendingMode(mode);
    try {
      const path = mode === 'auto' ? 'generate-drafts' : 'generate-and-apply';
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        'X-Correlation-ID': correlationId(),
      };
      if (mode === 'bypass') headers['Idempotency-Key'] = crypto.randomUUID();
      return await quotationFetch<ExecutionResult>(
        `${API_BASE}/api/v2/quotations/${quotationId}/content-actions/${path}`,
        {
          method: 'POST',
          headers,
          body: JSON.stringify({
            planId,
            actionIds,
            writingStyle,
            ...(mode === 'bypass' ? { expectedRevision } : {}),
          }),
        },
        mode === 'auto' ? 'Draft generation failed.' : 'Generate and apply failed.',
      );
    } finally {
      setPendingMode(null);
    }
  }, [quotationId]);

  return { pendingMode, accept, execute };
}
