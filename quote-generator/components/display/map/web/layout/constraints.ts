import type { WebRouteMapLayoutInput } from './contracts.ts';
import type { MarkerCandidate, RouteCandidate } from './candidates.ts';
import { polylineIntersectsRect, polylinesIntersect, rectsOverlap } from './geometry.ts';

export interface WebRouteMapOptimizationProblem {
  groups: Array<{ id: string; candidateIds: string[] }>;
  costs: Map<string, { clearance: number; comfort: number }>;
  conflicts: Array<[string, string]>;
  candidateCount: number;
}

function leaderIntersectsLeader(a: MarkerCandidate, b: MarkerCandidate): boolean {
  return polylinesIntersect(a.leader, b.leader);
}

export function buildOptimizationProblem(
  input: WebRouteMapLayoutInput,
  markerCandidates: Map<string, MarkerCandidate[]>,
  routeCandidates: Map<string, RouteCandidate[]>
): WebRouteMapOptimizationProblem {
  const groups: Array<{ id: string; candidateIds: string[] }> = [];
  const costs = new Map<string, { clearance: number; comfort: number }>();
  const conflicts: Array<[string, string]> = [];
  const flatMarkers = [...markerCandidates.values()].flat();
  const flatRoutes = [...routeCandidates.values()].flat();
  const clearance = input.minimumClearance ?? 12;

  for (const [sequence, candidates] of markerCandidates) {
    groups.push({ id: `marker:${sequence}`, candidateIds: candidates.map((candidate) => candidate.id) });
    for (const candidate of candidates) {
      costs.set(candidate.id, { clearance: candidate.clearanceScore, comfort: candidate.cost });
    }
  }
  for (const [routeId, candidates] of routeCandidates) {
    groups.push({ id: `route:${routeId}`, candidateIds: candidates.map((candidate) => candidate.id) });
    for (const candidate of candidates) {
      costs.set(candidate.id, { clearance: 0, comfort: candidate.cost });
    }
  }

  for (let index = 0; index < flatMarkers.length; index += 1) {
    for (let otherIndex = index + 1; otherIndex < flatMarkers.length; otherIndex += 1) {
      const a = flatMarkers[index];
      const b = flatMarkers[otherIndex];
      if (a.sequence === b.sequence) continue;
      if (
        rectsOverlap(a.rect, b.rect, clearance) ||
        leaderIntersectsLeader(a, b) ||
        polylineIntersectsRect(a.leader, b.rect, clearance / 2) ||
        polylineIntersectsRect(b.leader, a.rect, clearance / 2)
      ) {
        conflicts.push([a.id, b.id]);
      }
    }
  }

  for (const route of flatRoutes) {
    for (const marker of flatMarkers) {
      const isEndpoint = marker.sequence === route.route.fromSequence || marker.sequence === route.route.toSequence;
      if (!isEndpoint && polylineIntersectsRect(route.points, marker.rect, clearance / 2)) {
        conflicts.push([route.id, marker.id]);
      }
      if (!isEndpoint && polylinesIntersect(route.points, marker.leader)) {
        conflicts.push([route.id, marker.id]);
      }
    }
  }

  for (let index = 0; index < flatRoutes.length; index += 1) {
    for (let otherIndex = index + 1; otherIndex < flatRoutes.length; otherIndex += 1) {
      const a = flatRoutes[index];
      const b = flatRoutes[otherIndex];
      if (a.route.id === b.route.id) continue;
      const sharesStop =
        a.route.fromSequence === b.route.fromSequence ||
        a.route.fromSequence === b.route.toSequence ||
        a.route.toSequence === b.route.fromSequence ||
        a.route.toSequence === b.route.toSequence;
      const isReverseLeg =
        a.route.fromSequence === b.route.toSequence && a.route.toSequence === b.route.fromSequence;
      if ((isReverseLeg && a.curvature === b.curvature) || (!sharesStop && polylinesIntersect(a.points, b.points))) {
        conflicts.push([a.id, b.id]);
      }
    }
  }

  return {
    groups,
    costs,
    conflicts,
    candidateCount: flatMarkers.length + flatRoutes.length,
  };
}
