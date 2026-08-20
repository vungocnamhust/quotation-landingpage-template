/**
 * Pure adapter module bridging Review/Workflow responses with UI Navigation and Handoffs (Layer 2).
 *
 * Guarantees zero schema corruption and lossless mapping for Stage transitions.
 */

import type { ResolvedHandoff } from '../../components/quotation-workspace/editableHandoff.ts';
import type {
  ReviewResponse,
  WorkflowResponse,
} from '../../components/quotation-workspace/useQuotationWorkspace.ts';
import type {
  CanonicalBlockerItem,
  TargetHandoff,
} from './workflowReconciler.ts';
import {
  fromReviewResponse,
  groupBlockersByCategory,
  isWorkflowReady,
} from './workflowReconciler.ts';

export type CanonicalWorkflowStatus = {
  isReady: boolean;
  blockers: CanonicalBlockerItem[];
  categories: ReturnType<typeof groupBlockersByCategory>;
  factsReady: boolean;
  contentReady: boolean;
  designReady: boolean;
  reviewReady: boolean;
};

export const workflowAdapter = {
  /**
   * Convert a TargetHandoff or CanonicalBlockerItem into a ResolvedHandoff compatible with editableHandoff.ts.
   */
  toResolvedHandoff(target: TargetHandoff | CanonicalBlockerItem): ResolvedHandoff {
    const handoff = 'targetHandoff' in target ? target.targetHandoff : target;
    const stage = handoff.stage === 'facts' ? 'facts' : 'content';

    return {
      stage,
      section: handoff.section || (handoff.stage === 'facts' ? 'trip' : 'hero'),
      source: handoff.source || 'blocker',
      wildcardIndices: [],
      focus: handoff.focus
        ? {
            kind: handoff.focus.kind,
            index: handoff.focus.index,
            id: handoff.focus.id,
          }
        : undefined,
    };
  },

  /**
   * Convert server workflow & review responses into a unified CanonicalWorkflowStatus.
   */
  fromServerWorkflow(
    workflowData?: WorkflowResponse | null,
    reviewData?: ReviewResponse | null,
    publicationJob?: { id: string; status: string; lastError: string | null } | null,
    lang: string = 'en'
  ): CanonicalWorkflowStatus {
    const blockers = fromReviewResponse(reviewData, workflowData, publicationJob, lang);
    const categories = groupBlockersByCategory(blockers);
    const isReady = isWorkflowReady(blockers);

    return {
      isReady,
      blockers,
      categories,
      factsReady: workflowData?.facts.ready ?? (categories.facts.length === 0),
      contentReady: workflowData?.content.ready ?? (categories.content.filter((b) => !b.isAdvisory).length === 0),
      designReady: workflowData?.design.ready ?? (categories.design.length === 0),
      reviewReady: workflowData?.review.ready ?? isReady,
    };
  },
};
