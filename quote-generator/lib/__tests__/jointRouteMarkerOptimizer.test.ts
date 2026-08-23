import test from 'node:test';
import assert from 'node:assert/strict';
import {
  optimizeJointRouteLayout,
  getMarkerGeoBoundingBox,
  splineIntersectsMarkerBox,
  generateCandidateSpline,
  type MarkerPoint2D,
  type RouteSegment2D,
} from '../rules/jointRouteMarkerOptimizer.ts';

// ─── Test 1: 4-Destination Route (Saigon -> Mekong -> Hanoi -> Ninh Binh) ────

test('4-Destination Trip: FAILS if Ninh Binh is left-anchored, PASSES if right-anchored', () => {
  const pSaigon: MarkerPoint2D = { sequence: '01', lat: 10.8231, lng: 106.6297, name: 'Ho Chi Minh City' };
  const pMekong: MarkerPoint2D = { sequence: '02', lat: 10.2435, lng: 106.3756, name: 'Mekong Delta' };
  const pHanoi: MarkerPoint2D = { sequence: '03', lat: 21.0285, lng: 105.8542, name: 'Hanoi' };
  const pNinhBinh: MarkerPoint2D = { sequence: '04', lat: 20.2539, lng: 105.9750, name: 'Ninh Binh' };

  const points = [pSaigon, pMekong, pHanoi, pNinhBinh];
  const segments: RouteSegment2D[] = [
    { fromIndex: 0, toIndex: 1, fromSequence: '01', toSequence: '02' }, // Saigon -> Mekong
    { fromIndex: 1, toIndex: 2, fromSequence: '02', toSequence: '03' }, // Mekong -> Hanoi
    { fromIndex: 2, toIndex: 3, fromSequence: '03', toSequence: '04' }, // Hanoi -> Ninh Binh
  ];

  // Generate flight spline for Mekong -> Hanoi curving West
  const westFlightSpline = generateCandidateSpline(
    [pMekong.lat, pMekong.lng],
    [pHanoi.lat, pHanoi.lng],
    'west',
    0.75
  );

  // 1. If Ninh Binh is anchored LEFT (Westward):
  // The left-pointing box extends into the flight corridor [105.02 .. 105.97]
  const leftBoxNinhBinh = getMarkerGeoBoundingBox(pNinhBinh.lat, pNinhBinh.lng, 'left', 0.95, 0.35);
  const collidesWhenLeft = splineIntersectsMarkerBox(westFlightSpline, leftBoxNinhBinh, 0.05);

  // Assert FAILURE when left-anchored (line cuts through Ninh Binh label box!)
  assert.equal(
    collidesWhenLeft,
    true,
    'Expected FAILURE: Westward flight Mekong -> Hanoi collides with Ninh Binh when Ninh Binh is left-anchored!'
  );

  // 2. If Ninh Binh is anchored RIGHT (Eastward):
  // The right-pointing box extends into the open East Sea [105.97 .. 106.92]
  const rightBoxNinhBinh = getMarkerGeoBoundingBox(pNinhBinh.lat, pNinhBinh.lng, 'right', 0.95, 0.35);
  const collidesWhenRight = splineIntersectsMarkerBox(westFlightSpline, rightBoxNinhBinh, 0.05);

  // Assert PASS when right-anchored (0% collision, completely open corridor!)
  assert.equal(
    collidesWhenRight,
    false,
    'Expected PASS: Westward flight Mekong -> Hanoi completely clears Ninh Binh when Ninh Binh is right-anchored!'
  );

  // 3. Run Joint Global Optimizer JRM-GEO to verify that it automatically chooses right-anchored Ninh Binh
  const result = optimizeJointRouteLayout(points, segments);
  assert.equal(result.isCollisionFree, true);
  assert.equal(result.markerAnchors.get('04'), 'right', 'Optimizer must automatically choose right-aligned Ninh Binh');
  assert.equal(result.segmentCurvatures[1].direction, 'west', 'Optimizer must choose west curvature for Mekong -> Hanoi');
});

