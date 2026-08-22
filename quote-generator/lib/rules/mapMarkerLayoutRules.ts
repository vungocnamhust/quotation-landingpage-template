/**
 * Pure Domain Reconciler for Map Destination Marker Collision Detection & Layout
 *
 * Implements deterministic collision detection, cluster grouping, and multi-directional
 * anchor slot allocation (top-center, top-left, top-right, left, right, top-elevated, bottom-*)
 * with leader lines to prevent overlapping labels in dense geographic regions.
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
  /** Width threshold for collision detection in pixels. Default: 140 */
  collisionRadiusX?: number;
  /** Height threshold for collision detection in pixels. Default: 52 */
  collisionRadiusY?: number;
  /** Container viewport width for boundary clamping. Default: 794 */
  containerWidth?: number;
  /** Container viewport height for boundary clamping. Default: 1123 */
  containerHeight?: number;
  /** Padding from edge to avoid cut-off. Default: 35 */
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
}

const DEFAULT_OPTIONS: Required<CollisionLayoutOptions> = {
  collisionRadiusX: 140,
  collisionRadiusY: 52,
  containerWidth: 794,
  containerHeight: 1123,
  edgePadding: 35,
};

/**
 * Calculates leader line stem offsets for each anchor direction.
 */
export function getStemOffsetForAnchor(anchor: MarkerAnchorDirection): { x: number; y: number; needleLength: number } {
  switch (anchor) {
    case 'top-center':
      return { x: 0, y: -10, needleLength: 10 };
    case 'top-elevated':
      return { x: 0, y: -34, needleLength: 34 };
    case 'top-left':
      return { x: -16, y: -14, needleLength: 21 };
    case 'top-right':
      return { x: 16, y: -14, needleLength: 21 };
    case 'left':
      return { x: -18, y: 0, needleLength: 18 };
    case 'right':
      return { x: 18, y: 0, needleLength: 18 };
    case 'bottom-left':
      return { x: -16, y: 14, needleLength: 21 };
    case 'bottom-right':
      return { x: 16, y: 14, needleLength: 21 };
    case 'bottom-center':
      return { x: 0, y: 10, needleLength: 10 };
    default:
      return { x: 0, y: -10, needleLength: 10 };
  }
}

/**
 * Checks if an anchor direction causes the marker capsule to overflow container bounds.
 */
export function adjustAnchorForBounds(
  point: MarkerPointInput,
  anchor: MarkerAnchorDirection,
  options: Required<CollisionLayoutOptions>
): MarkerAnchorDirection {
  const { containerWidth, containerHeight, edgePadding } = options;
  const isNearTop = point.y < edgePadding + 50;
  const isNearBottom = point.y > containerHeight - edgePadding - 50;
  const isNearLeft = point.x < edgePadding + 80;
  const isNearRight = point.x > containerWidth - edgePadding - 80;

  if (isNearTop) {
    if (anchor === 'top-center' || anchor === 'top-elevated') {
      return isNearLeft ? 'bottom-right' : isNearRight ? 'bottom-left' : 'bottom-center';
    }
    if (anchor === 'top-left') return 'bottom-left';
    if (anchor === 'top-right') return 'bottom-right';
  }

  if (isNearBottom) {
    if (anchor === 'bottom-center') return 'top-center';
    if (anchor === 'bottom-left') return 'top-left';
    if (anchor === 'bottom-right') return 'top-right';
  }

  if (isNearLeft) {
    if (anchor === 'top-left' || anchor === 'left') return 'top-right';
    if (anchor === 'bottom-left') return 'bottom-right';
  }

  if (isNearRight) {
    if (anchor === 'top-right' || anchor === 'right') return 'top-left';
    if (anchor === 'bottom-right') return 'bottom-left';
  }

  return anchor;
}

