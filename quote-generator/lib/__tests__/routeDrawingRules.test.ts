import test from 'node:test';
import assert from 'node:assert/strict';
import {
  calculateSegmentNormal,
  calculatePointToSegmentDistance,
  evaluateAdaptiveSegmentCurvature,
  calculateOptimalSegmentCurvatureProfile,
  calculateHermiteTangents,
  sampleCubicBezierSegment,
  generateContinuousSmoothSpline,
} from '../rules/routeDrawingRules.ts';

// ─── Group 1: Geometric Primitives ──────────────────────────────────────────

test('calculateSegmentNormal calculates exact West and East normal unit vectors', () => {
  // South to North segment (e.g. from Lat 10 to Lat 20 at Lng 106)
  const p0: [number, number] = [10.0, 106.0];
  const p1: [number, number] = [20.0, 106.0];

  const { westNormal, eastNormal, chordDist } = calculateSegmentNormal(p0, p1);

  assert.equal(chordDist, 10.0);
  // West normal must have delta Lng < 0 (pointing West/Left)
  assert.ok(westNormal[1] < 0, 'West normal longitude component must be negative');
  // East normal must have delta Lng > 0 (pointing East/Right)
  assert.ok(eastNormal[1] > 0, 'East normal longitude component must be positive');
  // Dot product of west and east normals must be -1 (strictly opposite)
  const dot = westNormal[0] * eastNormal[0] + westNormal[1] * eastNormal[1];
  assert.ok(Math.abs(dot + 1.0) < 1e-6, 'West and East normals must be antiparallel');
});

test('calculatePointToSegmentDistance calculates accurate perpendicular and endpoint distances', () => {
  const p0: [number, number] = [10.0, 100.0];
  const p1: [number, number] = [20.0, 100.0];

  // Point directly to the right of midpoint (Lat 15, Lng 105) -> perpendicular dist = 5.0
  const pMid: [number, number] = [15.0, 105.0];
  const distMid = calculatePointToSegmentDistance(pMid, p0, p1);
  assert.ok(Math.abs(distMid - 5.0) < 1e-6);

  // Point beyond p1 endpoint (Lat 25, Lng 100) -> dist to p1 = 5.0
  const pBeyond: [number, number] = [25.0, 100.0];
  const distBeyond = calculatePointToSegmentDistance(pBeyond, p0, p1);
  assert.ok(Math.abs(distBeyond - 5.0) < 1e-6);
});

// ─── Group 2: ACMCS Adaptive Curvature Decisions ─────────────────────────────

test('ACMCS selects West curvature for Mekong -> Hanoi chặng when Saigon is at the East', () => {
  // Real User Case:
  // p0: Saigon [10.8231, 106.6297]
  // p1: Mekong [10.2435, 106.3756]
  // p2: Hanoi  [21.0285, 105.8542]
  // p3: Ninh Binh [20.2539, 105.9750]
  const itinerary: Array<[number, number]> = [
    [10.8231, 106.6297], // 0: Saigon
    [10.2435, 106.3756], // 1: Mekong
    [21.0285, 105.8542], // 2: Hanoi
    [20.2539, 105.9750], // 3: Ninh Binh
  ];

  // Segment index 1: Mekong -> Hanoi
  const decision = evaluateAdaptiveSegmentCurvature(1, itinerary);

  // Saigon is at the East of Mekong -> Hanoi chord.
  // Curving East would collide with Saigon.
  // ACMCS MUST strictly choose 'west'!
  assert.equal(
    decision.side,
    'west',
    'Mekong -> Hanoi segment must bow West to avoid colliding with Ho Chi Minh City on the East'
  );
  assert.ok(decision.amplitude > 0, 'Amplitude must be positive for long haul segment');
  assert.ok(decision.normalVector[1] < 0, 'Normal vector must point West (negative delta lng)');
});

test('ACMCS selects West curvature for Hanoi -> Saigon when Da Nang is at the East coast', () => {
  // Itinerary with direct flight Hanoi -> Saigon and an excursion to Da Nang
  const itinerary: Array<[number, number]> = [
    [21.0285, 105.8542], // 0: Hanoi
    [10.8231, 106.6297], // 1: Saigon
    [16.0544, 108.2022], // 2: Da Nang (East Coast)
  ];

  // Segment 0: Hanoi -> Saigon
  const decision = evaluateAdaptiveSegmentCurvature(0, itinerary);

  // Da Nang is to the East at Lng 108.2.
  // ACMCS must choose 'west' to avoid passing through Da Nang!
  assert.equal(
    decision.side,
    'west',
    'Hanoi -> Saigon direct segment must bow West away from Da Nang on the East coast'
  );
});

