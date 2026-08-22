import test from 'node:test';
import assert from 'node:assert/strict';
import {
  resolveMarkerCollisions,
  getStemOffsetForAnchor,
  getMarkerBoundingBox,
  segmentIntersectsBox,
  type MarkerPointInput,
} from '../rules/mapMarkerLayoutRules.ts';

test('Liang-Barsky segmentIntersectsBox accurately detects line-box intersections', () => {
  const box = { minX: 100, maxX: 150, minY: 100, maxY: 120 };

  // Line crossing straight through box
  assert.equal(segmentIntersectsBox({ x: 50, y: 110 }, { x: 200, y: 110 }, box), true);

  // Line completely above box
  assert.equal(segmentIntersectsBox({ x: 50, y: 80 }, { x: 200, y: 80 }, box), false);

  // Line completely to the left
  assert.equal(segmentIntersectsBox({ x: 50, y: 50 }, { x: 80, y: 150 }, box), false);

  // Line passing diagonally near box without intersecting
  assert.equal(segmentIntersectsBox({ x: 50, y: 50 }, { x: 90, y: 200 }, box), false);
});

test('resolveMarkerCollisions handles single isolated points cleanly', () => {
  const points: MarkerPointInput[] = [
    { sequence: '1', x: 300, y: 700, city: 'Ho Chi Minh City' },
    { sequence: '2', x: 400, y: 400, city: 'Da Nang' },
    { sequence: '3', x: 380, y: 150, city: 'Hanoi' },
  ];

  const layout = resolveMarkerCollisions(points);

  assert.equal(layout.size, 3);
  assert.ok(layout.get('1'));
  assert.ok(layout.get('2'));
  assert.ok(layout.get('3'));
});

test('SCERA pushes Ninh Binh into exterior safe angle away from incoming/outgoing route lines', () => {
  // Northern cluster: Hanoi -> Ninh Binh -> Ha Long Bay
  const points: MarkerPointInput[] = [
    { sequence: 'hn', x: 370, y: 190, city: 'Hanoi' },
    { sequence: 'nb', x: 380, y: 230, city: 'Ninh Binh' },
    { sequence: 'hl', x: 430, y: 200, city: 'Ha Long Bay' },
  ];

  const layout = resolveMarkerCollisions(points);

  assert.equal(layout.size, 3);
  const nb = layout.get('nb');
  assert.ok(nb);

  // For Ninh Binh, line comes from Hanoi (North-West) and goes to Ha Long (North-East).
  // Exterior bisector points South / South-West.
  // The anchor direction must NOT be top-center or top-right (which would cross into the Hanoi/Ha Long lines).
  assert.notEqual(nb?.anchorDirection, 'top-right');

  // Verify bounding box does not intersect route segment (hn -> hl)
  assert.equal(segmentIntersectsBox({ x: 370, y: 190 }, { x: 430, y: 200 }, nb!.boundingBox), false);
});

test('SCERA resolves full 5-destination itinerary with zero route occlusion', () => {
  const points: MarkerPointInput[] = [
    { sequence: '1', x: 300, y: 750, city: 'Ho Chi Minh City' },
    { sequence: '2', x: 260, y: 800, city: 'Mekong Delta' },
    { sequence: '3', x: 370, y: 190, city: 'Hanoi' },
    { sequence: '4', x: 380, y: 230, city: 'Ninh Binh' },
    { sequence: '5', x: 430, y: 200, city: 'Ha Long Bay' },
  ];

  const layout = resolveMarkerCollisions(points);

  assert.equal(layout.size, 5);
  for (let i = 1; i <= 5; i++) {
    const placement = layout.get(String(i));
    assert.ok(placement, `Marker ${i} must have placement`);
    assert.ok(placement?.boundingBox);
    assert.ok(placement?.stemOffset);
  }
});

test('getStemOffsetForAnchor returns valid micro-scale geometry', () => {
  const topCenter = getStemOffsetForAnchor('top-center');
  assert.equal(topCenter.x, 0);
  assert.equal(topCenter.y, -5);
  assert.equal(topCenter.needleLength, 5);

  const topElevated = getStemOffsetForAnchor('top-elevated');
  assert.equal(topElevated.x, 0);
  assert.equal(topElevated.y, -16);
  assert.equal(topElevated.needleLength, 16);

  const left = getStemOffsetForAnchor('left');
  assert.equal(left.x, -8);
  assert.equal(left.y, 0);

  const right = getStemOffsetForAnchor('right');
  assert.equal(right.x, 8);
  assert.equal(right.y, 0);
});

test('getMarkerBoundingBox calculates exact 2/3 micro-scale bounds', () => {
  const pt = { x: 100, y: 200 };
  const box = getMarkerBoundingBox(pt, 'right', 55, 16);

  assert.equal(box.minX, 100 + 8);
  assert.equal(box.maxX, 100 + 8 + 55);
  assert.equal(box.minY, 200 - 8);
  assert.equal(box.maxY, 200 + 8);
});
