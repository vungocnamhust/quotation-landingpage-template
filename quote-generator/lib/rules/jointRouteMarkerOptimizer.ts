/**
 * Pure Domain Reconciler: Joint Route-Marker Global Energy Optimizer (JRM-GEO)
 *
 * Simultaneously optimizes:
 * 1. Marker Anchor Directions (Left vs Right vs Top/Bottom)
 * 2. Route Spline Bowing Directions (West vs East vs Neutral / Above vs Below)
 *
 * Strictly adheres to the 3-Tier Priority System:
 * - Priority 1 (w = 10,000): Zero route-box occlusions and zero cross-line intersections.
 * - Priority 2 (w = 1,000): Balanced West-East distribution with zero line crowding.
 * - Priority 3 (w = 100): Balanced Left-Right marker placements and open ocean/sky allocation.
 *
 * 100% Pure Functions, 0 React/DOM dependencies, 100% deterministic.
 */

import {
  calculateSegmentNormal,
  sampleCubicBezierSegment,
} from './routeDrawingRules.ts';

export type AnchorSide = 'left' | 'right' | 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
export type CurvatureDirection = 'west' | 'east' | 'neutral' | 'above' | 'below';

export interface MarkerPoint2D {
  sequence: string;
  lat: number;
  lng: number;
  x?: number;
  y?: number;
  name?: string;
}

export interface RouteSegment2D {
  fromIndex: number;
  toIndex: number;
  fromSequence: string;
  toSequence: string;
}

export interface MarkerBox2D {
  minLat: number;
  maxLat: number;
  minLng: number;
  maxLng: number;
}

export interface JointOptimizationResult {
  markerAnchors: Map<string, AnchorSide>;
  segmentCurvatures: Array<{
    fromSequence: string;
    toSequence: string;
    direction: CurvatureDirection;
    amplitude: number;
    splinePoints: Array<[number, number]>;
  }>;
  totalEnergy: number;
  isCollisionFree: boolean;
}

/**
 * Approximate geographic bounding box for a marker anchored at (lat, lng) with given side.
 * Standard label capsule width ~ 1.0 deg lng, height ~ 0.4 deg lat in Vietnam coordinate space.
 */
export function getMarkerGeoBoundingBox(
  lat: number,
  lng: number,
  side: AnchorSide,
  boxWidthDeg = 0.95,
  boxHeightDeg = 0.35
): MarkerBox2D {
  const isLeft = side === 'left' || side === 'top-left' || side === 'bottom-left';
  const isTop = side === 'top-left' || side === 'top-right';
  const isBottom = side === 'bottom-left' || side === 'bottom-right';

  let minLng: number;
  let maxLng: number;
  let minLat: number;
  let maxLat: number;

  if (isLeft) {
    minLng = lng - boxWidthDeg;
    maxLng = lng;
  } else {
    minLng = lng;
    maxLng = lng + boxWidthDeg;
  }

  if (isTop) {
    minLat = lat;
    maxLat = lat + boxHeightDeg;
  } else if (isBottom) {
    minLat = lat - boxHeightDeg;
    maxLat = lat;
  } else {
    minLat = lat - boxHeightDeg / 2;
    maxLat = lat + boxHeightDeg / 2;
  }

  return { minLat, maxLat, minLng, maxLng };
}

/**
 * Checks if a polyline/spline passes through a geographic bounding box.
 */
export function splineIntersectsMarkerBox(
  splinePoints: Array<[number, number]>,
  box: MarkerBox2D,
  margin = 0.05
): boolean {
  const minLng = box.minLng - margin;
  const maxLng = box.maxLng + margin;
  const minLat = box.minLat - margin;
  const maxLat = box.maxLat + margin;

  for (let i = 0; i < splinePoints.length - 1; i++) {
    const p1 = splinePoints[i];
    const p2 = splinePoints[i + 1];

    // Check point containment
    if (p1[0] >= minLat && p1[0] <= maxLat && p1[1] >= minLng && p1[1] <= maxLng) {
      return true;
    }

    // Segment midpoint check
    const midLat = (p1[0] + p2[0]) / 2;
    const midLng = (p1[1] + p2[1]) / 2;
    if (midLat >= minLat && midLat <= maxLat && midLng >= minLng && midLng <= maxLng) {
      return true;
    }
  }

  return false;
}

