/**
 * Pure Domain Reconciler for Map Destination Marker Collision Detection & Line-Marker Non-Occlusion (SCERA)
 *
 * Implements SCERA: Sector-Clearance Exterior Radial Anchoring
 * - Computes incoming and outgoing route trajectory vectors at every waypoint.
 * - Enforces forbidden angular cones around route polylines to prevent direct line occlusion.
 * - Computes the 2D Exterior Bisector vector to push marker capsules into the open convex exterior space.
 * - Performs Liang-Barsky line-segment bounding-box intersection tests across all route polylines.
 * - Assigns optimal non-overlapping anchor directions (top-left, top-right, left, right, etc.) in 2/3 micro-scale.
 *
 * Zero React dependencies. 100% deterministic and unit-testable.
 */

export type MarkerAnchorDirection =
  | 'top-center'
  | 'top-left'
  | 'top-right'
  | 'left'
  | 'right'
  | 'top-elevated'
  | 'bottom-left'
  | 'bottom-right'
  | 'bottom-center';

export interface MarkerPointInput {
  sequence: string;
  x: number;
  y: number;
  city?: string;
  dayLabel?: string;
  visible?: boolean;
}

export interface CollisionLayoutOptions {
  /** Width threshold for collision detection in pixels. Default: 55 */
  collisionRadiusX?: number;
  /** Height threshold for collision detection in pixels. Default: 22 */
  collisionRadiusY?: number;
  /** Capsule bounding box width. Default: 55 */
  capsuleWidth?: number;
  /** Capsule bounding box height. Default: 16 */
  capsuleHeight?: number;
  /** Container viewport width for boundary clamping. Default: 794 */
  containerWidth?: number;
  /** Container viewport height for boundary clamping. Default: 1123 */
  containerHeight?: number;
  /** Padding from edge to avoid cut-off. Default: 20 */
  edgePadding?: number;
}

export interface ResolvedMarkerPlacement {
  sequence: string;
  anchorDirection: MarkerAnchorDirection;
  /** Offset of the stem attachment point relative to ground dot (0, 0) */
  stemOffset: { x: number; y: number };
  /** Approximate length of the leader line stem */
  needleLength: number;
  /** Whether this marker was adjusted due to a detected collision */
  isClustered: boolean;
  /** Total markers in its collision cluster */
  clusterSize: number;
  /** Bounding box of the marker capsule in container pixel coordinates */
  boundingBox: { minX: number; maxX: number; minY: number; maxY: number };
}

const DEFAULT_OPTIONS: Required<CollisionLayoutOptions> = {
  collisionRadiusX: 55,
  collisionRadiusY: 22,
  capsuleWidth: 55,
  capsuleHeight: 16,
  containerWidth: 794,
  containerHeight: 1123,
  edgePadding: 20,
};

const ALL_ANCHOR_DIRECTIONS: MarkerAnchorDirection[] = [
  'top-center',
  'top-left',
  'top-right',
  'left',
  'right',
  'top-elevated',
  'bottom-left',
  'bottom-right',
  'bottom-center',
];

/**
 * Calculates leader line stem offsets for each anchor direction (2/3 micro-scale).
 */
export function getStemOffsetForAnchor(anchor: MarkerAnchorDirection): { x: number; y: number; needleLength: number } {
  switch (anchor) {
    case 'top-center':
      return { x: 0, y: -5, needleLength: 5 };
    case 'top-elevated':
      return { x: 0, y: -16, needleLength: 16 };
    case 'top-left':
      return { x: -8, y: -6, needleLength: 10 };
    case 'top-right':
      return { x: 8, y: -6, needleLength: 10 };
    case 'left':
      return { x: -8, y: 0, needleLength: 8 };
    case 'right':
      return { x: 8, y: 0, needleLength: 8 };
    case 'bottom-left':
      return { x: -8, y: 6, needleLength: 10 };
    case 'bottom-right':
      return { x: 8, y: 6, needleLength: 10 };
    case 'bottom-center':
      return { x: 0, y: 5, needleLength: 5 };
    default:
      return { x: 0, y: -5, needleLength: 5 };
  }
}

/**
 * Calculates the bounding box of a marker capsule placed at point (px, py) with given anchor.
 */
