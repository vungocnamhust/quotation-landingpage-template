import test from 'node:test';
import assert from 'node:assert/strict';
import {
  resolveMarkerCollisions,
  getStemOffsetForAnchor,
  adjustAnchorForBounds,
  type MarkerPointInput,
} from '../rules/mapMarkerLayoutRules.ts';

test('resolveMarkerCollisions keeps single isolated points at top-center', () => {
  const points: MarkerPointInput[] = [
    { sequence: '1', x: 300, y: 700, city: 'Ho Chi Minh City' },
    { sequence: '2', x: 400, y: 400, city: 'Da Nang' },
    { sequence: '3', x: 380, y: 150, city: 'Hanoi' },
  ];

  const layout = resolveMarkerCollisions(points);

  assert.equal(layout.size, 3);
  assert.equal(layout.get('1')?.anchorDirection, 'top-center');
  assert.equal(layout.get('1')?.isClustered, false);
  assert.equal(layout.get('2')?.anchorDirection, 'top-center');
  assert.equal(layout.get('2')?.isClustered, false);
  assert.equal(layout.get('3')?.anchorDirection, 'top-center');
  assert.equal(layout.get('3')?.isClustered, false);
});

test('resolveMarkerCollisions splits 2 colliding points into top-left and top-right', () => {
  // Ninh Binh and Ha Long Bay (close in distance)
  const points: MarkerPointInput[] = [
    { sequence: 'nb', x: 380, y: 220, city: 'Ninh Binh' },
    { sequence: 'hl', x: 410, y: 200, city: 'Ha Long Bay' },
  ];

  const layout = resolveMarkerCollisions(points);

  assert.equal(layout.size, 2);
  const nb = layout.get('nb');
  const hl = layout.get('hl');

  assert.ok(nb);
  assert.ok(hl);
  assert.equal(nb?.isClustered, true);
  assert.equal(hl?.isClustered, true);
  assert.equal(nb?.clusterSize, 2);
  assert.equal(hl?.clusterSize, 2);

  // Leftmost point gets top-left, rightmost gets top-right
  assert.equal(nb?.anchorDirection, 'top-left');
  assert.equal(hl?.anchorDirection, 'top-right');
  assert.deepEqual(nb?.stemOffset, { x: -16, y: -14 });
  assert.deepEqual(hl?.stemOffset, { x: 16, y: -14 });
});

test('resolveMarkerCollisions handles vertically stacked 2-point clusters', () => {
  const points: MarkerPointInput[] = [
    { sequence: 'top', x: 400, y: 300, city: 'City A' },
    { sequence: 'bot', x: 405, y: 330, city: 'City B' },
  ];

  const layout = resolveMarkerCollisions(points);
  assert.equal(layout.get('top')?.anchorDirection, 'top-elevated');
  assert.equal(layout.get('bot')?.anchorDirection, 'top-center');
});

test('resolveMarkerCollisions distributes 3 colliding points across multi-directional slots', () => {
  // Hanoi, Ninh Binh, Ha Long Bay
  const points: MarkerPointInput[] = [
    { sequence: 'hn', x: 370, y: 190, city: 'Hanoi' },
    { sequence: 'nb', x: 380, y: 220, city: 'Ninh Binh' },
    { sequence: 'hl', x: 420, y: 200, city: 'Ha Long Bay' },
  ];

  const layout = resolveMarkerCollisions(points);

  assert.equal(layout.size, 3);
  const hn = layout.get('hn');
  const nb = layout.get('nb');
  const hl = layout.get('hl');

  assert.equal(hn?.clusterSize, 3);
  assert.equal(nb?.clusterSize, 3);
  assert.equal(hl?.clusterSize, 3);

  // Distinct anchor directions allocated
  const directions = new Set([hn?.anchorDirection, nb?.anchorDirection, hl?.anchorDirection]);
  assert.equal(directions.size, 3, 'All 3 points must have distinct anchor directions');
});

test('adjustAnchorForBounds clamps anchor away from container boundaries', () => {
  const defaultOpts = {
    collisionRadiusX: 140,
    collisionRadiusY: 52,
    containerWidth: 794,
    containerHeight: 1123,
    edgePadding: 35,
  };

  // Near top boundary
  const topPoint: MarkerPointInput = { sequence: '1', x: 400, y: 40 };
  assert.equal(adjustAnchorForBounds(topPoint, 'top-center', defaultOpts), 'bottom-center');
  assert.equal(adjustAnchorForBounds(topPoint, 'top-left', defaultOpts), 'bottom-left');
  assert.equal(adjustAnchorForBounds(topPoint, 'top-right', defaultOpts), 'bottom-right');

  // Near left boundary
  const leftPoint: MarkerPointInput = { sequence: '2', x: 40, y: 500 };
  assert.equal(adjustAnchorForBounds(leftPoint, 'top-left', defaultOpts), 'top-right');
  assert.equal(adjustAnchorForBounds(leftPoint, 'left', defaultOpts), 'top-right');

  // Near right boundary
  const rightPoint: MarkerPointInput = { sequence: '3', x: 760, y: 500 };
  assert.equal(adjustAnchorForBounds(rightPoint, 'top-right', defaultOpts), 'top-left');
  assert.equal(adjustAnchorForBounds(rightPoint, 'right', defaultOpts), 'top-left');
});

test('getStemOffsetForAnchor returns valid stem geometry', () => {
  const topCenter = getStemOffsetForAnchor('top-center');
  assert.equal(topCenter.x, 0);
  assert.equal(topCenter.y, -10);
  assert.equal(topCenter.needleLength, 10);

  const topElevated = getStemOffsetForAnchor('top-elevated');
  assert.equal(topElevated.x, 0);
  assert.equal(topElevated.y, -34);
  assert.equal(topElevated.needleLength, 34);

  const topLeft = getStemOffsetForAnchor('top-left');
  assert.equal(topLeft.x, -16);
  assert.equal(topLeft.y, -14);

  const topRight = getStemOffsetForAnchor('top-right');
  assert.equal(topRight.x, 16);
  assert.equal(topRight.y, -14);
});
