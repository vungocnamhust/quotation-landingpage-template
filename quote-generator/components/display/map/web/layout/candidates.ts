import type {
  MapPoint,
  MapRect,
  MarkerAnchorDirection,
  WebRouteMapLayoutInput,
  WebRouteMapMarkerInput,
  WebRouteMapRouteInput,
} from './contracts.ts';
import { distance, pointToRectEdge, polylineLength, quadraticBezier, rectsOverlap } from './geometry.ts';

export interface MarkerCandidate {
  id: string;
  sequence: string;
  rect: MapRect;
  direction: MarkerAnchorDirection;
  leader: MapPoint[];
  clearanceScore: number;
  cost: number;
}

export interface RouteCandidate {
  id: string;
  route: WebRouteMapRouteInput;
  points: MapPoint[];
  curvature: 'left' | 'right' | 'loop';
  cost: number;
}

const DIRECTIONS: ReadonlyArray<{ direction: MarkerAnchorDirection; x: number; y: number }> = [
  { direction: 'left', x: -1, y: 0 },
  { direction: 'right', x: 1, y: 0 },
  { direction: 'top', x: 0, y: -1 },
  { direction: 'bottom', x: 0, y: 1 },
  { direction: 'top-left', x: -0.72, y: -0.72 },
  { direction: 'top-right', x: 0.72, y: -0.72 },
  { direction: 'bottom-left', x: -0.72, y: 0.72 },
  { direction: 'bottom-right', x: 0.72, y: 0.72 },
];

function leaderLengthsFor(maximumLeaderLength: number): readonly number[] {
  return maximumLeaderLength <= 22 ? [6, 12, 22] : [8, 16, 28];
}

function isWithinViewport(rect: MapRect, input: WebRouteMapLayoutInput, clearance: number): boolean {
  return (
    rect.x >= clearance &&
    rect.y >= clearance &&
    rect.x + rect.width <= input.viewport.width - clearance &&
    rect.y + rect.height <= input.viewport.height - clearance
  );
}

function anchorRect(marker: WebRouteMapMarkerInput, direction: { x: number; y: number }, leaderLength: number): MapRect {
  const center = {
    x: marker.point.x + direction.x * (leaderLength + marker.labelSize.width / 2),
    y: marker.point.y + direction.y * (leaderLength + marker.labelSize.height / 2),
  };
  return {
    x: center.x - marker.labelSize.width / 2,
    y: center.y - marker.labelSize.height / 2,
    width: marker.labelSize.width,
    height: marker.labelSize.height,
  };
}

function outwardScore(marker: WebRouteMapMarkerInput, direction: { x: number; y: number }, markers: WebRouteMapMarkerInput[]): number {
  const center = markers.reduce(
    (sum, item) => ({ x: sum.x + item.point.x, y: sum.y + item.point.y }),
    { x: 0, y: 0 }
  );
  center.x /= markers.length || 1;
  center.y /= markers.length || 1;
  const fromCentroid = { x: marker.point.x - center.x, y: marker.point.y - center.y };
  return -(fromCentroid.x * direction.x + fromCentroid.y * direction.y);
}

function rectClearance(
  marker: WebRouteMapMarkerInput,
  rect: MapRect,
  input: WebRouteMapLayoutInput
): number {
  const viewportClearance = Math.min(
    rect.x,
    rect.y,
    input.viewport.width - rect.x - rect.width,
    input.viewport.height - rect.y - rect.height
  );
  const pinClearance = input.markers
    .filter((other) => other.sequence !== marker.sequence)
    .map((other) => distance(other.point, pointToRectEdge(other.point, rect)));
  const reservedClearance = input.reservedZones.map((zone) => {
    const dx = Math.max(zone.x - rect.x - rect.width, rect.x - zone.x - zone.width, 0);
    const dy = Math.max(zone.y - rect.y - rect.height, rect.y - zone.y - zone.height, 0);
    return Math.hypot(dx, dy);
  });
  return Math.min(viewportClearance, ...pinClearance, ...reservedClearance);
}

function curvedLeader(
  marker: WebRouteMapMarkerInput,
  attachment: MapPoint,
  direction: { x: number; y: number }
): MapPoint[] {
  const dx = attachment.x - marker.point.x;
  const dy = attachment.y - marker.point.y;
  const length = Math.hypot(dx, dy);
  if (length < 0.001) return [marker.point, attachment];
  const normal = { x: -dy / length, y: dx / length };
  const orientation = direction.x * dy - direction.y * dx >= 0 ? 1 : -1;
  const bend = Math.min(10, length * 0.18) * orientation;
  return quadraticBezier(
    marker.point,
    { x: (marker.point.x + attachment.x) / 2 + normal.x * bend, y: (marker.point.y + attachment.y) / 2 + normal.y * bend },
    attachment,
    8
  );
}

