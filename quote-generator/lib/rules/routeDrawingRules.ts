/**
 * Pure Domain Rules for Continuous Curved Route Generation and Adaptive Curvature (ACMCS).
 *
 * 100% Pure Functions, 0 React/DOM dependencies, 0 network calls, 100% deterministic.
 */

export interface BoundingBox2D {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

export type CurvatureDirection = 'west' | 'east' | 'neutral';

export interface CurvatureDecision {
  side: CurvatureDirection;
  amplitude: number;
  score: number;
  normalVector: [number, number];
}

export interface CurvatureEvaluationOptions {
  /** Maximum bowing amplitude relative to chord distance. Default: 0.14 */
  maxBowingRatio?: number;
  /** Minimum distance to trigger bowing in degrees. Default: 2.0 */
  minDistForBowing?: number;
  /** Safety distance threshold in degrees to other waypoints. Default: 0.35 */
  obstacleSafetyMarginDeg?: number;
}

export interface SplineOptions {
  /** Tension parameter for Catmull-Rom tangents [0.2 .. 0.6]. Default: 0.38 */
  tension?: number;
  /** Number of interpolated sample points per route segment. Default: 36 */
  samplesPerSegment?: number;
  /** Curvature evaluation options */
  curvatureOptions?: CurvatureEvaluationOptions;
}

/**
 * 1. Geometric Primitive: Calculate West and East normal unit vectors for a geographic segment.
 * West normal has delta Lng < 0 (pointing Left / Inland / West).
 * East normal has delta Lng > 0 (pointing Right / Ocean / East).
 */
export function calculateSegmentNormal(
  p0: [number, number],
  p1: [number, number]
): {
  westNormal: [number, number];
  eastNormal: [number, number];
  chordDist: number;
} {
  const dLat = p1[0] - p0[0];
  const dLng = p1[1] - p0[1];
  const chordDist = Math.hypot(dLat, dLng) || 1e-6;

  // Standard 2D perpendicular normal vector (-dy, dx)
  let nLat = -dLng / chordDist;
  let nLng = dLat / chordDist;

  // Guarantee westNormal points West (negative longitude offset)
  // and eastNormal points East (positive longitude offset)
  if (nLng > 0) {
    nLat = -nLat;
    nLng = -nLng;
  }

  const westNormal: [number, number] = [nLat, nLng];
  const eastNormal: [number, number] = [-nLat, -nLng];

  return { westNormal, eastNormal, chordDist };
}

/**
 * 2. Geometric Primitive: Calculate minimum perpendicular/endpoint distance from a point to a segment.
 */
export function calculatePointToSegmentDistance(
  point: [number, number],
  p0: [number, number],
  p1: [number, number]
): number {
  const dx = p1[1] - p0[1];
  const dy = p1[0] - p0[0];
  const lenSq = dx * dx + dy * dy;

  if (lenSq < 1e-12) {
    return Math.hypot(point[0] - p0[0], point[1] - p0[1]);
  }

  // Projection parameter t of point onto line segment [0, 1]
  const t = Math.max(
    0,
    Math.min(1, ((point[1] - p0[1]) * dx + (point[0] - p0[0]) * dy) / lenSq)
  );

  const projLat = p0[0] + t * dy;
  const projLng = p0[1] + t * dx;

  return Math.hypot(point[0] - projLat, point[1] - projLng);
}

export interface SegmentCurvatureProfile {
  direction: CurvatureDirection;
  amplitude: number;
  curvatureRatio: number;
  normalVector: [number, number];
  score: number;
}

/**
 * 3. Pure Reconciler: Adaptive Clearance-Maximizing Curvature Selector (ACMCS)
 * Determines whether a route segment should bow West, East, or stay Neutral
 * and calculates the optimal curvature amplitude profile.
 */
export function calculateOptimalSegmentCurvatureProfile(
  segIndex: number,
  allCoordinates: Array<[number, number]>,
  options?: CurvatureEvaluationOptions
): SegmentCurvatureProfile {
  const n = allCoordinates.length;
  const p0 = allCoordinates[segIndex];
  const p1 = allCoordinates[segIndex + 1];

  if (!p0 || !p1) {
    return {
      direction: 'neutral',
      amplitude: 0,
      curvatureRatio: 0,
      score: 0,
      normalVector: [0, 0],
    };
  }

  const { westNormal, eastNormal, chordDist } = calculateSegmentNormal(p0, p1);
  const minDist = options?.minDistForBowing ?? 0.35;
  const safetyMargin = options?.obstacleSafetyMarginDeg ?? 0.35;

  // Very short segments (< 0.35 deg, ~35km) stay strictly neutral
  if (chordDist < minDist) {
    return {
      direction: 'neutral',
      amplitude: 0,
      curvatureRatio: 0,
      score: 100,
      normalVector: [0, 0],
    };
  }

  // Extract obstacle waypoints (all other waypoints in the trip except start and end of this segment)
  const obstacles: Array<[number, number]> = [];
  for (let i = 0; i < n; i++) {
    if (i !== segIndex && i !== segIndex + 1) {
      obstacles.push(allCoordinates[i]);
    }
  }

  // Target amplitude formulation based on chord distance and corridor clearance:
  // 1. Long-haul flight (chordDist >= 3.5 deg, e.g. Mekong -> Hanoi ~11 deg):
  //    Target amplitude ~ 1.5 - 1.8 deg (sweeping luxury aviation arc).
  // 2. Medium/short connector (0.5 <= chordDist < 3.5 deg, e.g. Saigon -> Mekong ~0.8 deg, Ninh Binh -> Ha Long ~1.3 deg):
  //    Target amplitude ~ 0.18 - 0.28 deg (relaxed scenic drive curve).
  let targetAmplitude: number;
  if (chordDist >= 3.5) {
    targetAmplitude = Math.min(1.85, Math.max(1.35, chordDist * 0.16));
  } else {
    targetAmplitude = Math.min(0.35, Math.max(0.18, chordDist * 0.22));
  }

  // Score candidate curves: West vs East
  const evaluateSide = (
    normal: [number, number]
  ): { score: number; maxSafeAmplitude: number } => {
    let score = 0;
    let minObstacleOnThisSideDist = Infinity;

    for (const obs of obstacles) {
      const dSeg = calculatePointToSegmentDistance(obs, p0, p1);

      // Check if obstacle lies on the same side as this normal vector
      const normalDot = normal[0] * (obs[0] - p0[0]) + normal[1] * (obs[1] - p0[1]);
      if (normalDot > 0) {
        // Obstacle is in front of the curve on this side
        if (dSeg < minObstacleOnThisSideDist) {
          minObstacleOnThisSideDist = dSeg;
        }
        score -= 300 / (dSeg + 0.1);
      } else {
        // Obstacle is on the opposite side: bowing in this direction moves safely AWAY from it!
        score += Math.log(dSeg + 1.0) * 40;
      }
    }

    // If there are obstacles on this side, cap amplitude by that obstacle's clearance;
    // otherwise if this side is open (e.g. West of Vietnam), use full targetAmplitude!
    const maxSafeAmplitude = Number.isFinite(minObstacleOnThisSideDist)
      ? Math.min(targetAmplitude, Math.max(0.12, minObstacleOnThisSideDist - safetyMargin * 0.5))
      : targetAmplitude;

    return { score, maxSafeAmplitude };
  };

  const westEval = evaluateSide(westNormal);
  const eastEval = evaluateSide(eastNormal);

  // If no obstacles, choose side based purely on segment trajectory direction:
  // - Northbound routes (dLat > 0): Westward bowing provides natural inland sky arc.
  // - Southbound/Southwest routes (dLat < 0): Eastward normal points outward to coastal plain.
  if (obstacles.length === 0) {
    const dLat = p1[0] - p0[0];
    const isHeadingSouth = dLat < 0;
    const chosenNormal = isHeadingSouth ? eastNormal : westNormal;
    const chosenSide = isHeadingSouth ? 'east' : 'west';
    return {
      direction: chosenSide,
      amplitude: targetAmplitude,
      curvatureRatio: targetAmplitude / chordDist,
      score: 50,
      normalVector: chosenNormal,
    };
  }

  // Choose the side with strictly superior clearance score
  if (westEval.score >= eastEval.score) {
    const amp = westEval.maxSafeAmplitude;
    return {
      direction: 'west',
      amplitude: amp,
      curvatureRatio: amp / chordDist,
      score: westEval.score,
      normalVector: westNormal,
    };
  } else {
    const amp = eastEval.maxSafeAmplitude;
    return {
      direction: 'east',
      amplitude: amp,
      curvatureRatio: amp / chordDist,
      score: eastEval.score,
      normalVector: eastNormal,
    };
  }
}

/**
 * 3. Backward-compatible wrapper for evaluateAdaptiveSegmentCurvature.
 */
export function evaluateAdaptiveSegmentCurvature(
  segIndex: number,
  allCoordinates: Array<[number, number]>,
  options?: CurvatureEvaluationOptions
): CurvatureDecision {
  const profile = calculateOptimalSegmentCurvatureProfile(segIndex, allCoordinates, options);
  return {
    side: profile.direction,
    amplitude: profile.amplitude,
    score: profile.score,
    normalVector: profile.normalVector,
  };
}

/**
 * 4. Pure Function: Calculate Continuous C1 Hermite Tangents with Monotone Turn Dampening.
 * Eliminates hairpin turnaround overshoot (e.g. Saigon -> Mekong -> Hanoi).
 */
export function calculateHermiteTangents(
  coordinates: Array<[number, number]>,
  tension = 0.38
): Array<[number, number]> {
  const n = coordinates.length;
  if (n < 2) return coordinates.map(() => [0, 0]);

  const tangents: Array<[number, number]> = [];

  for (let i = 0; i < n; i++) {
    if (i === 0) {
      // First point: Forward difference with gentle dampening
      const dLat = coordinates[1][0] - coordinates[0][0];
      const dLng = coordinates[1][1] - coordinates[0][1];
      tangents.push([dLat * 0.6, dLng * 0.6]);
    } else if (i === n - 1) {
      // Last point: Backward difference
      const dLat = coordinates[n - 1][0] - coordinates[n - 2][0];
      const dLng = coordinates[n - 1][1] - coordinates[n - 2][1];
      tangents.push([dLat * 0.6, dLng * 0.6]);
    } else {
      // Intermediate point: Centered difference with turn-angle dampening
      const uLat = coordinates[i][0] - coordinates[i - 1][0];
      const uLng = coordinates[i][1] - coordinates[i - 1][1];
      const vLat = coordinates[i + 1][0] - coordinates[i][0];
      const vLng = coordinates[i + 1][1] - coordinates[i][1];

      const uLen = Math.hypot(uLat, uLng) || 1;
      const vLen = Math.hypot(vLat, vLng) || 1;

      // Cosine of angle between incoming and outgoing segments
      const cosAngle = (uLat * vLat + uLng * vLng) / (uLen * vLen);

      // Dampen tangent if route makes a sharp reversal (e.g. Saigon -> Mekong -> Hanoi)
      // to eliminate unnatural fishhook loops
      let turnDampen = Math.max(0.15, (cosAngle + 1) / 2);
      if (uLen < 1.5 || vLen < 1.5) {
        // If one segment is a short local excursion, dampen even further to prevent long haul pull
        turnDampen *= 0.6;
      }

      const dLat = (coordinates[i + 1][0] - coordinates[i - 1][0]) * tension * turnDampen;
      const dLng = (coordinates[i + 1][1] - coordinates[i - 1][1]) * tension * turnDampen;
      tangents.push([dLat, dLng]);
    }
  }

  return tangents;
}

/**
 * 5. Pure Function: Sample a single Cubic Bezier Segment between P0 and P1.
 */
export function sampleCubicBezierSegment(
  p0: [number, number],
  p1: [number, number],
  c1: [number, number],
  c2: [number, number],
  samples = 36,
  includeStart = true
): Array<[number, number]> {
  const result: Array<[number, number]> = [];
  const startIdx = includeStart ? 0 : 1;

  for (let s = startIdx; s <= samples; s++) {
    const t = s / samples;
    const u = 1 - t;
    const lat =
      u * u * u * p0[0] +
      3 * u * u * t * c1[0] +
      3 * u * t * t * c2[0] +
      t * t * t * p1[0];
    const lng =
      u * u * u * p0[1] +
      3 * u * u * t * c1[1] +
      3 * u * t * t * c2[1] +
      t * t * t * p1[1];
    result.push([lat, lng]);
  }

  return result;
}

/**
 * 6. Pipeline Facade: Continuous Smooth Spline Generator with ACMCS Clearance Optimization.
 *
 * Full 100% Pure Function that coordinates:
 * - ACMCS Adaptive Curvature Decisions
 * - Monotone Hermite Tangent Dampening
 * - Piecewise Cubic Bezier Spline Sampling
 */
export function generateContinuousSmoothSpline(
  coordinates: Array<[number, number]>,
  options?: SplineOptions
): Array<[number, number]> {
  const n = coordinates.length;
  if (n < 2) return coordinates;

  const tension = options?.tension ?? 0.38;
  const samples = options?.samplesPerSegment ?? 36;
  const curvOpts = options?.curvatureOptions;

  // Single segment handling (N = 2)
  if (n === 2) {
    const p0 = coordinates[0];
    const p1 = coordinates[1];
    const decision = evaluateAdaptiveSegmentCurvature(0, coordinates, curvOpts);
    const dLat = p1[0] - p0[0];
    const dLng = p1[1] - p0[1];

    const offsetLat = decision.normalVector[0] * decision.amplitude * 0.5;
    const offsetLng = decision.normalVector[1] * decision.amplitude * 0.5;

    const c1: [number, number] = [
      p0[0] + (1 / 3) * dLat + offsetLat,
      p0[1] + (1 / 3) * dLng + offsetLng,
    ];
    const c2: [number, number] = [
      p0[0] + (2 / 3) * dLat + offsetLat,
      p0[1] + (2 / 3) * dLng + offsetLng,
    ];

    return sampleCubicBezierSegment(p0, p1, c1, c2, samples, true);
  }

  // Multi-segment handling (N >= 3)
  const tangents = calculateHermiteTangents(coordinates, tension);
  const result: Array<[number, number]> = [];

  for (let i = 0; i < n - 1; i++) {
    const p0 = coordinates[i];
    const p1 = coordinates[i + 1];
    const t0 = tangents[i];
    const t1 = tangents[i + 1];

    const decision = evaluateAdaptiveSegmentCurvature(i, coordinates, curvOpts);

    let c1Lat = p0[0] + (1 / 3) * t0[0];
    let c1Lng = p0[1] + (1 / 3) * t0[1];
    let c2Lat = p1[0] - (1 / 3) * t1[0];
    let c2Lng = p1[1] - (1 / 3) * t1[1];

    if (decision.side !== 'neutral' && decision.amplitude > 0) {
      const bowLat = decision.normalVector[0] * decision.amplitude;
      const bowLng = decision.normalVector[1] * decision.amplitude;
      c1Lat += bowLat * 0.7;
      c1Lng += bowLng * 0.7;
      c2Lat += bowLat * 0.9;
      c2Lng += bowLng * 0.9;
    }

    const includeStart = i === 0;
    const segmentPoints = sampleCubicBezierSegment(
      p0,
      p1,
      [c1Lat, c1Lng],
      [c2Lat, c2Lng],
      samples,
      includeStart
    );

    result.push(...segmentPoints);
  }

  return result;
}
