import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  matchEditableSource,
  resolveEditableHandoff,
  resolveInspectorDescriptor,
  type InspectorDescriptor,
} from '../../components/quotation-workspace/editableHandoff.ts';

function dayTitleDescriptor(): InspectorDescriptor {
  return {
    fieldId: 'itinerary.days.*.title',
    section: 'itinerary',
    owner: 'content',
    kind: 'text',
    source: '/itinerary/days/{dayId}/title',
    requiredForPublish: true,
    visibleIn: ['desktop', 'mobile', 'pdf'],
    defaultStrategy: 'content-required',
    generator: 'llm',
    inspectorControl: 'none',
    editMode: 'handoff',
    handoff: { stage: 'content', section: 'itinerary', item: 'day', indexFromSource: 2 },
    handoffStage: 'content',
    handoffSection: 'itinerary',
  } as unknown as InspectorDescriptor;
}

function dayNumberDescriptor(): InspectorDescriptor {
  return {
    fieldId: 'itinerary.days.*.dayNumber',
    section: 'programme',
    owner: 'fact-derived',
    kind: 'text',
    source: '/itinerary/days/*/dayNumber',
    requiredForPublish: false,
    visibleIn: ['desktop', 'mobile', 'pdf'],
    defaultStrategy: 'fact-required',
    generator: 'none',
    inspectorControl: 'none',
    editMode: 'handoff',
    handoff: { stage: 'facts', section: 'programme', anchor: 'day', item: 'day', indexFromSource: 2 },
    handoffStage: 'facts',
    handoffSection: 'programme',
  } as unknown as InspectorDescriptor;
}

function documentWithDays(order: Array<{ id: string; dayNumber: number; title: string }>) {
  return { itinerary: { days: order.map((day) => ({ id: day.id, sourceFactId: day.id, dayNumber: day.dayNumber, title: day.title })) } };
}

describe('editableHandoff', () => {
  it('matches a v4 id-keyed template against a concrete id-keyed source', () => {
    const wildcardIndices = matchEditableSource('/itinerary/days/{dayId}/title', '/itinerary/days/day-3/title');
    assert.deepEqual(wildcardIndices, [2]);
  });

  it('still matches the v3 numeric-index template for a numeric source (transition compatibility)', () => {
    const wildcardIndices = matchEditableSource('/itinerary/days/*/dayNumber', '/itinerary/days/2/dayNumber');
    assert.deepEqual(wildcardIndices, [2]);
  });

  it('rejects a source with the wrong shape entirely', () => {
    assert.equal(matchEditableSource('/itinerary/days/{dayId}/title', '/itinerary/days/day-3/description'), null);
  });

  it('resolveInspectorDescriptor finds the id-keyed content descriptor for a live runtime source', () => {
    const matched = resolveInspectorDescriptor([dayTitleDescriptor()], '/itinerary/days/day-2/title');
    assert.ok(matched);
    assert.equal(matched?.descriptor.fieldId, 'itinerary.days.*.title');
  });

  it('resolves the correct day by id even after the array is reordered', () => {
    const original = documentWithDays([
      { id: 'day-1', dayNumber: 1, title: 'Arrival' },
      { id: 'day-2', dayNumber: 2, title: 'Hanoi tour' },
    ]);
    const reordered = documentWithDays([
      { id: 'day-2', dayNumber: 1, title: 'Hanoi tour' },
      { id: 'day-1', dayNumber: 2, title: 'Arrival' },
    ]);

    const beforeResolved = resolveEditableHandoff(dayTitleDescriptor(), '/itinerary/days/day-2/title', original);
    const afterResolved = resolveEditableHandoff(dayTitleDescriptor(), '/itinerary/days/day-2/title', reordered);

    assert.equal(beforeResolved?.focus?.id, 'day-2');
    assert.equal(beforeResolved?.focus?.index, 1);
    assert.equal(afterResolved?.focus?.id, 'day-2');
    assert.equal(afterResolved?.focus?.index, 0);
  });

  it('resolves a numeric-index fact-derived source to the record at that position (unmigrated v3 field)', () => {
    const document = documentWithDays([
      { id: 'day-1', dayNumber: 1, title: 'Arrival' },
      { id: 'day-2', dayNumber: 2, title: 'Hanoi tour' },
    ]);
    const resolved = resolveEditableHandoff(dayNumberDescriptor(), '/itinerary/days/1/dayNumber', document);
    assert.equal(resolved?.focus?.id, 'day-2');
    assert.equal(resolved?.focus?.index, 1);
  });

  it('returns undefined for a deleted day id', () => {
    const document = documentWithDays([{ id: 'day-1', dayNumber: 1, title: 'Arrival' }]);
    const resolved = resolveEditableHandoff(dayTitleDescriptor(), '/itinerary/days/day-9/title', document);
    assert.equal(resolved, undefined);
  });
});
