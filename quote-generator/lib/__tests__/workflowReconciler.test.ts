import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  workflowReconciler,
  parseJsonPointer,
  mapPresentationErrorToBlocker,
  mapMissingFactInput,
  fromReviewResponse,
  groupBlockersByCategory,
  isWorkflowReady,
} from '../rules/workflowReconciler.ts';
import { workflowAdapter } from '../rules/workflowAdapter.ts';
import type { ReviewResponse, WorkflowResponse } from '../../components/quotation-workspace/useQuotationWorkspace.ts';

describe('workflowReconciler pure domain rules', () => {
  it('exposes facade object with all expected domain functions', () => {
    assert.equal(typeof workflowReconciler.parseJsonPointer, 'function');
    assert.equal(typeof workflowReconciler.mapPresentationErrorToBlocker, 'function');
    assert.equal(typeof workflowReconciler.mapMissingFactInput, 'function');
    assert.equal(typeof workflowReconciler.fromReviewResponse, 'function');
    assert.equal(typeof workflowReconciler.groupBlockersByCategory, 'function');
    assert.equal(typeof workflowReconciler.isWorkflowReady, 'function');
  });

  describe('parseJsonPointer pointer extraction', () => {
    it('parses itinerary day description and title pointers', () => {
      const parsedDesc = parseJsonPointer('/itinerary/days/0/description');
      assert.equal(parsedDesc.domain, 'itinerary');
      assert.equal(parsedDesc.collection, 'days');
      assert.equal(parsedDesc.index, 0);
      assert.equal(parsedDesc.field, 'description');

      const parsedTitle = parseJsonPointer('/itinerary/days/3/title');
      assert.equal(parsedTitle.domain, 'itinerary');
      assert.equal(parsedTitle.index, 3);
      assert.equal(parsedTitle.field, 'title');

      const parsedDay = parseJsonPointer('/itinerary/days/1');
      assert.equal(parsedDay.domain, 'itinerary');
      assert.equal(parsedDay.index, 1);
      assert.equal(parsedDay.field, undefined);
    });

    it('parses stays hotels pointers', () => {
      const parsedHotel = parseJsonPointer('/stays/hotels/2');
      assert.equal(parsedHotel.domain, 'stays');
      assert.equal(parsedHotel.collection, 'hotels');
      assert.equal(parsedHotel.index, 2);
    });

    it('handles generic presentation pointers and empty inputs', () => {
      const pres = parseJsonPointer('presentation.renderer');
      assert.equal(pres.domain, 'presentation.renderer');

      const empty = parseJsonPointer('');
      assert.equal(empty.domain, 'unknown');
    });
  });

  describe('mapPresentationErrorToBlocker error mapping', () => {
    it('maps itinerary description error to content stage handoff', () => {
      const blockerEn = mapPresentationErrorToBlocker('/itinerary/days/0/description', 0, 'en');
      assert.equal(blockerEn.category, 'design');
      assert.ok(blockerEn.title.includes('Day 1 description too long'));
      assert.equal(blockerEn.targetHandoff.stage, 'content');
      assert.equal(blockerEn.targetHandoff.section, 'itinerary:day:1');
      assert.deepEqual(blockerEn.targetHandoff.focus, { kind: 'day', index: 0 });

      const blockerVi = mapPresentationErrorToBlocker('/itinerary/days/0/description', 0, 'vi');
      assert.ok(blockerVi.title.includes('Nội dung Ngày 1 quá dài'));
      assert.equal(blockerVi.ctaLabel, 'Sửa nội dung Ngày 1');
    });

    it('maps itinerary title error to content stage handoff', () => {
      const blocker = mapPresentationErrorToBlocker('/itinerary/days/2/title', 1, 'en');
      assert.ok(blocker.title.includes('Day 3 title too long'));
      assert.equal(blocker.targetHandoff.section, 'itinerary:day:3');
    });

    it('maps hotel stays error to hotel_plan section', () => {
      const blocker = mapPresentationErrorToBlocker('/stays/hotels/1', 0, 'en');
      assert.ok(blocker.title.includes('Hotel 2 copy too long'));
      assert.equal(blocker.targetHandoff.stage, 'content');
      assert.equal(blocker.targetHandoff.section, 'hotel_plan');
      assert.deepEqual(blocker.targetHandoff.focus, { kind: 'hotel', index: 1 });
    });
  });

  describe('mapMissingFactInput section deep linking', () => {
    it('maps fact paths to corresponding facts sections', () => {
      assert.deepEqual(mapMissingFactInput('customer_facts.customer_name'), { stage: 'facts', section: 'travellers' });
      assert.deepEqual(mapMissingFactInput('trip_facts.start_date'), { stage: 'facts', section: 'trip' });
      assert.deepEqual(mapMissingFactInput('pricing_facts.options'), { stage: 'facts', section: 'commercial' });
      assert.deepEqual(mapMissingFactInput('service_facts.hotels'), { stage: 'facts', section: 'services' });
      assert.deepEqual(mapMissingFactInput('brand_id'), { stage: 'facts', section: 'seller' });
    });
  });

  describe('fromReviewResponse aggregation & isWorkflowReady', () => {
    it('aggregates all blocker categories cleanly', () => {
      const review: ReviewResponse = {
        ready: false,
        missingInputs: ['customer_facts.customer_name'],
        blockingDrafts: ['route'],
        contentBlockers: [
          { sectionId: 'hero', sectionType: 'hero', path: 'trip.title', message: 'Hero title is required.' },
        ],
        presentationErrors: ['/itinerary/days/0/description'],
        assetReadiness: {
          ready: false,
          missing: ['r2_hero_image_key'],
          invalid: [],
        },
      };

      const publicationJob = {
        id: 'job_123',
        status: 'failed',
        lastError: 'Chromium PDF render timed out.',
      };

      const blockers = fromReviewResponse(review, null, publicationJob, 'en');
      const grouped = groupBlockersByCategory(blockers);

      assert.equal(grouped.facts.length, 1);
      assert.equal(grouped.content.length, 2); // 1 advisory draft + 1 content blocker
      assert.equal(grouped.design.length, 2); // 1 presentation error + 1 missing asset
      assert.equal(grouped.publish.length, 1); // 1 failed job

      assert.equal(isWorkflowReady(blockers), false);
    });

    it('returns isWorkflowReady = true when only advisory drafts remain', () => {
      const review: ReviewResponse = {
        ready: true,
        missingInputs: [],
        blockingDrafts: ['hero'],
      };

      const blockers = fromReviewResponse(review, null, null, 'en');
      assert.equal(blockers.length, 1);
      assert.equal(blockers[0].isAdvisory, true);
      assert.equal(isWorkflowReady(blockers), true);
    });
  });
});

describe('workflowAdapter mapping', () => {
  it('converts TargetHandoff to ResolvedHandoff', () => {
    const handoff = workflowAdapter.toResolvedHandoff({
      stage: 'content',
      section: 'itinerary:day:2',
      focus: { kind: 'day', index: 1 },
    });

    assert.equal(handoff.stage, 'content');
    assert.equal(handoff.section, 'itinerary:day:2');
    assert.deepEqual(handoff.focus, { kind: 'day', index: 1, id: undefined });
  });

  it('builds CanonicalWorkflowStatus from server workflow responses', () => {
    const workflow: WorkflowResponse = {
      locale: 'en',
      currentRevision: 2,
      facts: { ready: true, missingInputs: [] },
      content: { ready: true, blockingDrafts: [], contentBlockers: [], generationOptional: true },
      design: { ready: true, presentationErrors: [] },
      review: { ready: true, blockers: [] },
    };

    const status = workflowAdapter.fromServerWorkflow(workflow, null, null, 'en');
    assert.equal(status.isReady, true);
    assert.equal(status.factsReady, true);
    assert.equal(status.contentReady, true);
    assert.equal(status.designReady, true);
  });
});
