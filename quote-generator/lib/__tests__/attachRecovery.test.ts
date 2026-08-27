import assert from 'node:assert/strict';
import test from 'node:test';

import {
  ATTACH_RECOVERY_PARAMS,
  clearAttachRecovery,
  readAttachRecovery,
} from '../attachRecovery.ts';

test('reads a complete attach recovery payload', () => {
  const params = new URLSearchParams({
    [ATTACH_RECOVERY_PARAMS.sheetId]: 'cst_123',
    [ATTACH_RECOVERY_PARAMS.idempotencyKey]: 'attach-key-123',
  });

  assert.deepEqual(readAttachRecovery(params), {
    sheetId: 'cst_123',
    idempotencyKey: 'attach-key-123',
  });
});

test('rejects a partial recovery payload rather than replacing its key', () => {
  assert.equal(
    readAttachRecovery(new URLSearchParams({ [ATTACH_RECOVERY_PARAMS.sheetId]: 'cst_123' })),
    null,
  );
  assert.equal(
    readAttachRecovery(new URLSearchParams({ [ATTACH_RECOVERY_PARAMS.idempotencyKey]: 'attach-key-123' })),
    null,
  );
});

test('clears recovery fields while preserving the active costing route', () => {
  const params = new URLSearchParams({
    stage: 'costing',
    lang: 'en',
    [ATTACH_RECOVERY_PARAMS.sheetId]: 'cst_123',
    [ATTACH_RECOVERY_PARAMS.idempotencyKey]: 'attach-key-123',
  });

  assert.equal(clearAttachRecovery(params).toString(), 'stage=costing&lang=en');
});
