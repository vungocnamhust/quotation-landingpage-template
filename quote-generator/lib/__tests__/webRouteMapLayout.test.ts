import assert from 'node:assert/strict';
import test from 'node:test';
import GLPK from 'glpk.js/node';
import type { WebRouteMapLayoutInput } from '../../components/display/map/web/layout/contracts.ts';
import { solveWebRouteMapLayout } from '../../components/display/map/web/layout/optimizer.ts';
import { validateWebRouteMapLayout } from '../../components/display/map/web/layout/validate.ts';
import { polylineLength } from '../../components/display/map/web/layout/geometry.ts';

const GLPK_SOLVER = await GLPK();

function fixture(): WebRouteMapLayoutInput {
  const markers = [
    ['01', 385, 560],
    ['02', 320, 610],
    ['03', 365, 155],
    ['04', 390, 225],
    ['05', 475, 170],
  ].map(([sequence, x, y], order) => ({
    sequence: String(sequence),
    point: { x: Number(x), y: Number(y) },
    labelSize: { width: 156, height: 30 },
    order,
  }));
  return {
    viewport: { width: 680, height: 760 },
    markers,
    routes: markers.slice(1).map((marker, index) => ({
      id: `${markers[index].sequence}->${marker.sequence}`,
      fromSequence: markers[index].sequence,
      toSequence: marker.sequence,
      order: index,
    })),
    reservedZones: [{ x: 12, y: 12, width: 46, height: 92 }],
    layoutVersion: 'test-v1',
  };
}

test('web map MIP produces a deterministic, collision-free northern cluster layout', async () => {
  const input = fixture();
  const first = await solveWebRouteMapLayout(input, GLPK_SOLVER);
  const second = await solveWebRouteMapLayout(input, GLPK_SOLVER);

  assert.ok(first.diagnostics.status === 'optimal' || first.diagnostics.status === 'feasible');
  assert.deepEqual(validateWebRouteMapLayout(input, first), []);
  assert.deepEqual(
    { ...first, diagnostics: { ...first.diagnostics, elapsedMs: 0 } },
    { ...second, diagnostics: { ...second.diagnostics, elapsedMs: 0 } }
  );
  assert.equal(first.markers.length, 5);
  assert.equal(first.routes.length, 4);
});

test('web map MIP assigns parallel lanes to a return leg', async () => {
  const input = fixture();
  input.routes = [
    { id: '01->02', fromSequence: '01', toSequence: '02', order: 0 },
    { id: '02->01', fromSequence: '02', toSequence: '01', order: 1 },
  ];
  const plan = await solveWebRouteMapLayout(input, GLPK_SOLVER);
  assert.ok(plan.diagnostics.status === 'optimal' || plan.diagnostics.status === 'feasible');
  assert.equal(plan.routes.length, 2);
  assert.notEqual(plan.routes[0].curvature, plan.routes[1].curvature);
  assert.ok(plan.routes.every((route) => route.points.length > 2));
});

test('web map keeps every ordinary label local and uses curved leaders', async () => {
  const input = fixture();
  input.maxLeaderLength = 28;
  const plan = await solveWebRouteMapLayout(input, GLPK_SOLVER);
  assert.ok(plan.diagnostics.status === 'optimal' || plan.diagnostics.status === 'feasible');
  assert.ok(plan.markers.every((marker) => marker.leader.length > 2));
  assert.ok(plan.markers.every((marker) => polylineLength(marker.leader) <= 28.01));
  assert.deepEqual(validateWebRouteMapLayout(input, plan), []);
});

test('mobile labels remain local or cluster instead of using a desktop leader length', async () => {
  const input = fixture();
  input.viewport = { width: 420, height: 620 };
  input.maxLeaderLength = 22;
  const plan = await solveWebRouteMapLayout(input, GLPK_SOLVER);
  assert.ok(plan.diagnostics.status === 'optimal' || plan.diagnostics.status === 'feasible');
  assert.ok(plan.markers.every((marker) => polylineLength(marker.leader) <= 22.01));
  assert.deepEqual(validateWebRouteMapLayout(input, plan), []);
});

test('dense local labels cluster before a distant rail and preserve the active stop', async () => {
  const input = fixture();
  input.viewport = { width: 500, height: 300 };
  input.markers = input.markers.map((marker, order) => ({
    ...marker,
    point: { x: 250 + (order % 2) * 3, y: 150 + Math.floor(order / 2) * 3 },
    labelSize: { width: 280, height: 30 },
  }));
  input.routes = input.markers.slice(1).map((marker, index) => ({
    id: `${input.markers[index].sequence}->${marker.sequence}`,
    fromSequence: input.markers[index].sequence,
    toSequence: marker.sequence,
    order: index,
  }));
  input.activeSequence = '01';
  const plan = await solveWebRouteMapLayout(input, GLPK_SOLVER);
  assert.ok(plan.diagnostics.status === 'optimal' || plan.diagnostics.status === 'feasible');
  assert.ok(plan.markers.some((marker) => marker.sequence === '01' && !marker.isCluster));
  assert.ok(plan.markers.some((marker) => marker.isCluster));
  assert.ok(plan.markers.every((marker) => marker.leader.length > 2));
});

test('web map capacity clustering keeps the visible marker contract bounded', async () => {
  const input = fixture();
  input.viewport = { width: 1600, height: 900 };
  input.markers = Array.from({ length: 13 }, (_, order) => ({
    sequence: String(order + 1).padStart(2, '0'),
    point: { x: 120 + order * 105, y: 380 + (order % 2) * 110 },
    labelSize: { width: 96, height: 30 },
    order,
  }));
  input.routes = input.markers.slice(1).map((marker, index) => ({
    id: `${input.markers[index].sequence}->${marker.sequence}`,
    fromSequence: input.markers[index].sequence,
    toSequence: marker.sequence,
    order: index,
  }));
  const plan = await solveWebRouteMapLayout(input, GLPK_SOLVER);
  assert.ok(plan.diagnostics.status === 'optimal' || plan.diagnostics.status === 'feasible');
  assert.ok(plan.markers.length <= 12);
  assert.ok(plan.markers.some((marker) => marker.isCluster));
});
