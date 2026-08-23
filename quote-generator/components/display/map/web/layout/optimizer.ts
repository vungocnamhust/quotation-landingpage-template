import type { LP, Options, Result } from 'glpk.js';
import type {
  WebRouteMapLayoutDiagnostics,
  WebRouteMapLayoutInput,
  WebRouteMapLayoutPlan,
  WebRouteMapMarkerInput,
  WebRouteMapRouteInput,
} from './contracts.ts';
import { buildMarkerCandidates, buildRouteCandidates, type MarkerCandidate, type RouteCandidate } from './candidates.ts';
import { buildOptimizationProblem } from './constraints.ts';
import { validateWebRouteMapLayout } from './validate.ts';

interface PreparedInput {
  input: WebRouteMapLayoutInput;
  membersBySequence: Map<string, string[]>;
}

export interface WebRouteMapMipSolver {
  readonly GLP_MIN: number;
  readonly GLP_MAX: number;
  readonly GLP_UP: number;
  readonly GLP_LO: number;
  readonly GLP_FX: number;
  readonly GLP_OPT: number;
  readonly GLP_FEAS: number;
  readonly GLP_MSG_OFF: number;
  solve(lp: LP, options?: number | Options): Promise<Result> | Result;
}

function clusterMarkersToCapacity(
  input: WebRouteMapLayoutInput,
  targetMarkerCount: number
): PreparedInput {
  if (input.markers.length <= targetMarkerCount) {
    return {
      input,
      membersBySequence: new Map(input.markers.map((marker) => [marker.sequence, marker.memberSequences ?? [marker.sequence]])),
    };
  }

  type Cluster = { markers: WebRouteMapMarkerInput[] };
  const clusters: Cluster[] = input.markers
    .slice()
    .sort((a, b) => a.order - b.order)
    .map((marker) => ({ markers: [marker] }));
  const centroid = (cluster: Cluster) => {
    const count = cluster.markers.length;
    return cluster.markers.reduce(
      (point, marker) => ({ x: point.x + marker.point.x / count, y: point.y + marker.point.y / count }),
      { x: 0, y: 0 }
    );
  };

  // Capacity clustering is separate from label placement. Once the map must
  // compress, this deterministic geographic reduction leaves the global MIP
  // responsible for every visible marker/route decision.
  while (clusters.length > targetMarkerCount) {
    let bestPair: [number, number] = [0, 1];
    let bestDistance = Number.POSITIVE_INFINITY;
    for (let left = 0; left < clusters.length; left += 1) {
      for (let right = left + 1; right < clusters.length; right += 1) {
        const containsActiveStop = [...clusters[left].markers, ...clusters[right].markers]
          .some((marker) => (marker.memberSequences ?? [marker.sequence]).includes(input.activeSequence ?? ''));
        if (containsActiveStop) continue;
        const a = centroid(clusters[left]);
        const b = centroid(clusters[right]);
        const candidateDistance = Math.hypot(a.x - b.x, a.y - b.y);
        if (candidateDistance < bestDistance) {
          bestDistance = candidateDistance;
          bestPair = [left, right];
        }
      }
    }
    if (!Number.isFinite(bestDistance)) break;
    const [left, right] = bestPair;
    clusters[left] = { markers: [...clusters[left].markers, ...clusters[right].markers] };
    clusters.splice(right, 1);
  }

  const representativeBySequence = new Map<string, string>();
  const membersBySequence = new Map<string, string[]>();
  const markers = clusters.map((cluster) => {
    const ordered = cluster.markers.slice().sort((a, b) => a.order - b.order);
    const representative = ordered[0];
    const point = centroid(cluster);
    const memberSequences = ordered.flatMap((marker) => marker.memberSequences ?? [marker.sequence]);
    for (const member of memberSequences) representativeBySequence.set(member, representative.sequence);
    membersBySequence.set(representative.sequence, memberSequences);
    return {
      ...representative,
      point,
      labelSize: {
        width: Math.max(...ordered.map((marker) => marker.labelSize.width)),
        height: Math.max(...ordered.map((marker) => marker.labelSize.height)),
      },
      memberSequences,
    } satisfies WebRouteMapMarkerInput;
  });

  const routes: WebRouteMapRouteInput[] = input.routes.flatMap((route) => {
    const fromSequence = representativeBySequence.get(route.fromSequence) ?? route.fromSequence;
    const toSequence = representativeBySequence.get(route.toSequence) ?? route.toSequence;
    return fromSequence === toSequence ? [] : [{ ...route, fromSequence, toSequence }];
  });

  return { input: { ...input, markers, routes }, membersBySequence };
}

