import assert from 'node:assert/strict';
import test from 'node:test';
import { resolveWebRouteMapFocusZoom } from '../../components/display/map/web/layout/focus.ts';

test('web map focus preserves the legacy minimum zoom by view mode', () => {
  assert.equal(resolveWebRouteMapFocusZoom(5, 'desktop'), 7.6);
  assert.equal(resolveWebRouteMapFocusZoom(5, 'mobile'), 6.4);
  assert.equal(resolveWebRouteMapFocusZoom(9, 'desktop'), 9);
});
