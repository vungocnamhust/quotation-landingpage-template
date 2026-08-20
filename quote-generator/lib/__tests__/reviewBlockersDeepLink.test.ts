import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  fromReviewResponse,
  mapPresentationErrorToBlocker,
  workflowReconciler,
} from '../rules/workflowReconciler.ts';
import { workflowAdapter } from '../rules/workflowAdapter.ts';
import type { ReviewResponse } from '../../components/quotation-workspace/useQuotationWorkspace.ts';

describe('Review Blockers 1-Click Deep-Link & Resolution Roundtrip', () => {
  it('deep-links text overflow error directly to Design Canvas with Day 2 target and CTA', () => {
    const errorPointer = '/itinerary/days/1/description';
    const blocker = mapPresentationErrorToBlocker(errorPointer, 0, 'vi');

    assert.equal(blocker.category, 'design');
    assert.equal(blocker.title, 'Nội dung Ngày 2 quá dài (vượt quá 1,150 ký tự)');
    assert.equal(blocker.ctaLabel, 'Sửa nội dung Ngày 2 trên Design Canvas');
    assert.equal(blocker.targetHandoff.stage, 'design');
    assert.equal(blocker.targetHandoff.section, 'itinerary:day:2');
    assert.equal(blocker.targetHandoff.source, '/itinerary/days/1/description/0');
    assert.deepEqual(blocker.targetHandoff.focus, { kind: 'day', index: 1 });

    const resolved = workflowAdapter.toResolvedHandoff(blocker);
    assert.equal(resolved.stage, 'design');
    assert.equal(resolved.section, 'itinerary:day:2');
    assert.equal(resolved.source, '/itinerary/days/1/description/0');
    assert.deepEqual(resolved.focus, { kind: 'day', index: 1, id: undefined });
  });

  it('deep-links missing hero asset directly to Design Canvas hero image picker', () => {
    const review: ReviewResponse = {
      ready: false,
      missingInputs: [],
      blockingDrafts: [],
      contentBlockers: [],
      presentationErrors: [],
      assetReadiness: {
        ready: false,
        missing: ['r2_hero_cover_missing'],
        invalid: [],
      },
    };

    const blockers = fromReviewResponse(review, null, null, 'vi');
    const heroBlocker = blockers.find((b) => b.id === 'asset-missing');
    assert.ok(heroBlocker);
    assert.equal(heroBlocker.category, 'design');
    assert.equal(heroBlocker.ctaLabel, 'Chọn ảnh Hero trên Design Canvas');
    assert.equal(heroBlocker.targetHandoff.stage, 'design');
    assert.equal(heroBlocker.targetHandoff.source, '/hero/bannerImage');

    const resolved = workflowAdapter.toResolvedHandoff(heroBlocker);
    assert.equal(resolved.stage, 'design');
    assert.equal(resolved.source, '/hero/bannerImage');
  });

  it('verifies round-trip blocker resolution clears blockers when length is shortened', () => {
    // 1. Initial review with overflow on Day 2
    const reviewWithOverflow: ReviewResponse = {
      ready: false,
      missingInputs: [],
      blockingDrafts: [],
      contentBlockers: [],
      presentationErrors: ['/itinerary/days/1/description'],
    };

    const blockersInitial = fromReviewResponse(reviewWithOverflow, null, null, 'vi');
    assert.equal(blockersInitial.length, 1);
    assert.equal(workflowReconciler.isWorkflowReady(blockersInitial), false);

    // 2. User shortens text on Design Canvas and saves -> Server returns clean review
    const reviewResolved: ReviewResponse = {
      ready: true,
      missingInputs: [],
      blockingDrafts: [],
      contentBlockers: [],
      presentationErrors: [],
    };

    const blockersResolved = fromReviewResponse(reviewResolved, null, null, 'vi');
    assert.equal(blockersResolved.length, 0);
    assert.equal(workflowReconciler.isWorkflowReady(blockersResolved), true);
  });
});
