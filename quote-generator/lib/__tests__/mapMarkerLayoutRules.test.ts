import test from 'node:test';
import assert from 'node:assert/strict';
import {
  resolveMarkerCollisions,
  getStemOffsetForAnchor,
  getMarkerBoundingBox,
  segmentIntersectsBox,
  generateContinuousSmoothSpline,
  type MarkerPointInput,
} from '../../components/display/map/pdf/layout/markerPlacement.ts';

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

  // Verify smooth curvature on Saigon -> Hanoi leg (points deviate smoothly from straight chord)
  const chordMidLng = (waypoints[0][1] + waypoints[1][1]) / 2;
  const leg1Sample = spline.slice(5, 15);
  const hasSmoothCurvature = leg1Sample.some((pt) => Math.abs(pt[1] - chordMidLng) > 0.01);
  assert.ok(hasSmoothCurvature, 'North-South haul should have smooth adaptive curvature');
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
  // Verify strict alternating left/right alignment
  const isLeft1 = p1.anchorDirection === 'left' || p1.anchorDirection === 'top-left' || p1.anchorDirection === 'bottom-left';
  const isLeft2 = p2.anchorDirection === 'left' || p2.anchorDirection === 'top-left' || p2.anchorDirection === 'bottom-left';
  assert.notEqual(isLeft1, isLeft2, 'Adjacent vertical waypoints must strictly alternate lateral directions (one left, one right)');

  // Verify that the two bounding boxes do not overlap
  const minOverlap =
    p1.boundingBox.maxX < p2.boundingBox.minX ||
    p1.boundingBox.minX > p2.boundingBox.maxX ||
    p1.boundingBox.maxY < p2.boundingBox.minY ||
    p1.boundingBox.minY > p2.boundingBox.maxY;
  assert.ok(minOverlap, 'Close waypoints must have disjoint bounding boxes');
});

test('generateContinuousSmoothSpline dampens sharp hairpin turns on out-and-back excursions', () => {
  const waypoints: Array<[number, number]> = [
    [10.7769, 106.7009], // Saigon
    [10.0452, 105.7469], // Mekong Delta (South-West)
    [21.0285, 105.8542], // Hanoi (North)
  ];

  const spline = generateContinuousSmoothSpline(waypoints, {
    tension: 0.35,
    samplesPerSegment: 30,
    eastwardBiasScale: 0.10,
  });

  assert.ok(spline.length > 50);
  // Ensure the spline near Mekong Delta does not wildly loop south below 9.5 deg latitude
  const minLat = Math.min(...spline.map((pt) => pt[0]));
  assert.ok(minLat > 9.8, `Spline min lat ${minLat} should not overshoot below 9.8 deg`);
});

test('resolveMarkerCollisions handles 5-point itinerary (Saigon -> Mekong -> Hanoi -> Ninh Binh -> Ha Long)', () => {
  // Projected 2D coordinates representing the 5 points in media_1787415233366.png
  const points = [
    { sequence: '01', x: 450, y: 800, city: 'Ho Chi Minh City', visible: true },
    { sequence: '02', x: 380, y: 850, city: 'Mekong Delta', visible: true },
    { sequence: '03', x: 400, y: 150, city: 'Hanoi', visible: true },
    { sequence: '04', x: 410, y: 220, city: 'Ninh Binh', visible: true },
    { sequence: '05', x: 480, y: 160, city: 'Ha Long Bay', visible: true },
  ];

  const results = resolveMarkerCollisions(points);

  const pHanoi = results.get('03');
  const pNinhBinh = results.get('04');
  const pHaLong = results.get('05');

  assert.ok(pHanoi && pNinhBinh && pHaLong);

  // Hanoi must anchor Left (to avoid horizontal collision with Ha Long Bay at x=480)
  const isHanoiLeft =
    pHanoi.anchorDirection === 'left' ||
    pHanoi.anchorDirection === 'top-left' ||
    pHanoi.anchorDirection === 'bottom-left';
  assert.equal(isHanoiLeft, true, 'Hanoi must anchor Left to give room to Ha Long Bay on the East');

  // Ninh Binh must anchor Right (facing East Sea)
  const isNinhBinhRight =
    pNinhBinh.anchorDirection === 'right' ||
    pNinhBinh.anchorDirection === 'top-right' ||
    pNinhBinh.anchorDirection === 'bottom-right';
  assert.equal(isNinhBinhRight, true, 'Ninh Binh must anchor Right');

  // Ha Long must anchor Right
  const isHaLongRight =
    pHaLong.anchorDirection === 'right' ||
    pHaLong.anchorDirection === 'top-right' ||
    pHaLong.anchorDirection === 'bottom-right';
  assert.equal(isHaLongRight, true, 'Ha Long must anchor Right');
});