/**
 * Pure Reconciler: Resolves marker placement and assigns optimal non-overlapping
 * anchor directions to all markers based on projected 2D coordinates.
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

  if (visiblePoints.length === 0) {
    return results;
  }

  // 1. Build Adjacency Graph of Colliding Points
  const n = visiblePoints.length;
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

  // 2. Find Connected Components (Collision Clusters)
  const visited = new Array<boolean>(n).fill(false);
  const clusters: number[][] = [];

  for (let i = 0; i < n; i++) {
    if (!visited[i]) {
      const cluster: number[] = [];
      const queue: number[] = [i];
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
      clusters.push(cluster);
    }
  }

  // 3. Resolve Placements per Cluster
  for (const clusterIndices of clusters) {
    const clusterSize = clusterIndices.length;

    // Single isolated marker
    if (clusterSize === 1) {
      const p = visiblePoints[clusterIndices[0]];
      const anchor = adjustAnchorForBounds(p, 'top-center', options);
      const stem = getStemOffsetForAnchor(anchor);

      results.set(p.sequence, {
        sequence: p.sequence,
        anchorDirection: anchor,
        stemOffset: { x: stem.x, y: stem.y },
        needleLength: stem.needleLength,
        isClustered: false,
        clusterSize: 1,
      });
      continue;
    }

    // Cluster of 2 markers
    if (clusterSize === 2) {
      const pA = visiblePoints[clusterIndices[0]];
      const pB = visiblePoints[clusterIndices[1]];

      let anchorA: MarkerAnchorDirection;
      let anchorB: MarkerAnchorDirection;

      if (Math.abs(pA.x - pB.x) >= 20) {
        // Horizontal separation: leftmost gets top-left, rightmost gets top-right
        if (pA.x <= pB.x) {
          anchorA = 'top-left';
          anchorB = 'top-right';
        } else {
          anchorA = 'top-right';
          anchorB = 'top-left';
        }
      } else {
        // Vertical stack: topmost gets top-elevated, bottom gets top-center
        if (pA.y <= pB.y) {
          anchorA = 'top-elevated';
          anchorB = 'top-center';
        } else {
          anchorA = 'top-center';
          anchorB = 'top-elevated';
        }
      }

      anchorA = adjustAnchorForBounds(pA, anchorA, options);
      anchorB = adjustAnchorForBounds(pB, anchorB, options);

      const stemA = getStemOffsetForAnchor(anchorA);
      const stemB = getStemOffsetForAnchor(anchorB);

      results.set(pA.sequence, {
        sequence: pA.sequence,
        anchorDirection: anchorA,
        stemOffset: { x: stemA.x, y: stemA.y },
        needleLength: stemA.needleLength,
        isClustered: true,
        clusterSize: 2,
      });

      results.set(pB.sequence, {
        sequence: pB.sequence,
        anchorDirection: anchorB,
        stemOffset: { x: stemB.x, y: stemB.y },
        needleLength: stemB.needleLength,
        isClustered: true,
        clusterSize: 2,
      });
      continue;
    }

    // Cluster of 3+ markers (e.g. Hanoi, Ninh Binh, Ha Long Bay)
    // Sort cluster members by x-coordinate ascending
    const sortedIndices = [...clusterIndices].sort((a, b) => {
      const ptA = visiblePoints[a];
      const ptB = visiblePoints[b];
      return ptA.x - ptB.x;
    });

    // Anchor distribution template for multi-point clusters
    const multiAnchorSlots: MarkerAnchorDirection[] = [
      'top-left',
      'top-elevated',
      'top-right',
      'left',
      'right',
      'bottom-left',
      'bottom-right',
      'bottom-center',
    ];

    sortedIndices.forEach((pointIdx, rank) => {
      const p = visiblePoints[pointIdx];
      let assignedAnchor = multiAnchorSlots[rank % multiAnchorSlots.length];
      assignedAnchor = adjustAnchorForBounds(p, assignedAnchor, options);
      const stem = getStemOffsetForAnchor(assignedAnchor);

      results.set(p.sequence, {
        sequence: p.sequence,
        anchorDirection: assignedAnchor,
        stemOffset: { x: stem.x, y: stem.y },
        needleLength: stem.needleLength,
        isClustered: true,
        clusterSize,
      });
    });
  }

  return results;
}
