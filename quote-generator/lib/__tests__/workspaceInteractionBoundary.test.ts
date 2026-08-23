import assert from 'node:assert/strict';
import test from 'node:test';
import { isWorkspaceNativeInteractionTarget } from '../../components/quotation-workspace/interactionBoundary.ts';

test('workspace inspector capture skips an opted-in native interaction surface', () => {
  const mapTarget = {
    closest: (selector: string) => selector === '[data-workspace-interactive="true"]' ? {} : null,
  } as unknown as EventTarget;
  assert.equal(isWorkspaceNativeInteractionTarget(mapTarget), true);
});

test('workspace inspector capture continues for ordinary brochure targets', () => {
  const textTarget = {
    closest: () => null,
  } as unknown as EventTarget;
  assert.equal(isWorkspaceNativeInteractionTarget(textTarget), false);
  assert.equal(isWorkspaceNativeInteractionTarget(null), false);
});
