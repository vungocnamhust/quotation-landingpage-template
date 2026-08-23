'use client';

import type { Map as LeafletMap } from 'leaflet';
import L from 'leaflet';
import { useEffect, useMemo, useRef, useState } from 'react';
import type { RouteSegmentViewModel } from '../../../../display/types.ts';
import { textValue } from '../../../../display/types.ts';
import type {
  WebRouteMapLayoutPlan,
  WebRouteMapLayoutDiagnostics,
  WebRouteMapWorkerRequest,
  WebRouteMapWorkerResponse,
} from './layout/contracts.ts';

export interface WebRouteMapLayoutState {
  plan: WebRouteMapLayoutPlan | null;
  status: 'loading' | 'ready' | 'failed';
  error?: string;
  diagnostics?: WebRouteMapLayoutDiagnostics;
}

function measureMarkerLabels(segments: RouteSegmentViewModel[], typographyClassName: string) {
  if (typeof document === 'undefined') {
    return new Map(segments.map((segment) => [segment.sequence, { width: 180, height: 30 }]));
  }
  const host = document.createElement('div');
  host.className = 'display-route-map-marker-measure';
  document.body.appendChild(host);
  const sizes = new Map<string, { width: number; height: number }>();
  for (const segment of segments) {
    const capsule = document.createElement('div');
    capsule.className = 'display-route-map-marker__capsule';
    const badge = document.createElement('span');
    badge.className = `display-route-map-marker__badge ${typographyClassName}`;
    badge.textContent = textValue(segment.dayLabel);
    const label = document.createElement('span');
    label.className = `display-route-map-marker__label ${typographyClassName}`;
    label.textContent = textValue(segment.city);
    capsule.append(badge, label);
    host.appendChild(capsule);
    const rect = capsule.getBoundingClientRect();
    sizes.set(segment.sequence, { width: Math.ceil(rect.width), height: Math.ceil(rect.height) });
  }
  host.remove();
  return sizes;
}

function getReservedZones(map: LeafletMap) {
  const container = map.getContainer();
  const containerRect = container.getBoundingClientRect();
  return Array.from(container.querySelectorAll('.leaflet-control-zoom, .leaflet-control-attribution')).map((element) => {
    const rect = element.getBoundingClientRect();
    return {
      x: rect.left - containerRect.left,
      y: rect.top - containerRect.top,
      width: rect.width,
      height: rect.height,
    };
  });
}

export function useWebRouteMapLayout({
  map,
  segments,
  typographyClassName,
  activeSequence,
  maxLeaderLength,
  layoutVersion,
}: {
  map: LeafletMap | null;
  segments: RouteSegmentViewModel[];
  typographyClassName: string;
  activeSequence: string;
  maxLeaderLength: number;
  layoutVersion: string;
}): WebRouteMapLayoutState {
  const [state, setState] = useState<WebRouteMapLayoutState>({ plan: null, status: 'loading' });
  const workerRef = useRef<Worker | null>(null);
  const requestIdRef = useRef(0);
  const frameRef = useRef<number | null>(null);

  const segmentKey = useMemo(
    () => segments.map((segment) => `${segment.sequence}:${segment.coordinates.join(',')}:${textValue(segment.city)}`).join('|'),
    [segments]
  );

  useEffect(() => {
    const worker = new Worker(new URL('./layout/webRouteMapLayout.worker.ts', import.meta.url));
    workerRef.current = worker;
    return () => {
      worker.terminate();
      workerRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!map || segments.length === 0 || !workerRef.current) return;
    let disposed = false;
    const schedule = () => {
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
      frameRef.current = requestAnimationFrame(async () => {
        await document.fonts?.ready;
        if (disposed || !workerRef.current) return;
        const labelSizes = measureMarkerLabels(segments, typographyClassName);
        const size = map.getSize();
        const projectedSegments = segments.map((segment, order) => {
          const point = map.latLngToContainerPoint(L.latLng(segment.coordinates[0], segment.coordinates[1]));
          return {
            sequence: segment.sequence,
            point: { x: point.x, y: point.y },
            labelSize: labelSizes.get(segment.sequence) ?? { width: 180, height: 30 },
            order,
          };
        });
        const viewportHalo = maxLeaderLength + 16;
        const visibleSequences = new Set(
          projectedSegments
            .filter(({ point, sequence }) =>
              sequence === activeSequence || (
                point.x >= -viewportHalo &&
                point.y >= -viewportHalo &&
                point.x <= size.x + viewportHalo &&
                point.y <= size.y + viewportHalo
              )
            )
            .map(({ sequence }) => sequence)
        );
        const markers = projectedSegments.filter(({ sequence }) => visibleSequences.has(sequence));
        const id = ++requestIdRef.current;
        const request: WebRouteMapWorkerRequest = {
          id,
          input: {
            viewport: { width: size.x, height: size.y },
            markers,
            routes: segments.slice(1).flatMap((segment, index) =>
              visibleSequences.has(segments[index].sequence) && visibleSequences.has(segment.sequence)
                ? [{
                    id: `${segments[index].sequence}->${segment.sequence}`,
                    fromSequence: segments[index].sequence,
                    toSequence: segment.sequence,
                    order: index,
                  }]
                : []
            ),
            reservedZones: getReservedZones(map),
            activeSequence,
            maxLeaderLength,
            layoutVersion,
          },
        };
        setState((current) => ({ ...current, status: 'loading' }));
        workerRef.current.postMessage(request);
      });
    };
    const handleMessage = (event: MessageEvent<WebRouteMapWorkerResponse>) => {
      const response = event.data;
      if (disposed || response.id !== requestIdRef.current) return;
      if (!response.plan || response.plan.diagnostics.status === 'failed' || response.plan.diagnostics.status === 'infeasible') {
        setState({ plan: null, status: 'failed', error: response.error ?? response.plan?.diagnostics.status, diagnostics: response.plan?.diagnostics });
        return;
      }
      setState({ plan: response.plan, status: 'ready', diagnostics: response.plan.diagnostics });
    };
    const handleFailure = () => setState({ plan: null, status: 'failed', error: 'Worker bootstrap failed.' });
    workerRef.current.addEventListener('message', handleMessage);
    workerRef.current.addEventListener('error', handleFailure);
    map.on('moveend', schedule);
    map.on('resize', schedule);
    schedule();
    return () => {
      disposed = true;
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
      workerRef.current?.removeEventListener('message', handleMessage);
      workerRef.current?.removeEventListener('error', handleFailure);
      map.off('moveend', schedule);
      map.off('resize', schedule);
    };
  }, [activeSequence, layoutVersion, map, maxLeaderLength, segmentKey, segments, typographyClassName]);

  return state;
}