// ─── Test 2: 7-Day 5-Destination Full Itinerary (Saigon -> Mekong -> Saigon -> Hanoi -> Ninh Binh -> Hanoi -> Ha Long) ───

test('7-Day 5-Destination Comprehensive Itinerary: satisfies 100% of line and marker direction rules', () => {
  // Day 1: Ho Chi Minh
  // Day 2: Mekong Delta
  // Day 3: Ho Chi Minh
  // Day 4: Hanoi
  // Day 5: Ninh Binh
  // Day 6: Hanoi
  // Day 7: Ha Long Bay
  const points: MarkerPoint2D[] = [
    { sequence: '01', lat: 10.8231, lng: 106.6297, name: 'Ho Chi Minh City' }, // Index 0
    { sequence: '02', lat: 10.2435, lng: 106.3756, name: 'Mekong Delta' },     // Index 1
    { sequence: '03', lat: 21.0285, lng: 105.8542, name: 'Hanoi' },            // Index 2
    { sequence: '04', lat: 20.2539, lng: 105.9750, name: 'Ninh Binh' },        // Index 3
    { sequence: '05', lat: 20.9599, lng: 107.0436, name: 'Ha Long Bay' },      // Index 4
  ];

  // 5 Lines / Segments:
  // 1. Ho Chi Minh -> Mekong
  // 2. Mekong -> Ho Chi Minh
  // 3. Ho Chi Minh -> Hanoi
  // 4. Hanoi -> Ninh Binh
  // 5. Hanoi -> Ha Long Bay
  const segments: RouteSegment2D[] = [
    { fromIndex: 0, toIndex: 1, fromSequence: '01', toSequence: '02' }, // Ho Chi Minh -> Mekong
    { fromIndex: 1, toIndex: 0, fromSequence: '02', toSequence: '01' }, // Mekong -> Ho Chi Minh
    { fromIndex: 0, toIndex: 2, fromSequence: '01', toSequence: '03' }, // Ho Chi Minh -> Hanoi
    { fromIndex: 2, toIndex: 3, fromSequence: '03', toSequence: '04' }, // Hanoi -> Ninh Binh
    { fromIndex: 2, toIndex: 4, fromSequence: '03', toSequence: '05' }, // Hanoi -> Ha Long Bay
  ];

  const result = optimizeJointRouteLayout(points, segments);

  // 1. Total lines count
  assert.equal(result.segmentCurvatures.length, 5, 'Must produce exactly 5 route lines');
  assert.equal(result.isCollisionFree, true, 'Global layout must be 100% collision-free');

  // 2. Lateral Marker Alignments (Đông - Tây)
  // - Ho Chi Minh: hướng Đông (Right)
  // - Mekong: hướng Tây (Left)
  // - Hanoi: hướng Tây (Left)
  // - Ninh Binh: hướng Đông (Right)
  // - Ha Long Bay: hướng Đông (Right)
  assert.equal(result.markerAnchors.get('01'), 'right', 'Ho Chi Minh marker must be anchored East (Right)');
  assert.equal(result.markerAnchors.get('02'), 'left', 'Mekong Delta marker must be anchored West (Left)');
  assert.equal(result.markerAnchors.get('03'), 'left', 'Hanoi marker must be anchored West (Left)');
  assert.equal(result.markerAnchors.get('04'), 'right', 'Ninh Binh marker must be anchored East (Right)');
  assert.equal(result.markerAnchors.get('05'), 'right', 'Ha Long Bay marker must be anchored East (Right)');

  // 3. Line Directions
  // - Ho Chi Minh -> Mekong: line hướng Đông / tự nhiên
  // - Ho Chi Minh -> Hanoi: line hướng Tây (West)
  // - Hanoi -> Ninh Binh: line hướng Đông / ở dưới (below / east)
  // - Hanoi -> Ha Long: line hướng Đông / ở trên (above / east)
  const hcmToMekong = result.segmentCurvatures[0];
  const hcmToHanoi = result.segmentCurvatures[2];
  const hanoiToNinhBinh = result.segmentCurvatures[3];
  const hanoiToHaLong = result.segmentCurvatures[4];

  assert.ok(hcmToMekong.amplitude >= 0, 'HCM -> Mekong line amplitude must be valid');
  assert.equal(hcmToHanoi.direction, 'west', 'Ho Chi Minh -> Hanoi line must curve West');
  assert.ok(
    hanoiToNinhBinh.direction === 'below' || hanoiToNinhBinh.direction === 'east',
    'Hanoi -> Ninh Binh line must curve East / Below'
  );
  assert.ok(
    hanoiToHaLong.direction === 'above' || hanoiToHaLong.direction === 'east',
    'Hanoi -> Ha Long Bay line must curve East / Above'
  );
});

