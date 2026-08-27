/**
 * Pure domain rules for the Design canvas write-target dispatcher (Layer 1).
 *
 * Plan 16 §C.3 (docs/plans/refactor-tech-stack/16-design-tab-editable-content-audit.md):
 * a Design canvas edit resolves to exactly one of these mutation kinds, then
 * DesignCanvas.tsx calls the matching API for it. There is deliberately no
 * `fact` kind here — a locked (owner === 'fact' | 'fact-derived') field never
 * writes from Design; it only hands off to Facts (see ContextualInspector's
 * Locked Panel).
 */

export type ContentPointer = string; // id-keyed JSON pointer, ACL-validated server-side

export interface ContentMutation {
  kind: 'content';
  source: ContentPointer;
  value: string | string[];
}

export interface DesignMutation {
  kind: 'presentation';
  target: 'copyOverrides' | 'identityOverrides';
  fieldId: string;
  value: string;
}

export interface MediaMutation {
  kind: 'media';
  slotId: string;
  value: { r2Key: string; source: 'manual' } | { r2Key: string }[];
}

export type DesignCanvasMutation = ContentMutation | DesignMutation | MediaMutation;

export interface ContentPatchRequest {
  baseRevision: number;
  mutations: ContentMutation[];
}

export interface ContentPatchResponse {
  revision: number;
  updatedSources: string[];
  staleDraftScopes: string[];
}

/**
 * The literal, id-keyed pointer a content write targets. A repeated field
 * (itinerary day, hotel, route segment) is only ever selected via a live
 * runtime element, which already carries its resolved id-keyed source
 * (`resolvedSource`); a non-repeated field has no wildcard to resolve and
 * falls back to the contract's own template.
 */
export function resolveContentMutationSource(descriptorSource: string, resolvedSource: string | undefined): ContentPointer {
  return resolvedSource ?? descriptorSource;
}

export function buildContentMutation(descriptorSource: string, resolvedSource: string | undefined, value: string): ContentMutation {
  return { kind: 'content', source: resolveContentMutationSource(descriptorSource, resolvedSource), value };
}

export const designMutationReconciler = {
  resolveContentMutationSource,
  buildContentMutation,
};