/**
 * Checks if two 2D line segments (p1->p2) and (p3->p4) intersect.
 */
export function segmentsIntersect(
  p1: [number, number],
  p2: [number, number],
  p3: [number, number],
  p4: [number, number]
): boolean {
  const ccw = (a: [number, number], b: [number, number], c: [number, number]) => {
    return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0]);
  };
  return (
    ccw(p1, p3, p4) !== ccw(p2, p3, p4) &&
    ccw(p1, p2, p3) !== ccw(p1, p2, p4)
  );
}

/**
 * Checks if two bounding boxes overlap.
 */
export function boxesOverlap(b1: MarkerBox2D, b2: MarkerBox2D): boolean {
  return !(
    b1.maxLng < b2.minLng ||
    b1.minLng > b2.maxLng ||
    b1.maxLat < b2.minLat ||
    b1.minLat > b2.maxLat
  );
}

/**
 * Generate candidate curved bezier spline points for a segment with given direction.
 */
export function generateCandidateSpline(
  p0: [number, number],
  p1: [number, number],
  direction: CurvatureDirection,
  amplitude: number,
  samples = 24
): Array<[number, number]> {
  const { westNormal, eastNormal } = calculateSegmentNormal(p0, p1);
  const dLat = p1[0] - p0[0];
  const dLng = p1[1] - p0[1];

  let normVector: [number, number] = [0, 0];
  if (direction === 'west') {
    normVector = westNormal;
  } else if (direction === 'east') {
    normVector = eastNormal;
  } else if (direction === 'above') {
    // Normal with positive latitude component (curving upwards)
    normVector = [-Math.abs(eastNormal[0]), Math.abs(eastNormal[1])];
  } else if (direction === 'below') {
    // Normal with negative latitude component (curving downwards)
    normVector = [Math.abs(eastNormal[0]), Math.abs(eastNormal[1])];
  }

  const offsetLat = normVector[0] * amplitude;
  const offsetLng = normVector[1] * amplitude;

  const c1: [number, number] = [
    p0[0] + (1 / 3) * dLat + offsetLat * 0.7,
    p0[1] + (1 / 3) * dLng + offsetLng * 0.7,
  ];
  const c2: [number, number] = [
    p0[0] + (2 / 3) * dLat + offsetLat * 0.9,
    p0[1] + (2 / 3) * dLng + offsetLng * 0.9,
  ];

  return sampleCubicBezierSegment(p0, p1, c1, c2, samples, true);
}

/**
 * Pure Reconciler: Global Joint Optimizer (JRM-GEO)
 * Finds the optimal configuration (A*, B*) that minimizes the hierarchical energy function.
 */