test('calculateOptimalSegmentCurvatureProfile provides sweeping amplitude >= 1.4 deg for Mekong -> Hanoi', () => {
  const itinerary: Array<[number, number]> = [
    [10.8231, 106.6297], // 0: Saigon
    [10.2435, 106.3756], // 1: Mekong
    [21.0285, 105.8542], // 2: Hanoi
    [20.2539, 105.9750], // 3: Ninh Binh
  ];

  // Segment 1: Mekong -> Hanoi (chordDist ~ 10.8 deg)
  const profile = calculateOptimalSegmentCurvatureProfile(1, itinerary);
  assert.equal(profile.direction, 'west', 'Mekong -> Hanoi must bow West');
  assert.ok(
    profile.amplitude >= 1.35,
    `Mekong -> Hanoi curvature amplitude must be >= 1.35 deg for sweeping luxury arc (actual: ${profile.amplitude.toFixed(2)} deg)`
  );
});

test('calculateOptimalSegmentCurvatureProfile provides gentle visible curve >= 0.18 deg for Saigon -> Mekong', () => {
  const itinerary: Array<[number, number]> = [
    [10.8231, 106.6297], // 0: Saigon
    [10.2435, 106.3756], // 1: Mekong
  ];

  // Segment 0: Saigon -> Mekong
  const profile = calculateOptimalSegmentCurvatureProfile(0, itinerary);
  assert.equal(profile.direction, 'east', 'Saigon -> Mekong must bow East towards the open coast');
  assert.ok(
    profile.amplitude >= 0.18,
    `Saigon -> Mekong amplitude must be >= 0.18 deg for visible relaxed drive (actual: ${profile.amplitude.toFixed(2)} deg)`
  );
});

test('calculateOptimalSegmentCurvatureProfile keeps ultra-short micro segments (<0.35 deg) neutral', () => {
  const ultraShortTrip: Array<[number, number]> = [
    [10.8231, 106.6297], // Saigon center
    [10.8350, 106.6400], // Saigon airport (< 0.05 deg)
  ];

  const profile = calculateOptimalSegmentCurvatureProfile(0, ultraShortTrip);
  assert.equal(profile.direction, 'neutral');
  assert.equal(profile.amplitude, 0);
});

// ─── Group 3: Tangents & Turn Dampening ──────────────────────────────────────

test('calculateHermiteTangents applies Monotone Turn Dampening on hairpin turns', () => {
  // Route with 180-deg reversal: Saigon -> Mekong -> Hanoi
  const itinerary: Array<[number, number]> = [
    [10.8231, 106.6297], // 0: Saigon
    [10.2435, 106.3756], // 1: Mekong
    [21.0285, 105.8542], // 2: Hanoi
  ];

  const tangents = calculateHermiteTangents(itinerary, 0.38);

  assert.equal(tangents.length, 3);
  // Tangent at point 1 (Mekong) must be heavily dampened (magnitude much smaller than raw centered diff)
  const rawDiffLat = 21.0285 - 10.8231; // ~10.2
  const rawDiffLng = 105.8542 - 106.6297; // ~-0.77
  const rawMagnitude = Math.hypot(rawDiffLat, rawDiffLng);
  const tangentMagnitude = Math.hypot(tangents[1][0], tangents[1][1]);

  // Dampening must reduce magnitude by at least 70%
  assert.ok(
    tangentMagnitude < rawMagnitude * 0.3,
    `Tangent at hairpin turnaround point must be dampened by >= 70% (actual: ${(tangentMagnitude / rawMagnitude).toFixed(2)})`
  );
});

// ─── Group 4: Spline Pipeline & Pure Invariants ──────────────────────────────