function solvePreparedInput(
  prepared: PreparedInput,
  glpk: WebRouteMapMipSolver,
  startedAt: number
): Promise<WebRouteMapLayoutPlan> {
  return solvePreparedLayout(prepared.input, prepared.membersBySequence, glpk, startedAt);
}

function buildLp(
  glpk: WebRouteMapMipSolver,
  problem: ReturnType<typeof buildOptimizationProblem>,
  objective: 'clearance' | 'comfort',
  clearanceFloor?: number
) {
  const subjectTo = [
    ...problem.groups.map((group) => ({
      name: `choose:${group.id}`,
      vars: group.candidateIds.map((name) => ({ name, coef: 1 })),
      bnds: { type: glpk.GLP_FX, lb: 1, ub: 1 },
    })),
    ...problem.conflicts.map(([left, right], index) => ({
      name: `conflict:${index}`,
      vars: [{ name: left, coef: 1 }, { name: right, coef: 1 }],
      bnds: { type: glpk.GLP_UP, lb: 0, ub: 1 },
    })),
  ];
  if (typeof clearanceFloor === 'number') {
    subjectTo.push({
      name: 'clearance-floor',
      vars: [...problem.costs.entries()].map(([name, cost]) => ({ name, coef: cost.clearance })),
      bnds: { type: glpk.GLP_LO, lb: clearanceFloor, ub: 0 },
    });
  }
  return {
    name: `web-route-map-${objective}`,
    objective: {
      direction: objective === 'clearance' ? glpk.GLP_MAX : glpk.GLP_MIN,
      name: objective,
      vars: [...problem.costs.entries()].map(([name, cost]) => ({ name, coef: cost[objective] })),
    },
    subjectTo,
    binaries: [...problem.costs.keys()],
  };
}

function selectedIds(vars: Record<string, number>): Set<string> {
  return new Set(Object.entries(vars).filter(([, value]) => value > 0.5).map(([name]) => name));
}

function selected<T extends { id: string }>(candidates: Map<string, T[]>, ids: Set<string>): T[] {
  return [...candidates.values()].map((group) => {
    const candidate = group.find((item) => ids.has(item.id));
    if (!candidate) throw new Error('Solver result omitted a required layout candidate.');
    return candidate;
  });
}

function buildPlan(
  input: WebRouteMapLayoutInput,
  membersBySequence: Map<string, string[]>,
  markers: MarkerCandidate[],
  routes: RouteCandidate[],
  diagnostics: WebRouteMapLayoutDiagnostics
): WebRouteMapLayoutPlan {
  return {
    layoutVersion: input.layoutVersion,
    markers: markers.map((marker) => ({
      sequence: marker.sequence,
      memberSequences: membersBySequence.get(marker.sequence) ?? [marker.sequence],
      point: marker.leader[0],
      rect: marker.rect,
      direction: marker.direction,
      leader: marker.leader,
      isCluster: (membersBySequence.get(marker.sequence)?.length ?? 1) > 1,
    })),
    routes: routes.map((route) => ({
      id: route.route.id,
      fromSequence: route.route.fromSequence,
      toSequence: route.route.toSequence,
      points: route.points,
      curvature: route.curvature,
    })),
    diagnostics,
  };
}

