/**
 * Serializable contract between the web-map projection adapter, the worker
 * optimizer, and Leaflet render layers. This module intentionally has no
 * React, Leaflet, DOM, or PDF dependencies.
 */

export interface MapPoint {
  x: number;
  y: number;
}

export interface MapRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export type MarkerAnchorDirection =
  | 'left'
  | 'right'
  | 'top'
  | 'bottom'
  | 'top-left'
  | 'top-right'
  | 'bottom-left'
  | 'bottom-right';

export interface WebRouteMapMarkerInput {
  sequence: string;
  point: MapPoint;
  labelSize: { width: number; height: number };
  order: number;
  memberSequences?: string[];
}

export interface WebRouteMapRouteInput {
  id: string;
  fromSequence: string;
  toSequence: string;
  order: number;
}

export interface WebRouteMapLayoutInput {
  viewport: { width: number; height: number };
  markers: WebRouteMapMarkerInput[];
  routes: WebRouteMapRouteInput[];
  reservedZones: MapRect[];
  minimumClearance?: number;
  maxVisibleMarkers?: number;
  maxLeaderLength?: number;
  activeSequence?: string;
  layoutVersion: string;
}

export interface WebRouteMapMarkerPlacement {
  sequence: string;
  memberSequences: string[];
  point: MapPoint;
  rect: MapRect;
  direction: MarkerAnchorDirection;
  leader: MapPoint[];
  isCluster: boolean;
}

export interface WebRouteMapRoutePlacement {
  id: string;
  fromSequence: string;
  toSequence: string;
  points: MapPoint[];
  curvature: 'left' | 'right' | 'loop';
}

export interface WebRouteMapLayoutDiagnostics {
  status: 'optimal' | 'feasible' | 'infeasible' | 'failed';
  solver: 'glpk-mip';
  elapsedMs: number;
  candidateCount: number;
  rejectedConflicts: number;
}

export interface WebRouteMapLayoutPlan {
  layoutVersion: string;
  markers: WebRouteMapMarkerPlacement[];
  routes: WebRouteMapRoutePlacement[];
  diagnostics: WebRouteMapLayoutDiagnostics;
}

export interface WebRouteMapWorkerRequest {
  id: number;
  input: WebRouteMapLayoutInput;
}

export interface WebRouteMapWorkerResponse {
  id: number;
  plan?: WebRouteMapLayoutPlan;
  error?: string;
}
