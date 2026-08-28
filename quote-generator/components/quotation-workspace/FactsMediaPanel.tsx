'use client';

import dynamic from 'next/dynamic';
import { useMemo, useState, useTransition } from 'react';
import { getTypographyClassName } from '../../config/typography.ts';
import { cn } from '../../utils/cn.ts';
import { apiErrorMessage, quotationFetch } from '../../lib/apiError.ts';
import { useToast } from '../staff-workspace/ToastProvider.tsx';
import { useMediaSlotSave } from './useMediaSlotSave.ts';
import { derivePickerTarget } from '../../lib/rules/mediaSlotAdapter.ts';
import { entityFieldToken, resolveEntityIndex } from '../../lib/rules/mediaSlotReconciler.ts';

const MediaDrawer = dynamic(() => import('./MediaDrawer'));
const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? '';
type MediaRef = { r2Key: string; status: 'ready'; source?: 'manual' | 'auto' | 'fallback'; altText?: string };
type RecordValue = Record<string, unknown>;
type Descriptor = { fieldId: string; owner: string; kind: string; section: string };
function record(value: unknown): RecordValue { return value && typeof value === 'object' && !Array.isArray(value) ? value as RecordValue : {}; }
function label(id: string) { return id.replaceAll('.', ' · '); }
function ref(value: unknown): MediaRef | null { const item = record(value); return typeof item.r2Key === 'string' && item.r2Key ? { r2Key: item.r2Key, status: 'ready', altText: typeof item.altText === 'string' ? item.altText : '' } : null; }

