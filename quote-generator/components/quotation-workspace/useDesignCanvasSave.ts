'use client';

import { quotationFetch, apiErrorMessage } from '../../lib/apiError.ts';
import type { ContentMutation, ContentPatchResponse } from '../../lib/rules/designMutation.ts';

const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? '';

export type DesignCanvasNotify = (options: {
  message: string;
  type: 'error';
  persistent?: boolean;
  scope: string;
  action?: { label: string; onClick: () => void };
}) => void;

export interface UseDesignCanvasSaveArgs {
  quotationId: string;
  lang: string;
  currentRevision: number;
  onSaved: () => Promise<unknown> | void;
  toast: (message: string, kind: 'success' | 'error') => void;
  notify: DesignCanvasNotify;
  clearScope: (scope: string) => void;
}

/**
 * The Design canvas' three write-target API calls (Layer 3 — React-facing
 * glue, single-retry-on-409 pattern shared across all three). Extracted from
 * DesignCanvas.tsx to keep that component under the file-size ceiling as
 * Plan 16 adds the content-values write path and the Locked Panel UX.
 */
export function useDesignCanvasSave({ quotationId, lang, currentRevision, onSaved, toast, notify, clearScope }: UseDesignCanvasSaveArgs) {
  const patchContentValues = async (mutations: ContentMutation[], retryCount = 0): Promise<ContentPatchResponse> => {
    try {
      const result = await quotationFetch<ContentPatchResponse>(
        `${API_BASE}/api/v2/quotations/${quotationId}/content-values?lang=${encodeURIComponent(lang)}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ baseRevision: currentRevision, mutations }),
        },
        'Content could not be saved.'
      );
      await onSaved();
      return result;
    } catch (error) {
      if (retryCount < 1 && error instanceof Error && error.message.includes('conflict')) {
        await onSaved();
        return patchContentValues(mutations, retryCount + 1);
      }
      throw error;
    }
  };

  const savePresentationOverride = async (
    fieldId: string,
    value: string,
    identityKey?: string,
    retryCount = 0
  ): Promise<void> => {
    try {
      await quotationFetch(
        `${API_BASE}/api/v2/quotations/${quotationId}/presentation/overrides?lang=${encodeURIComponent(lang)}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            baseRevision: currentRevision,
            copyOverrides: identityKey ? {} : { [fieldId]: value },
            identityOverrides: identityKey ? { [identityKey]: value } : {},
          }),
        },
        'Design override could not be saved.'
      );
      await onSaved();
      clearScope('design:override');
      toast('Design override saved.', 'success');
    } catch (error) {
      if (retryCount < 1 && error instanceof Error && error.message.includes('conflict')) {
        await onSaved();
        return savePresentationOverride(fieldId, value, identityKey, retryCount + 1);
      }
      const message = apiErrorMessage(error);
      notify({
        message,
        type: 'error',
        persistent: true,
        scope: 'design:override',
        action: { label: 'Reload', onClick: () => window.location.reload() },
      });
      throw new Error(message);
    }
  };

  return { patchContentValues, savePresentationOverride };
}
