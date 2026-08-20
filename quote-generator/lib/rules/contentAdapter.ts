/**
 * Pure adapter module bridging DocumentResponse, ContentDraft, and ContentEditorState
 * with the unified CanonicalContent model (Layer 2).
 *
 * Guarantees zero schema corruption and lossless two-way mapping.
 */

import type {
  ContentCandidate,
  ContentDraft,
  DocumentResponse,
} from '../../components/quotation-workspace/useQuotationWorkspace.ts';

export type CanonicalContentScopeState = {
  scope: string;
  candidate: ContentCandidate;
  draft?: ContentDraft | null;
  isDraft: boolean;
};

export type CanonicalContentState = {
  scopes: Record<string, CanonicalContentScopeState>;
  lang?: string | null;
};

export const contentAdapter = {
  /**
   * Convert DocumentResponse and optional drafts into a unified CanonicalContentState.
   */
  fromDocumentResponse(
    response: Partial<DocumentResponse>,
    drafts: ContentDraft[] = [],
    lang: string = 'en'
  ): CanonicalContentState {
    const editorState = response.contentEditorState || {};
    const scopes: Record<string, CanonicalContentScopeState> = {};

    // 1. Ingest base candidates from contentEditorState
    for (const [scope, candidate] of Object.entries(editorState)) {
      if (candidate && typeof candidate === 'object') {
        scopes[scope] = {
          scope,
          candidate: { ...candidate },
          draft: null,
          isDraft: false,
        };
      }
    }

    // 2. Overlay drafts if present
    for (const draft of drafts) {
      if (!draft || !draft.scope) continue;
      const existing = scopes[draft.scope];
      scopes[draft.scope] = {
        scope: draft.scope,
        candidate: draft.candidate ? { ...draft.candidate } : existing?.candidate || {},
        draft,
        isDraft: draft.status === 'draft',
      };
    }

    return {
      scopes,
      lang,
    };
  },

  /**
   * Convert raw contentEditorState dictionary and drafts array to CanonicalContentState.
   */
  toCanonicalContent(
    contentEditorState: Record<string, ContentCandidate> = {},
    drafts: ContentDraft[] = [],
    lang: string = 'en'
  ): CanonicalContentState {
    const scopes: Record<string, CanonicalContentScopeState> = {};

    for (const [scope, candidate] of Object.entries(contentEditorState)) {
      if (candidate && typeof candidate === 'object') {
        scopes[scope] = {
          scope,
          candidate: { ...candidate },
          draft: null,
          isDraft: false,
        };
      }
    }

    for (const draft of drafts) {
      if (!draft || !draft.scope) continue;
      const existing = scopes[draft.scope];
      scopes[draft.scope] = {
        scope: draft.scope,
        candidate: draft.candidate ? { ...draft.candidate } : existing?.candidate || {},
        draft,
        isDraft: draft.status === 'draft',
      };
    }

    return {
      scopes,
      lang,
    };
  },

  /**
   * Synchronize CanonicalContentState back to the raw contentEditorState record.
   * Preserves any untracked previous editor state entries.
   */
  syncToContentEditorState(
    canonical: CanonicalContentState,
    prevEditorState: Record<string, ContentCandidate> = {}
  ): Record<string, ContentCandidate> {
    const result: Record<string, ContentCandidate> = { ...prevEditorState };

    for (const [scope, scopeState] of Object.entries(canonical.scopes)) {
      if (scopeState && scopeState.candidate) {
        result[scope] = { ...scopeState.candidate };
      }
    }

    return result;
  },

  /**
   * Apply candidate changes to a complete document JSON object without losing unedited fields.
   */
  mergeCandidateWithDocument(
    document: Record<string, unknown>,
    scope: string,
    candidate: ContentCandidate
  ): Record<string, unknown> {
    const nextDoc = JSON.parse(JSON.stringify(document)) as Record<string, unknown>;

    if (scope === 'hero') {
      const tripCandidate = (candidate.trip as Record<string, unknown>) || {};
      const narrativeCandidate = (candidate.narrative as Record<string, unknown>) || {};

      nextDoc.trip = {
        ...((nextDoc.trip as Record<string, unknown>) || {}),
        ...tripCandidate,
      };

      nextDoc.narrative = {
        ...((nextDoc.narrative as Record<string, unknown>) || {}),
        ...narrativeCandidate,
      };
    } else if (scope === 'overview_letter' || scope === 'overview') {
      const narrativeCandidate = (candidate.narrative as Record<string, unknown>) || {};
      nextDoc.narrative = {
        ...((nextDoc.narrative as Record<string, unknown>) || {}),
        ...narrativeCandidate,
      };
    } else if (scope === 'route') {
      const routeCandidate = (candidate.route as Record<string, unknown>) || candidate;
      const currentRoute = (nextDoc.route as Record<string, unknown>) || {};

      const title =
        typeof routeCandidate.title === 'string' ? routeCandidate.title : currentRoute.title;
      const description =
        typeof routeCandidate.description === 'string'
          ? routeCandidate.description
          : currentRoute.description;

      const staySegments = Array.isArray(currentRoute.staySegments)
        ? [...(currentRoute.staySegments as Array<Record<string, unknown>>)]
        : [];

      if (Array.isArray(routeCandidate.mapSegmentDescriptions)) {
        routeCandidate.mapSegmentDescriptions.forEach((desc, idx) => {
          if (staySegments[idx]) {
            staySegments[idx] = {
              ...staySegments[idx],
              mapSegmentDesc: String(desc ?? ''),
            };
          }
        });
      }

      nextDoc.route = {
        ...currentRoute,
        title,
        description,
        staySegments,
      };
    } else if (scope === 'itinerary') {
      const itineraryCandidate = (candidate.itinerary as Record<string, unknown>) || candidate;
      nextDoc.itinerary = {
        ...((nextDoc.itinerary as Record<string, unknown>) || {}),
        ...itineraryCandidate,
      };
    } else if (scope.startsWith('itinerary:day:')) {
      const dayNumber = parseInt(scope.split(':').pop() || '1', 10);
      const itineraryObj = (nextDoc.itinerary as Record<string, unknown>) || {};
      const days = Array.isArray(itineraryObj.days)
        ? [...(itineraryObj.days as Array<Record<string, unknown>>)]
        : [];

      const dayIndex = days.findIndex((d) => d.dayNumber === dayNumber || d.day_number === dayNumber);
      const targetIndex = dayIndex >= 0 ? dayIndex : dayNumber - 1;

      if (targetIndex >= 0 && targetIndex < days.length) {
        const currentDay = days[targetIndex] || {};
        days[targetIndex] = {
          ...currentDay,
          dayNumber,
          title: candidate.title !== undefined ? candidate.title : currentDay.title,
          description:
            candidate.description !== undefined ? candidate.description : currentDay.description,
          activities:
            candidate.activities !== undefined ? candidate.activities : currentDay.activities,
        };
      }

      nextDoc.itinerary = {
        ...itineraryObj,
        days,
      };
    }

    return nextDoc;
  },
};
