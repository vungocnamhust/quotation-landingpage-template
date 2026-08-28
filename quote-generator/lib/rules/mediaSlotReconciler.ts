/**
 * Pure domain rules for media slots (Layer 1).
 *
 * Plan 16.1 §2.1 (docs/plans/refactor-tech-stack/16.1-design-tab-media-resolution.md):
 * `document_json` fact media slots are the single store of truth for media —
 * there is no second `mediaOverrides` store to reconcile against. This module
 * only carries the shape (`MediaRef`) and the cardinality rule (R9) shared by
 * every write surface (DesignCanvas, FactsMediaPanel, MediaSlotRenderer).
 */

export type MediaSource = 'manual' | 'auto' | 'fallback';
export type MediaStatus = 'ready' | 'review_required';

export interface MediaRef {
  readonly r2Key: string;
  readonly status?: MediaStatus;
  readonly source?: MediaSource;
  readonly altText?: string;
}

export interface MediaSlotCardinality {
  readonly minItems: number;
  readonly maxItems: number;
}

/**
 * Mirrors the server-side check in `main._validate_v2_fact_media_slots`: an
 * empty selection is always a valid "cleared" state, but a non-empty
 * selection must satisfy both bounds. Client-side so the picker can block a
 * doomed confirm before round-tripping to the API.
 */
export function validateCardinality(descriptor: MediaSlotCardinality, refs: readonly MediaRef[]): string | null {
  if (refs.length > descriptor.maxItems) {
    return descriptor.maxItems === 1
      ? 'Select only 1 image.'
      : `Select at most ${descriptor.maxItems} images.`;
  }
  if (refs.length > 0 && refs.length < descriptor.minItems) {
    return `This slot requires at least ${descriptor.minItems} image${descriptor.minItems === 1 ? '' : 's'}.`;
  }
  return null;
}

export function withManualSource(r2Key: string, altText = ''): MediaRef {
  return { r2Key, status: 'ready', source: 'manual', altText };
}

export function normalizeSelection(r2Keys: readonly string[]): MediaRef[] {
  return r2Keys.map((r2Key) => withManualSource(r2Key));
}
