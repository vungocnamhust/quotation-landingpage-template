import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { normalizeSelection, validateCardinality, withManualSource } from '../rules/mediaSlotReconciler.ts';

describe('mediaSlotReconciler', () => {
  it('rejects a gallery selection below minItems', () => {
    const error = validateCardinality({ minItems: 3, maxItems: 3 }, normalizeSelection(['a.jpg', 'b.jpg']));
    assert.equal(error, 'This slot requires at least 3 images.');
  });

  it('rejects a selection above maxItems', () => {
    const error = validateCardinality({ minItems: 3, maxItems: 3 }, normalizeSelection(['a.jpg', 'b.jpg', 'c.jpg', 'd.jpg']));
    assert.equal(error, 'Select at most 3 images.');
  });

  it('accepts a selection exactly at minItems/maxItems', () => {
    const error = validateCardinality({ minItems: 3, maxItems: 3 }, normalizeSelection(['a.jpg', 'b.jpg', 'c.jpg']));
    assert.equal(error, null);
  });

  it('allows an empty selection regardless of minItems (clearing is always valid)', () => {
    const error = validateCardinality({ minItems: 3, maxItems: 3 }, []);
    assert.equal(error, null);
  });

  it('reports a single-item cardinality error with singular wording', () => {
    const error = validateCardinality({ minItems: 1, maxItems: 1 }, normalizeSelection(['a.jpg', 'b.jpg']));
    assert.equal(error, 'Select only 1 image.');
  });

  it('tags a manual selection with source and ready status', () => {
    assert.deepEqual(withManualSource('a.jpg', 'Alt'), { r2Key: 'a.jpg', status: 'ready', source: 'manual', altText: 'Alt' });
  });
});
