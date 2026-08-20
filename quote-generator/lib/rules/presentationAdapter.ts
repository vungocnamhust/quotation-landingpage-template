/**
 * Pure adapter module bridging Document Models, EditableBrochureContract,
 * and Presentation State with the unified CanonicalPresentationState (Layer 2).
 *
 * Guarantees zero schema corruption and lossless mapping for Design Canvas.
 */

import type { EditableBrochureContract } from '../../components/quotation-workspace/useQuotationWorkspace.ts';

export type CanonicalPresentationState = {
  themeId: string;
  layoutVersion: number;
  renderer: string;
  copyOverrides: Record<string, string>;
  identityOverrides: Record<string, string>;
};

export type PresentationOverridesPayload = {
  baseRevision: number;
  copyOverrides: Record<string, string>;
  identityOverrides: Record<string, string>;
};

export const presentationAdapter = {
  /**
   * Extract presentation state from a raw JSON document.
   */
  fromDocument(document: Record<string, unknown> = {}): CanonicalPresentationState {
    const pres = (document.presentation as Record<string, unknown>) || {};
    const copyOverrides = (pres.copyOverrides as Record<string, string>) || {};
    const identityOverrides = (pres.identityOverrides as Record<string, string>) || {};

    return {
      themeId: typeof pres.themeId === 'string' ? pres.themeId : 'brochure',
      layoutVersion: typeof pres.layoutVersion === 'number' ? pres.layoutVersion : 1,
      renderer: typeof pres.renderer === 'string' ? pres.renderer : 'v2',
      copyOverrides: { ...copyOverrides },
      identityOverrides: { ...identityOverrides },
    };
  },

  /**
   * Synchronize CanonicalPresentationState back to document JSON object.
   */
  syncToDocument(
    presentationState: CanonicalPresentationState,
    prevDocument: Record<string, unknown> = {}
  ): Record<string, unknown> {
    const nextDoc = JSON.parse(JSON.stringify(prevDocument)) as Record<string, unknown>;
    const prevPres = (nextDoc.presentation as Record<string, unknown>) || {};

    nextDoc.presentation = {
      ...prevPres,
      themeId: presentationState.themeId,
      layoutVersion: presentationState.layoutVersion,
      renderer: presentationState.renderer,
      copyOverrides: { ...presentationState.copyOverrides },
      identityOverrides: { ...presentationState.identityOverrides },
    };

    return nextDoc;
  },

  /**
   * Create standardized payload for PUT /api/v2/quotations/{id}/presentation/overrides.
   */
  createOverridePayload(
    baseRevision: number,
    copyOverrides: Record<string, string> = {},
    identityOverrides: Record<string, string> = {}
  ): PresentationOverridesPayload {
    return {
      baseRevision,
      copyOverrides: { ...copyOverrides },
      identityOverrides: { ...identityOverrides },
    };
  },

  /**
   * Separate unified overrides dictionary into copyOverrides vs identityOverrides
   * based on the editable contract descriptor source path.
   */
  separateOverrides(
    overrides: Record<string, string>,
    contract?: EditableBrochureContract
  ): { copyOverrides: Record<string, string>; identityOverrides: Record<string, string> } {
    const copyOverrides: Record<string, string> = {};
    const identityOverrides: Record<string, string> = {};

    const descriptorMap = new Map<string, string>();
    if (contract && contract.fields) {
      for (const field of contract.fields) {
        if (field.fieldId && field.source) {
          descriptorMap.set(field.fieldId, field.source);
        }
      }
    }

    for (const [key, value] of Object.entries(overrides)) {
      const source = descriptorMap.get(key) || '';
      const identityMatch = source.match(/^\/presentation\/identityOverrides\/([^/]+)$/);

      if (identityMatch) {
        const identityKey = identityMatch[1];
        identityOverrides[identityKey] = value;
      } else if (key.startsWith('identity.')) {
        const identityKey = key.replace('identity.', '');
        identityOverrides[identityKey] = value;
      } else {
        copyOverrides[key] = value;
      }
    }

    return { copyOverrides, identityOverrides };
  },
};
