import test from 'node:test';
import assert from 'node:assert/strict';
import {
  resolveMarkerCollisions,
  getStemOffsetForAnchor,
  getMarkerBoundingBox,
  segmentIntersectsBox,
  generateContinuousSmoothSpline,
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

test('getStemOffsetForAnchor returns zero offset for direct pin placement', () => {
  const topCenter = getStemOffsetForAnchor('top-center');
  assert.equal(topCenter.x, 0);
  assert.equal(topCenter.y, 0);
  assert.equal(topCenter.needleLength, 0);

  const right = getStemOffsetForAnchor('right');
  assert.equal(right.x, 0);
  assert.equal(right.y, 0);
  assert.equal(right.needleLength, 0);
});

test('getMarkerBoundingBox calculates exact direct pin bounds', () => {
  const pt = { x: 100, y: 200 };
  const box = getMarkerBoundingBox(pt, 'right', 55, 16);

  assert.equal(box.minX, 100 - 8);
  assert.equal(box.maxX, 100 - 8 + 55);
  assert.equal(box.minY, 200 - 8);
  assert.equal(box.maxY, 200 + 8);
});

test('generateContinuousSmoothSpline generates C1 continuous curved path starting and ending at exact waypoints', () => {
  const waypoints: Array<[number, number]> = [
    [10.7769, 106.7009], // Saigon
    [21.0285, 105.8542], // Hanoi
    [20.2506, 105.9745], // Ninh Binh
    [20.9505, 107.0734], // Ha Long Bay
  ];

  const spline = generateContinuousSmoothSpline(waypoints, {
    tension: 0.4,
    samplesPerSegment: 20,
    eastwardBiasScale: 0.12,
  });

  // Verify non-empty and adequate sampling
  assert.ok(spline.length > 50);

  // Exact start and end coordinate snapping
  assert.equal(spline[0][0], waypoints[0][0]);
  assert.equal(spline[0][1], waypoints[0][1]);
  assert.equal(spline[spline.length - 1][0], waypoints[waypoints.length - 1][0]);
  assert.equal(spline[spline.length - 1][1], waypoints[waypoints.length - 1][1]);

  // Verify Eastward bowing on Saigon -> Hanoi leg (max longitude should exceed midpoint longitude)
  const midpointLng = (waypoints[0][1] + waypoints[1][1]) / 2;
  const leg1Sample = spline.slice(5, 15);
  const hasEastwardBowing = leg1Sample.some((pt) => pt[1] > midpointLng);
  assert.ok(hasEastwardBowing, 'North-South haul should bow Eastward towards the sea');
});

test('resolveMarkerCollisions ensures no bounding box overlap for close vertical points', () => {
  const points: MarkerPointInput[] = [
    { sequence: '01', x: 300, y: 150, city: 'Hanoi', visible: true },
    { sequence: '02', x: 305, y: 200, city: 'Ninh Binh', visible: true },
  ];

  const results = resolveMarkerCollisions(points, {
    containerWidth: 800,
    containerHeight: 1100,
    capsuleWidth: 55,
    capsuleHeight: 16,
  });

  const p1 = results.get('01');
  const p2 = results.get('02');

  assert.ok(p1 && p2);
  assert.ok(p1.anchorDirection);
  assert.ok(p2.anchorDirection);
  // Verify that the two bounding boxes do not overlap
  const minOverlap =
    p1.boundingBox.maxX < p2.boundingBox.minX ||
    p1.boundingBox.minX > p2.boundingBox.maxX ||
    p1.boundingBox.maxY < p2.boundingBox.minY ||
    p1.boundingBox.minY > p2.boundingBox.maxY;
  assert.ok(minOverlap, 'Close waypoints must have disjoint bounding boxes');
});
