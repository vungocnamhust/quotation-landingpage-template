import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { buildContentMutation, resolveContentMutationSource } from '../rules/designMutation.ts';

describe('designMutation', () => {
  it('resolves a repeated field to its live id-keyed source', () => {
    const source = resolveContentMutationSource('/itinerary/days/{dayId}/title', '/itinerary/days/day-3/title');
    assert.equal(source, '/itinerary/days/day-3/title');
  });

  it('falls back to the contract template when there is no resolved source', () => {
    const source = resolveContentMutationSource('/trip/title', undefined);
    assert.equal(source, '/trip/title');
  });

  it('builds a content mutation carrying the resolved source and value', () => {
    const mutation = buildContentMutation('/itinerary/days/{dayId}/title', '/itinerary/days/day-3/title', 'Welcome to Hanoi');
    assert.deepEqual(mutation, { kind: 'content', source: '/itinerary/days/day-3/title', value: 'Welcome to Hanoi' });
  });

  it('builds a content mutation for a non-repeated field with no resolved source', () => {
    const mutation = buildContentMutation('/trip/title', undefined, 'New title');
    assert.deepEqual(mutation, { kind: 'content', source: '/trip/title', value: 'New title' });
  });
});