export default function FactsMediaPanel({ quotationId, lang, document, currentRevision, contract, onSaved }: { quotationId: string; lang: string; document: RecordValue; currentRevision: number; contract?: { fields: Descriptor[] }; onSaved: () => Promise<unknown> | void }) {
  const { toast } = useToast();
  const [draft, setDraft] = useState<Record<string, MediaRef | MediaRef[] | null>>({});
  const [selection, setSelection] = useState<{ fieldId: string; gallery: boolean } | null>(null);
  const [message, setMessage] = useState('Select all quotation images here. The Design stage is read-only for media.');
  const [pending, startTransition] = useTransition();
  const { saveSlots } = useMediaSlotSave({ quotationId, lang, currentRevision, onSaved });

  const fields = useMemo(() => {
    const declared = (contract?.fields ?? []).filter((field) => field.owner === 'fact' && ['image', 'gallery'].includes(field.kind) && !field.fieldId.includes('*'));
    const itinerary = Array.isArray(record(document.itinerary).days) ? record(document.itinerary).days as unknown[] : [];
    const hotels = Array.isArray(record(document.stays).hotels) ? record(document.stays).hotels as unknown[] : [];
    return [
      ...declared,
      // A day/hotel's fieldId embeds its stable id (Plan 16.1 M3.3), not its
      // array position, so a save submitted after the list is reordered
      // elsewhere still lands on the right entity.
      ...itinerary.map((day, index) => ({ fieldId: `itinerary.days.${entityFieldToken(record(day), index)}.gallery`, owner: 'fact', kind: 'gallery', section: 'itinerary' })),
      ...hotels.flatMap((hotel, index) => {
        const token = entityFieldToken(record(hotel), index);
        return [
          { fieldId: `stays.hotels.${token}.hotelImage`, owner: 'fact', kind: 'image', section: 'hotels' },
          { fieldId: `stays.hotels.${token}.roomImage`, owner: 'fact', kind: 'image', section: 'hotels' }
        ];
      })
    ];
  }, [contract, document]);

  const getValue = (fieldId: string): MediaRef | MediaRef[] | null => {
    const leaf = fieldId.split('.').at(-1) ?? '';
    if (fieldId in draft) return draft[fieldId];
    if (fieldId.startsWith('assets.')) return ref(record(document.assets)[leaf]);
    if (fieldId.startsWith('itinerary.days.')) {
      const rawDays = record(document.itinerary).days;
      const days: unknown[] = Array.isArray(rawDays) ? rawDays : [];
      const day = resolveEntityIndex(days.map(record), fieldId.split('.')[2]);
      const images = day === null ? {} : record(record(days[day]).images);
      const carousel = images.carousel;
      return Array.isArray(carousel) ? carousel.map(ref).filter((item): item is MediaRef => item !== null) : [];
    }
    const rawHotels = record(document.stays).hotels;
    const hotels: unknown[] = Array.isArray(rawHotels) ? rawHotels : [];
    const index = resolveEntityIndex(hotels.map(record), fieldId.split('.')[2]);
    return index === null ? null : ref(record(hotels[index])[leaf]);
  };

  const save = () => startTransition(async () => {
    if (!Object.keys(draft).length) return;
    try {
      const entries = Object.entries(draft).map(([fieldId, value]) => ({ fieldId, value }));
      const response = await saveSlots(entries);
      const msg = `Saved Fact media revision ${response.currentRevision}.`;
      setMessage(msg);
      toast(msg, 'success');
      setDraft({});
    } catch (error) {
      const msg = apiErrorMessage(error);
      setMessage(msg);
      toast(msg, 'error');
    }
  });

  const defaults = () => startTransition(async () => {
    try {
      const preview = await quotationFetch<{ rationale: unknown[]; appliedCount?: number; hasChanges?: boolean }>(
        `${API_BASE}/api/v2/quotations/${quotationId}/facts/media-defaults?lang=${encodeURIComponent(lang)}`,
        { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ baseRevision: currentRevision, dryRun: true }) },
        'Media defaults could not be previewed.'
      );
      if (!preview.hasChanges && (!preview.rationale || !preview.rationale.length)) {
        const msg = 'No matching default media was found for empty slots.';
        setMessage(msg);
        toast(msg, 'info');
        return;
      }
      const applied = await quotationFetch<{ rationale: unknown[]; appliedCount?: number }>(
        `${API_BASE}/api/v2/quotations/${quotationId}/facts/media-defaults?lang=${encodeURIComponent(lang)}`,
        { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ baseRevision: currentRevision, dryRun: false }) },
        'Media defaults could not be applied.'
      );
      const count = applied.appliedCount ?? applied.rationale?.length ?? preview.rationale?.length ?? 0;
      const msg = `Applied ${count} generated Fact media choices.`;
      setMessage(msg);
      toast(msg, 'success');
      await onSaved();
    } catch (error) {
      const msg = apiErrorMessage(error);
      setMessage(msg);
      toast(msg, 'error');
    }
  });

  const confirm = (keys: string[]) => {
    if (!selection) return;
    const next = keys.map((r2Key) => ({ r2Key, status: 'ready' as const, source: 'manual' as const, altText: '' }));
    setDraft((current) => ({ ...current, [selection.fieldId]: selection.gallery ? next : next[0] ?? null }));
    setSelection(null);
  };

  const activeTarget = useMemo(() => {
    if (!selection) return {};
    return derivePickerTarget(document, selection.fieldId);
  }, [selection, document]);

  return (
    <section className="flex flex-col gap-4 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-5 shadow-2xs">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className={cn(getTypographyClassName('cardTitle'), 'text-[var(--color-on-surface)]')}>Quotation media</h2>
          <p className={cn(getTypographyClassName('bodySm'), 'text-[var(--color-muted)]')}>{message}</p>
        </div>
        <button
          type="button"
          disabled={pending}
          onClick={defaults}
          className={cn(
            getTypographyClassName('buttonSecondary'),
            'min-h-11 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-4 shadow-2xs border border-transparent transition-all disabled:opacity-50 cursor-pointer'
          )}
        >
          Generate missing media
        </button>
      </div>
      <div className="grid gap-3">
        {fields.map((field) => {
          const value = getValue(field.fieldId);
          const values = Array.isArray(value) ? value : value ? [value] : [];
          return (
            <div key={field.fieldId} className="rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface-white)] p-3.5 shadow-2xs">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <span className={cn(getTypographyClassName('bodySm'), 'text-[var(--color-on-surface)]')}>
                  {label(field.fieldId)} · {values.length ? `${values.length}${field.kind === 'gallery' ? '/3' : ''} selected` : 'empty/default fallback'}
                </span>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setSelection({ fieldId: field.fieldId, gallery: field.kind === 'gallery' })}
                    className={cn(
                      getTypographyClassName('buttonSecondary'),
                      'min-h-10 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-3.5 shadow-2xs border border-transparent transition-all cursor-pointer'
                    )}
                  >
                    {field.kind === 'gallery' ? 'Choose images' : 'Choose image'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setDraft((current) => ({ ...current, [field.fieldId]: null }))}
                    className={cn(
                      getTypographyClassName('buttonSecondary'),
                      'min-h-10 rounded-[var(--radius-button)] bg-rose-700 !text-white hover:bg-rose-800 px-3.5 shadow-2xs border border-transparent transition-all cursor-pointer'
                    )}
                  >
                    Clear
                  </button>
                </div>
              </div>
              {values.map((item, index) => (
                <div key={`${item.r2Key}-${index}`} className="mt-2 flex flex-wrap gap-2">
                  <span className={cn(getTypographyClassName('caption'), 'break-all text-[var(--color-muted)]')}>
                    {item.r2Key}
                  </span>
                  <input
                    aria-label={`${label(field.fieldId)} alt text`}
                    value={item.altText ?? ''}
                    onChange={(event) => {
                      const changed = [...values];
                      changed[index] = { ...item, altText: event.target.value };
                      setDraft((current) => ({ ...current, [field.fieldId]: field.kind === 'gallery' ? changed : changed[0] }));
                    }}
                    placeholder="Alt text"
                    className={cn(
                      getTypographyClassName('caption'),
                      'rounded border border-[var(--color-border)] px-2 py-0.5'
                    )}
                  />
                </div>
              ))}
            </div>
          );
        })}
      </div>
      <button
        type="button"
        disabled={pending || !Object.keys(draft).length}
        onClick={save}
        className={cn(
          getTypographyClassName('buttonPrimary'),
          'min-h-11 w-fit rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-5 shadow-md border border-transparent transition-all disabled:opacity-50 cursor-pointer'
        )}
      >
        Save media facts
      </button>
      <MediaDrawer
        open={selection !== null}
        onClose={() => setSelection(null)}
        selectionMode={selection?.gallery ? 'multiple' : 'single'}
        maxSelection={selection?.gallery ? 3 : 1}
        minSelection={selection?.gallery ? 3 : 1}
        initialPrefix={activeTarget.initialPrefix}
        context={activeTarget.context}
        onConfirm={confirm}
      />
    </section>
  );
}