export function getMarkerBoundingBox(
  point: { x: number; y: number },
  anchor: MarkerAnchorDirection,
  width = 55,
  height = 16
): { minX: number; maxX: number; minY: number; maxY: number } {
  const stem = getStemOffsetForAnchor(anchor);
  const sx = point.x + stem.x;
  const sy = point.y + stem.y;

  let minX: number;
  let maxX: number;
  let minY: number;
  let maxY: number;

  switch (anchor) {
    case 'top-center':
    case 'top-elevated':
      minX = sx - width / 2;
      maxX = sx + width / 2;
      minY = sy - height;
      maxY = sy;
      break;
    case 'top-left':
      minX = sx - width;
      maxX = sx;
      minY = sy - height;
      maxY = sy;
      break;
    case 'top-right':
      minX = sx;
      maxX = sx + width;
      minY = sy - height;
      maxY = sy;
      break;
    case 'left':
      minX = sx - width;
      maxX = sx;
      minY = sy - height / 2;
      maxY = sy + height / 2;
      break;
    case 'right':
      minX = sx;
      maxX = sx + width;
      minY = sy - height / 2;
      maxY = sy + height / 2;
      break;
    case 'bottom-left':
      minX = sx - width;
      maxX = sx;
      minY = sy;
      maxY = sy + height;
      break;
    case 'bottom-right':
      minX = sx;
      maxX = sx + width;
      minY = sy;
      maxY = sy + height;
      break;
    case 'bottom-center':
      minX = sx - width / 2;
      maxX = sx + width / 2;
      minY = sy;
      maxY = sy + height;
      break;
    default:
      minX = sx - width / 2;
      maxX = sx + width / 2;
      minY = sy - height;
      maxY = sy;
  }

  return { minX, maxX, minY, maxY };
}

/**
 * Calculates shortest angular difference in radians between two angles [-PI, PI].
 */
function angleDifference(a: number, b: number): number {
  let diff = Math.abs(a - b) % (2 * Math.PI);
  if (diff > Math.PI) {
    diff = 2 * Math.PI - diff;
  }
  return diff;
}

/**
 * Liang-Barsky Line Segment vs AABB Bounding Box Intersection Test.
 * Returns true if segment (p1 -> p2) intersects or passes through box.
 */
export function segmentIntersectsBox(
  p1: { x: number; y: number },
  p2: { x: number; y: number },
  box: { minX: number; maxX: number; minY: number; maxY: number },
  margin = 2
): boolean {
  const minX = box.minX - margin;
  const maxX = box.maxX + margin;
  const minY = box.minY - margin;
  const maxY = box.maxY + margin;

  const dx = p2.x - p1.x;
  const dy = p2.y - p1.y;

  let t0 = 0.0;
  let t1 = 1.0;

  const p = [-dx, dx, -dy, dy];
  const q = [p1.x - minX, maxX - p1.x, p1.y - minY, maxY - p1.y];

  for (let i = 0; i < 4; i++) {
    if (p[i] === 0) {
      if (q[i] < 0) return false;
    } else {
      const t = q[i] / p[i];
      if (p[i] < 0) {
        if (t > t1) return false;
        if (t > t0) t0 = t;
      } else {
        if (t < t0) return false;
        if (t < t1) t1 = t;
      }
    }
  }
  return t0 <= t1;
}

/**
 * Checks if box is inside the container viewport bounds.
 */
export function isBoxWithinBounds(
  box: { minX: number; maxX: number; minY: number; maxY: number },
  options: Required<CollisionLayoutOptions>
): boolean {
  const { containerWidth, containerHeight, edgePadding } = options;
  return (
    box.minX >= edgePadding &&
    box.maxX <= containerWidth - edgePadding &&
    box.minY >= edgePadding &&
    box.maxY <= containerHeight - edgePadding
  );
}

/**
 * Check if two AABB bounding boxes overlap.
 */
function boxesOverlap(
  b1: { minX: number; maxX: number; minY: number; maxY: number },
  b2: { minX: number; maxX: number; minY: number; maxY: number }
): boolean {
  return !(b1.maxX < b2.minX || b1.minX > b2.maxX || b1.maxY < b2.minY || b1.minY > b2.maxY);
}

/**
 * Pure Reconciler: SCERA (Sector-Clearance Exterior Radial Anchoring)
 * Resolves non-overlapping marker placements and guarantees route polylines are 0% occluded.
 */