export async function solveWebRouteMapLayout(
  sourceInput: WebRouteMapLayoutInput,
  glpk: WebRouteMapMipSolver
): Promise<WebRouteMapLayoutPlan> {
  const startedAt = performance.now();
  const capacity = Math.min(sourceInput.maxVisibleMarkers ?? 12, sourceInput.markers.length);
  const minimumVisibleMarkers = sourceInput.activeSequence ? Math.min(2, sourceInput.markers.length) : 1;
  for (let targetMarkerCount = capacity; targetMarkerCount >= minimumVisibleMarkers; targetMarkerCount -= 1) {
    const plan = await solvePreparedInput(clusterMarkersToCapacity(sourceInput, targetMarkerCount), glpk, startedAt);
    if (plan.diagnostics.status === 'optimal' || plan.diagnostics.status === 'feasible') return plan;
  }
  return buildPlan(sourceInput, new Map(), [], [], {
    status: 'infeasible',
    solver: 'glpk-mip',
    elapsedMs: performance.now() - startedAt,
    candidateCount: 0,
    rejectedConflicts: 0,
  });
}

async function solvePreparedLayout(
  input: WebRouteMapLayoutInput,
  membersBySequence: Map<string, string[]>,
  glpk: WebRouteMapMipSolver,
  startedAt: number
): Promise<WebRouteMapLayoutPlan> {
  const markerCandidates = buildMarkerCandidates(input);
  const routeCandidates = buildRouteCandidates(input);
  const problem = buildOptimizationProblem(input, markerCandidates, routeCandidates);
  if (problem.groups.some((group) => group.candidateIds.length === 0)) {
    return buildPlan(input, membersBySequence, [], [], {
      status: 'infeasible',
      solver: 'glpk-mip',
      elapsedMs: performance.now() - startedAt,
      candidateCount: problem.candidateCount,
      rejectedConflicts: problem.conflicts.length,
    });
  }

  const solveOptions = { msglev: glpk.GLP_MSG_OFF, presol: true, tmlim: 3 };
  const clearanceResult = await glpk.solve(buildLp(glpk, problem, 'clearance'), solveOptions);
  const clearanceStatus = clearanceResult.result.status;
  if (clearanceStatus !== glpk.GLP_OPT && clearanceStatus !== glpk.GLP_FEAS) {
    return buildPlan(input, membersBySequence, [], [], {
      status: 'infeasible',
      solver: 'glpk-mip',
      elapsedMs: performance.now() - startedAt,
      candidateCount: problem.candidateCount,
      rejectedConflicts: problem.conflicts.length,
    });
  }

  const comfortResult = await glpk.solve(
    buildLp(glpk, problem, 'comfort', clearanceResult.result.z - 0.001),
    solveOptions
  );
  const finalResult =
    comfortResult.result.status === glpk.GLP_OPT || comfortResult.result.status === glpk.GLP_FEAS
      ? comfortResult
      : clearanceResult;
  const markerPlacements = selected(markerCandidates, selectedIds(finalResult.result.vars));
  const routePlacements = selected(routeCandidates, selectedIds(finalResult.result.vars));
  const diagnostics: WebRouteMapLayoutDiagnostics = {
    status: finalResult.result.status === glpk.GLP_OPT ? 'optimal' : 'feasible',
    solver: 'glpk-mip',
    elapsedMs: performance.now() - startedAt,
    candidateCount: problem.candidateCount,
    rejectedConflicts: problem.conflicts.length,
  };
  const plan = buildPlan(input, membersBySequence, markerPlacements, routePlacements, diagnostics);
  const violations = validateWebRouteMapLayout(input, plan);
  if (violations.length > 0) {
    return { ...plan, markers: [], routes: [], diagnostics: { ...diagnostics, status: 'failed' } };
  }
  return plan;
}