export function buildMarkerCandidates(input: WebRouteMapLayoutInput): Map<string, MarkerCandidate[]> {
  const clearance = input.minimumClearance ?? 12;
  const maximumLeaderLength = input.maxLeaderLength ?? 28;
  const candidates = new Map<string, MarkerCandidate[]>();

  for (const marker of input.markers) {
    const markerCandidates: MarkerCandidate[] = [];
    for (const direction of DIRECTIONS) {
      for (const leaderLength of leaderLengthsFor(maximumLeaderLength)) {
        if (leaderLength > maximumLeaderLength) continue;
        const rect = anchorRect(marker, direction, leaderLength);
        if (!isWithinViewport(rect, input, clearance)) continue;
        if (input.reservedZones.some((zone) => rectsOverlap(rect, zone, clearance))) continue;
        const attachment = pointToRectEdge(marker.point, rect);
        const leader = curvedLeader(marker, attachment, direction);
        const actualLength = polylineLength(leader);
        if (actualLength > maximumLeaderLength) continue;
        markerCandidates.push({
          id: `marker:${marker.sequence}:${direction.direction}:${leaderLength}`,
          sequence: marker.sequence,
          rect,
          direction: direction.direction,
          leader,
          clearanceScore: rectClearance(marker, rect, input),
          cost: actualLength + outwardScore(marker, direction, input.markers) * 0.12,
        });
      }
    }
    candidates.set(marker.sequence, markerCandidates);
  }

  return candidates;
}

function isReturnRoute(route: WebRouteMapRouteInput, routes: WebRouteMapRouteInput[]): boolean {
  return routes.some(
    (other) =>
      other.id !== route.id &&
      other.fromSequence === route.toSequence &&
      other.toSequence === route.fromSequence
  );
}

export function buildRouteCandidates(input: WebRouteMapLayoutInput): Map<string, RouteCandidate[]> {
  const markerBySequence = new Map(input.markers.map((marker) => [marker.sequence, marker]));
  const candidates = new Map<string, RouteCandidate[]>();

  for (const route of input.routes) {
    const from = markerBySequence.get(route.fromSequence)?.point;
    const to = markerBySequence.get(route.toSequence)?.point;
    if (!from || !to) {
      candidates.set(route.id, []);
      continue;
    }
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const chord = Math.hypot(dx, dy);
    if (chord < 1) {
      const angle = route.order * 1.7;
      const radius = 9;
      const start = { x: from.x + Math.cos(angle) * radius, y: from.y + Math.sin(angle) * radius };
      const end = { x: to.x + Math.cos(angle + Math.PI * 0.72) * radius, y: to.y + Math.sin(angle + Math.PI * 0.72) * radius };
      const control = { x: from.x + Math.cos(angle + Math.PI * 0.36) * radius * 2.3, y: from.y + Math.sin(angle + Math.PI * 0.36) * radius * 2.3 };
      const points = quadraticBezier(start, control, end);
      candidates.set(route.id, [{ id: `route:${route.id}:loop`, route, points, curvature: 'loop', cost: polylineLength(points) }]);
      continue;
    }
    const normal = { x: -dy / chord, y: dx / chord };
    const isReturn = isReturnRoute(route, input.routes);
    const offsets = isReturn
      ? [-0.22, -0.12, 0.12, 0.22]
      : chord >= 100
        ? [-0.08, 0.08, -0.16, 0.16, -0.28, 0.28]
        : [-0.06, 0.06, -0.13, 0.13];
    const routeCandidates = offsets.map((ratio) => {
      const offset = chord * ratio;
      const control = {
        x: (from.x + to.x) / 2 + normal.x * offset,
        y: (from.y + to.y) / 2 + normal.y * offset,
      };
      const curvature = ratio < 0 ? 'left' : 'right';
      const points = quadraticBezier(from, control, to);
      return {
        id: `route:${route.id}:${curvature}:${Math.abs(ratio)}`,
        route,
        points,
        curvature,
        cost: polylineLength(points) + Math.abs(offset) * 0.55,
      } satisfies RouteCandidate;
    });
    candidates.set(route.id, routeCandidates);
  }

  return candidates;
}