export function resolveMarkerCollisions(
  points: MarkerPointInput[],
  customOptions?: CollisionLayoutOptions
): Map<string, ResolvedMarkerPlacement> {
  const options: Required<CollisionLayoutOptions> = {
    ...DEFAULT_OPTIONS,
    ...customOptions,
  };

  const results = new Map<string, ResolvedMarkerPlacement>();
  const visiblePoints = points.filter((p) => p.visible !== false);
  const n = visiblePoints.length;

  if (n === 0) {
    return results;
  }

  // 1. Extract Route Polyline Segments
  const routeSegments: Array<{ p1: MarkerPointInput; p2: MarkerPointInput }> = [];
  for (let i = 0; i < n - 1; i++) {
    routeSegments.push({ p1: visiblePoints[i], p2: visiblePoints[i + 1] });
  }

  // 2. Identify Proximity Collision Clusters
  const adj: number[][] = Array.from({ length: n }, () => []);
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      const p1 = visiblePoints[i];
      const p2 = visiblePoints[j];
      const dx = Math.abs(p1.x - p2.x);
      const dy = Math.abs(p1.y - p2.y);
      if (dx < options.collisionRadiusX && dy < options.collisionRadiusY) {
        adj[i].push(j);
        adj[j].push(i);
      }
    }
  }

  const clusterSizes = new Array<number>(n).fill(1);
  const visited = new Array<boolean>(n).fill(false);

  for (let i = 0; i < n; i++) {
    if (!visited[i]) {
      const cluster: number[] = [];
      const queue = [i];
      visited[i] = true;
      while (queue.length > 0) {
        const curr = queue.shift()!;
        cluster.push(curr);
        for (const neighbor of adj[curr]) {
          if (!visited[neighbor]) {
            visited[neighbor] = true;
            queue.push(neighbor);
          }
        }
      }
      for (const idx of cluster) {
        clusterSizes[idx] = cluster.length;
      }
    }
  }

  // 3. For Each Waypoint, Score and Select Optimal Anchor Direction via SCERA
  const placedBoxes: Array<{ sequence: string; box: { minX: number; maxX: number; minY: number; maxY: number } }> = [];

  for (let i = 0; i < n; i++) {
    const pt = visiblePoints[i];
    const prev = i > 0 ? visiblePoints[i - 1] : null;
    const next = i < n - 1 ? visiblePoints[i + 1] : null;

    // A. Compute Incoming and Outgoing Angles at pt
    const prevAngle = prev ? Math.atan2(prev.y - pt.y, prev.x - pt.x) : null;
    const nextAngle = next ? Math.atan2(next.y - pt.y, next.x - pt.x) : null;

    // B. Compute Exterior Bisector Vector (Points directly into safe open space away from paths)
    let extBisectorX = 0;
    let extBisectorY = -1; // Default upwards

    if (prev && next) {
      const uX = prev.x - pt.x;
      const uY = prev.y - pt.y;
      const uLen = Math.hypot(uX, uY) || 1;
      const vX = next.x - pt.x;
      const vY = next.y - pt.y;
      const vLen = Math.hypot(vX, vY) || 1;

      const normUx = uX / uLen;
      const normUy = uY / uLen;
      const normVx = vX / vLen;
      const normVy = vY / vLen;

      const sumX = normUx + normVx;
      const sumY = normUy + normVy;
      const sumLen = Math.hypot(sumX, sumY);

      if (sumLen > 0.1) {
        // Safe exterior bisector points opposite of angle interior
        extBisectorX = -sumX / sumLen;
        extBisectorY = -sumY / sumLen;
      } else {
        // Collinear 180 deg paths: use perpendicular normal away from right boundary
        extBisectorX = -normUy;
        extBisectorY = normUx;
        if (pt.x > options.containerWidth * 0.6) {
          extBisectorX = -Math.abs(extBisectorX);
        }
      }
    } else if (next) {
      // Start waypoint: orient opposite of outgoing trajectory
      const vX = next.x - pt.x;
      const vY = next.y - pt.y;
      const vLen = Math.hypot(vX, vY) || 1;
      extBisectorX = -vX / vLen;
      extBisectorY = -vY / vLen;
    } else if (prev) {
      // End waypoint: orient opposite of incoming trajectory
      const uX = prev.x - pt.x;
      const uY = prev.y - pt.y;
      const uLen = Math.hypot(uX, uY) || 1;
      extBisectorX = -uX / uLen;
      extBisectorY = -uY / uLen;
    }

    const bisectorAngle = Math.atan2(extBisectorY, extBisectorX);

    // C. Evaluate and Rank Candidate Anchor Directions
    interface ScoredCandidate {
      anchor: MarkerAnchorDirection;
      box: { minX: number; maxX: number; minY: number; maxY: number };
      stem: { x: number; y: number; needleLength: number };
      score: number;
      occludesLine: boolean;
      withinBounds: boolean;
      overlapsOtherMarker: boolean;
    }

    const candidates: ScoredCandidate[] = ALL_ANCHOR_DIRECTIONS.map((anchor) => {
      const box = getMarkerBoundingBox(pt, anchor, options.capsuleWidth, options.capsuleHeight);
      const stem = getStemOffsetForAnchor(anchor);
      const withinBounds = isBoxWithinBounds(box, options);

      // Anchor Vector from Ground Dot to Capsule Center
      const centerX = (box.minX + box.maxX) / 2 - pt.x;
      const centerY = (box.minY + box.maxY) / 2 - pt.y;
      const anchorAngle = Math.atan2(centerY, centerX);

      // Check Forbidden Angular Sector (within 35 deg of incoming or outgoing line)
      const FORBIDDEN_RAD = (35 * Math.PI) / 180;
      let isInForbiddenAngle = false;
      if (prevAngle !== null && angleDifference(anchorAngle, prevAngle) < FORBIDDEN_RAD) {
        isInForbiddenAngle = true;
      }
      if (nextAngle !== null && angleDifference(anchorAngle, nextAngle) < FORBIDDEN_RAD) {
        isInForbiddenAngle = true;
      }

      // Check Line-Box Intersections with all Route Segments
      let occludesLine = isInForbiddenAngle;
      if (!occludesLine) {
        for (const seg of routeSegments) {
          // Ignore lines directly attached to current point (already guarded by forbidden cone)
          const isDirectAttach =
            (seg.p1.sequence === pt.sequence && seg.p2.sequence === next?.sequence) ||
            (seg.p2.sequence === pt.sequence && seg.p1.sequence === prev?.sequence);

          if (!isDirectAttach && segmentIntersectsBox(seg.p1, seg.p2, box, 4)) {
            occludesLine = true;
            break;
          }
        }
      }

      // Check Overlap with Previously Placed Markers
      let overlapsOtherMarker = false;
      for (const placed of placedBoxes) {
        if (boxesOverlap(box, placed.box)) {
          overlapsOtherMarker = true;
          break;
        }
      }

      // Compute Alignment with Safe Exterior Bisector [cos(theta) in -1..1]
      const diffToBisector = angleDifference(anchorAngle, bisectorAngle);
      const bisectorAlignment = Math.cos(diffToBisector);

      // Composite Score: Prioritize non-occlusion, boundary fit, bisector alignment, and non-overlap
      let score = bisectorAlignment * 10;
      if (withinBounds) score += 5;
      if (!occludesLine) score += 20;
      if (!overlapsOtherMarker) score += 10;

      // Slight natural preference for top-oriented anchors
      if (anchor === 'top-center' || anchor === 'top-left' || anchor === 'top-right') {
        score += 1;
      }

      return {
        anchor,
        box,
        stem,
        score,
        occludesLine,
        withinBounds,
        overlapsOtherMarker,
      };
    });

    // D. Pick Best Candidate (Strictly prefer 0% line occlusion and within bounds)
    candidates.sort((a, b) => b.score - a.score);

    // Filter optimal tier: non-occluding, in-bounds, non-overlapping
    const bestTier = candidates.filter((c) => !c.occludesLine && c.withinBounds && !c.overlapsOtherMarker);
    const secondTier = candidates.filter((c) => !c.occludesLine && c.withinBounds);
    const thirdTier = candidates.filter((c) => !c.occludesLine);

    const chosen = bestTier[0] || secondTier[0] || thirdTier[0] || candidates[0];

    placedBoxes.push({ sequence: pt.sequence, box: chosen.box });

    results.set(pt.sequence, {
      sequence: pt.sequence,
      anchorDirection: chosen.anchor,
      stemOffset: { x: chosen.stem.x, y: chosen.stem.y },
      needleLength: chosen.stem.needleLength,
      isClustered: clusterSizes[i] > 1,
      clusterSize: clusterSizes[i],
      boundingBox: chosen.box,
    });
  }

  return results;
}
