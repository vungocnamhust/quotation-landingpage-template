'use client';

import { quotationFetch, QuotationApiError } from '../../lib/apiError.ts';

const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? '';

export interface MediaSlotSaveArgs {
  quotationId: string;
  lang: string;
  currentRevision: number;
  onSaved: () => Promise<unknown> | void;
}

export interface MediaSlotEntry {
  fieldId: string;
  value: unknown;
}

export interface MediaSlotSaveResult {
  currentRevision: number;
}

export interface MediaSlotResetResult {
  currentRevision: number;
  applied: boolean;
  appliedCount: number;
}

/**
 * The single write facade for every media surface (Design canvas,
 * MediaSlotRenderer). Plan 16.1 D1/D3: `PUT /facts/media` is
 * the only media write path — there is deliberately no second call target
 * (the retired `presentation/overrides.mediaOverrides` shape).
 */
export function useMediaSlotSave({ quotationId, lang, currentRevision, onSaved }: MediaSlotSaveArgs) {
  const saveSlots = async (entries: MediaSlotEntry[], retryCount = 0): Promise<MediaSlotSaveResult> => {
    try {
      const result = await quotationFetch<MediaSlotSaveResult>(
        `${API_BASE}/api/v2/quotations/${quotationId}/facts/media?lang=${encodeURIComponent(lang)}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            baseRevision: currentRevision,
            slots: entries.map(({ fieldId, value }) => ({ fieldId, value })),
          }),
        },
        'Media could not be saved.'
      );
      await onSaved();
      return result;
    } catch (error) {
      if (retryCount < 1 && error instanceof QuotationApiError && error.kind === 'conflict') {
        await onSaved();
        return saveSlots(entries, retryCount + 1);
      }
      throw error;
    }
  };

  const saveSlot = (fieldId: string, value: unknown) => saveSlots([{ fieldId, value }]);

  /**
   * Reset a single slot back to its resolver-computed default (Plan 16.1
   * D4). This is the only path allowed to overwrite a manual selection —
   * `force` scopes the overwrite to exactly this one fieldId server-side.
   */
  const resetSlotToDefault = async (fieldId: string, retryCount = 0): Promise<MediaSlotResetResult> => {
    try {
      const result = await quotationFetch<MediaSlotResetResult>(
        `${API_BASE}/api/v2/quotations/${quotationId}/facts/media-defaults?lang=${encodeURIComponent(lang)}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ baseRevision: currentRevision, dryRun: false, fieldIds: [fieldId], force: true }),
        },
        'Media could not be reset to default.'
      );
      await onSaved();
      return result;
    } catch (error) {
      if (retryCount < 1 && error instanceof QuotationApiError && error.kind === 'conflict') {
        await onSaved();
        return resetSlotToDefault(fieldId, retryCount + 1);
      }
      throw error;
    }
  };

  return { saveSlot, saveSlots, resetSlotToDefault };
}