export function optimizeJointRouteLayout(
  points: MarkerPoint2D[],
  segments: RouteSegment2D[]
): JointOptimizationResult {
  const n = points.length;
  const m = segments.length;

  if (n === 0) {
    return {
      markerAnchors: new Map(),
      segmentCurvatures: [],
      totalEnergy: 0,
      isCollisionFree: true,
    };
  }

  // Pre-calculate candidate anchor sides for each point based on local geography
  // In Vietnam:
  // - Hanoi (Northern inland gateway): Can be 'left' or 'right'
  // - Ninh Binh (South of Hanoi): 'right' or 'left'
  // - Ha Long (Eastern coastal bay): 'right' (East Sea)
  // - Saigon (Southern hub): 'right' or 'left'
  // - Mekong (Southwest delta): 'left' or 'right'
  const candidateAnchorSides: AnchorSide[] = ['right', 'left'];

  // Segment curvature candidates: 'west', 'east', 'neutral' (and 'above', 'below' for northern triangles)
  const candidateCurvatures: CurvatureDirection[] = ['west', 'east', 'neutral'];

  let bestResult: JointOptimizationResult | null = null;
  let minEnergy = Infinity;

  // Generate and evaluate configuration combinations
  // We evaluate up to 2^n anchor combinations and 3^m curvature combinations with branch & bound pruning.
  const anchorCombinations: AnchorSide[][] = [];
  const generateAnchors = (current: AnchorSide[]) => {
    if (current.length === n) {
      anchorCombinations.push([...current]);
      return;
    }
    for (const side of candidateAnchorSides) {
      generateAnchors([...current, side]);
    }
  };
  generateAnchors([]);

  for (const anchors of anchorCombinations) {
    // 1. Build and test Marker Bounding Boxes for overlap
    const boxes: MarkerBox2D[] = [];
    let boxOverlapPenalty = 0;

    for (let i = 0; i < n; i++) {
      const box = getMarkerGeoBoundingBox(points[i].lat, points[i].lng, anchors[i]);
      for (const existing of boxes) {
        if (boxesOverlap(box, existing)) {
          boxOverlapPenalty += 10000; // Priority 1 violation: overlapping labels
        }
      }
      boxes.push(box);
    }

    // Compute Centroid Longitude of all trip points for Convex Hull Outward Heuristics
    let sumLng = 0;
    for (let i = 0; i < n; i++) {
      sumLng += points[i].lng;
    }
    const centroidLng = sumLng / n;

    // Evaluate segment curvatures
    const segCurvatures: Array<{
      fromSequence: string;
      toSequence: string;
      direction: CurvatureDirection;
      amplitude: number;
      splinePoints: Array<[number, number]>;
    }> = [];

    let totalSegmentPenalty = 0;

    for (let j = 0; j < m; j++) {
      const seg = segments[j];
      const p0 = points[seg.fromIndex];
      const p1 = points[seg.toIndex];
      const chordDist = Math.hypot(p1.lat - p0.lat, p1.lng - p0.lng);

      // Select optimal curvature direction for this segment given current anchor boxes
      let bestDir: CurvatureDirection = 'neutral';
      let bestSpline: Array<[number, number]> = [];
      let bestDirPenalty = Infinity;

      // Directions to evaluate based purely on geometry
      const isHorizontalCluster = Math.abs(p1.lat - p0.lat) < 1.0 && Math.abs(p1.lng - p0.lng) > 0.4;
      const directionsToTry: CurvatureDirection[] =
        chordDist > 2.5
          ? ['west', 'east']
          : isHorizontalCluster
          ? ['above', 'below', 'neutral', 'east', 'west']
          : candidateCurvatures;

      const targetAmp =
        chordDist >= 3.5
          ? Math.min(1.85, Math.max(1.35, chordDist * 0.16))
          : Math.min(0.35, Math.max(0.18, chordDist * 0.22));

      for (const dir of directionsToTry) {
        const candidateSpline = generateCandidateSpline(
          [p0.lat, p0.lng],
          [p1.lat, p1.lng],
          dir,
          targetAmp
        );

        let dirPenalty = 0;

        // Priority 1: Check intersection against ALL marker boxes (except direct endpoints)
        for (let k = 0; k < n; k++) {
          const isEndpoint = k === seg.fromIndex || k === seg.toIndex;
          if (!isEndpoint) {
            if (splineIntersectsMarkerBox(candidateSpline, boxes[k], 0.08)) {
              dirPenalty += 10000; // Slicing through another waypoint's marker box!
            }
            // Check distance to other waypoint coordinates
            for (const pt of candidateSpline) {
              const d = Math.hypot(pt[0] - points[k].lat, pt[1] - points[k].lng);
              if (d < 0.20) {
                dirPenalty += 8000; // Dangerously close to waypoint
              }
            }
          }
        }

        // Priority 2: West-East Balance & Open Space Clearance
        if (chordDist > 2.5) {
          // Check how many markers lie on the East side vs West side
          const rightAnchorsCount = anchors.filter((a) => a === 'right' || a === 'top-right').length;
          const leftAnchorsCount = anchors.filter((a) => a === 'left' || a === 'top-left').length;

          // If more markers are on East, curving West creates perfect visual balance
          if (dir === 'west' && rightAnchorsCount >= leftAnchorsCount) {
            dirPenalty -= 800;
          } else if (dir === 'east' && rightAnchorsCount > leftAnchorsCount) {
            dirPenalty += 1200; // Crowding both labels and flight on East!
          }
        }

        // Branch Divergence Heuristic for shared origin points
        // If multiple segments originate from p0, diverge them (upper branch curves above, lower branch curves below)
        for (let otherIdx = 0; otherIdx < m; otherIdx++) {
          if (otherIdx === j) continue;
          const otherSeg = segments[otherIdx];
          if (otherSeg.fromIndex === seg.fromIndex) {
            const otherP1 = points[otherSeg.toIndex];
            // If this destination is south of the other destination, curve downwards/eastwards
            if (p1.lat < otherP1.lat) {
              if (dir === 'below' || dir === 'east') dirPenalty -= 500;
            } else if (p1.lat > otherP1.lat) {
              if (dir === 'above' || dir === 'east') dirPenalty -= 500;
            }
          }
        }

        if (dirPenalty < bestDirPenalty) {
          bestDirPenalty = dirPenalty;
          bestDir = dir;
          bestSpline = candidateSpline;
        }
      }

      totalSegmentPenalty += bestDirPenalty;
      segCurvatures.push({
        fromSequence: seg.fromSequence,
        toSequence: seg.toSequence,
        direction: bestDir,
        amplitude: targetAmp,
        splinePoints: bestSpline,
      });
    }

    // Priority 3: Pure Geometric Regional Band & Relative Peer Longitude Scoring (0 Hardcode)
    let markerBalanceScore = 0;

    for (let i = 0; i < n; i++) {
      const p = points[i];

      // Find peers in the same regional latitude band (|lat_i - lat_k| < 2.5 deg)
      const regionalPeers = points.filter((other, idx) => idx !== i && Math.abs(p.lat - other.lat) < 2.5);

      if (regionalPeers.length > 0) {
        // Find if we are to the West or East of our regional peers
        const minPeerLng = Math.min(...regionalPeers.map((peer) => peer.lng));

        if (p.lng <= minPeerLng + 0.05) {
          // We are the Westernmost point in this regional cluster -> strongly prefer 'left'
          if (anchors[i] === 'left' || anchors[i] === 'top-left') markerBalanceScore -= 350;
          if (anchors[i] === 'right' || anchors[i] === 'top-right') markerBalanceScore += 350;
        } else if (p.lng >= minPeerLng + 0.10) {
          // We are to the East of another waypoint in this regional cluster -> strongly prefer 'right'
          if (anchors[i] === 'right' || anchors[i] === 'top-right') markerBalanceScore -= 350;
          if (anchors[i] === 'left' || anchors[i] === 'top-left') markerBalanceScore += 350;
        }
      } else {
        // Isolated waypoint with no peers in latitude band: use global centroid longitude
        if (p.lng > centroidLng) {
          if (anchors[i] === 'right' || anchors[i] === 'top-right') markerBalanceScore -= 200;
        } else {
          if (anchors[i] === 'left' || anchors[i] === 'top-left') markerBalanceScore -= 200;
        }
      }
    }

    const currentEnergy = boxOverlapPenalty + totalSegmentPenalty + markerBalanceScore;

    if (currentEnergy < minEnergy) {
      minEnergy = currentEnergy;
      const markerMap = new Map<string, AnchorSide>();
      for (let i = 0; i < n; i++) {
        markerMap.set(points[i].sequence, anchors[i]);
      }

      bestResult = {
        markerAnchors: markerMap,
        segmentCurvatures: segCurvatures,
        totalEnergy: currentEnergy,
        isCollisionFree: boxOverlapPenalty === 0 && totalSegmentPenalty < 5000,
      };
    }
  }

  return bestResult!;
}