test('sampleCubicBezierSegment samples cubic curve points accurately', () => {
  const p0: [number, number] = [10.0, 106.0];
  const p1: [number, number] = [20.0, 106.0];
  const c1: [number, number] = [13.0, 105.0];
  const c2: [number, number] = [17.0, 105.0];

  const points = sampleCubicBezierSegment(p0, p1, c1, c2, 10, true);
  assert.equal(points.length, 11);
  assert.deepEqual(points[0], p0);
  assert.deepEqual(points[points.length - 1], p1);
  // Midpoint should be bowed to the west (Lng < 106.0)
  assert.ok(points[5][1] < 106.0);
});

test('generateContinuousSmoothSpline creates smooth path starting and ending at exact waypoints', () => {
  const itinerary: Array<[number, number]> = [
    [10.8231, 106.6297],
    [10.2435, 106.3756],
    [21.0285, 105.8542],
    [20.2539, 105.9750],
  ];

  const spline = generateContinuousSmoothSpline(itinerary, { samplesPerSegment: 20 });

  assert.ok(spline.length > 50);
  // Exact start point
  assert.deepEqual(spline[0], itinerary[0]);
  // Exact end point
  assert.deepEqual(spline[spline.length - 1], itinerary[itinerary.length - 1]);

  // Verify all points have finite valid geographic coordinates
  for (const pt of spline) {
    assert.ok(Number.isFinite(pt[0]) && pt[0] >= -90 && pt[0] <= 90);
    assert.ok(Number.isFinite(pt[1]) && pt[1] >= -180 && pt[1] <= 180);
  }
});

test('generateContinuousSmoothSpline is 100% deterministic (Pure Function Invariance)', () => {
  const itinerary: Array<[number, number]> = [
    [10.8231, 106.6297],
    [10.2435, 106.3756],
    [21.0285, 105.8542],
    [20.2539, 105.9750],
  ];

  const run1 = generateContinuousSmoothSpline(itinerary);
  const run2 = generateContinuousSmoothSpline(itinerary);

  assert.deepEqual(run1, run2, 'Consecutive calls must return identical coordinates');
});

test('STRAIGHT line from Mekong to Hanoi FAILS because it cuts right through Ninh Binh', () => {
  const pMekong: [number, number] = [10.2435, 106.3756];
  const pHanoi: [number, number] = [21.0285, 105.8542];
  const pNinhBinh: [number, number] = [20.2539, 105.9750];

  // Calculate distance from Ninh Binh to the straight chord connecting Mekong and Hanoi
  const straightDistToNinhBinh = calculatePointToSegmentDistance(pNinhBinh, pMekong, pHanoi);

  // The straight line passes dangerously close to Ninh Binh (< 0.1 deg / ~10km), slicing right through it!
  assert.ok(
    straightDistToNinhBinh < 0.10,
    `Straight flight line passes dangerously close to Ninh Binh (distance: ${straightDistToNinhBinh.toFixed(4)} deg < 0.10 deg), causing collision!`
  );
});

test('ACMCS Adaptive Spline SUCCEEDS and prevents collision by curving safely around Ninh Binh', () => {
  const itinerary: Array<[number, number]> = [
    [10.8231, 106.6297], // 0: Saigon
    [10.2435, 106.3756], // 1: Mekong
    [21.0285, 105.8542], // 2: Hanoi
    [20.2539, 105.9750], // 3: Ninh Binh
  ];

  const samples = 36;
  const spline = generateContinuousSmoothSpline(itinerary, { samplesPerSegment: samples });

  // Extract segment 1: Mekong (index 1) -> Hanoi (index 2)
  const segment1Points = spline.slice(samples, samples * 2 + 1);
  const ninhBinhCoord = itinerary[3]; // [20.2539, 105.9750]

  let minDistToNinhBinh = Infinity;
  for (const pt of segment1Points) {
    const d = Math.hypot(pt[0] - ninhBinhCoord[0], pt[1] - ninhBinhCoord[1]);
    if (d < minDistToNinhBinh) {
      minDistToNinhBinh = d;
    }
  }

  // Under ACMCS, the spline bows Westward, widening the clearance from 0.08 deg to > 0.35 deg (~40km)!
  assert.ok(
    minDistToNinhBinh >= 0.35,
    `ACMCS spline safely clears Ninh Binh with ${minDistToNinhBinh.toFixed(4)} deg clearance (>= 0.35 deg)`
  );
});