// ─── Test Case 5: Direct RCA Verification for media_1787415233366.png ───────────

test('Test Case 5 (RCA Verification): Hanoi MUST anchor Left, Ninh Binh MUST anchor Right', () => {
  const pSaigon: MarkerPoint2D = { sequence: '01', lat: 10.8231, lng: 106.6297, name: 'Ho Chi Minh City' };
  const pMekong: MarkerPoint2D = { sequence: '02', lat: 10.2435, lng: 106.3756, name: 'Mekong Delta' };
  const pHanoi: MarkerPoint2D = { sequence: '03', lat: 21.0285, lng: 105.8542, name: 'Hanoi' };
  const pNinhBinh: MarkerPoint2D = { sequence: '04', lat: 20.2539, lng: 105.9750, name: 'Ninh Binh' };
  const pHaLong: MarkerPoint2D = { sequence: '05', lat: 20.9599, lng: 107.0436, name: 'Ha Long Bay' };

  const points = [pSaigon, pMekong, pHanoi, pNinhBinh, pHaLong];
  const segments: RouteSegment2D[] = [
    { fromIndex: 0, toIndex: 1, fromSequence: '01', toSequence: '02' }, // Saigon -> Mekong
    { fromIndex: 1, toIndex: 2, fromSequence: '02', toSequence: '03' }, // Mekong -> Hanoi
    { fromIndex: 2, toIndex: 3, fromSequence: '03', toSequence: '04' }, // Hanoi -> Ninh Binh
    { fromIndex: 2, toIndex: 4, fromSequence: '03', toSequence: '05' }, // Hanoi -> Ha Long Bay
  ];

  const result = optimizeJointRouteLayout(points, segments);

  // 1. Hanoi MUST anchor Left (West) to prevent overlapping Ha Long Bay on the East
  assert.equal(
    result.markerAnchors.get('03'),
    'left',
    'Hanoi MUST anchor Left to prevent colliding horizontally with Ha Long Bay!'
  );

  // 2. Ninh Binh MUST anchor Right (East) to prevent colliding with the Westward flight line
  assert.equal(
    result.markerAnchors.get('04'),
    'right',
    'Ninh Binh MUST anchor Right to leave the West corridor completely clear for Mekong -> Hanoi flight!'
  );

  // 3. Ha Long Bay MUST anchor Right (East) facing the open sea
  assert.equal(
    result.markerAnchors.get('05'),
    'right',
    'Ha Long Bay MUST anchor Right facing the open Gulf of Tonkin'
  );

  // 4. Saigon MUST anchor Right and Mekong MUST anchor Left
  assert.equal(result.markerAnchors.get('01'), 'right', 'Saigon MUST anchor Right');
  assert.equal(result.markerAnchors.get('02'), 'left', 'Mekong MUST anchor Left');

  // 5. Zero collisions
  assert.equal(result.isCollisionFree, true, 'Resulting layout must be 100% collision-free');
});
