'use client';

import type { Map as LeafletMap } from 'leaflet';
import L from 'leaflet';
import { useCallback, useMemo, useState } from 'react';
import type { ViewMode } from '../../../../display/contracts.ts';
import type { RouteSegmentViewModel } from '../../../../display/types.ts';
import { resolveWebRouteMapFocusZoom } from './layout/focus.ts';

export { resolveWebRouteMapFocusZoom } from './layout/focus.ts';

export function useWebRouteMapInteraction({
  map,
  segments,
  initialActiveSequence,
  viewMode,
}: {
  map: LeafletMap | null;
  segments: RouteSegmentViewModel[];
  initialActiveSequence: string;
  viewMode: Exclude<ViewMode, 'pdf'>;
}) {
  const [requestedActiveSequence, setActiveSequence] = useState(initialActiveSequence);
  const segmentsBySequence = useMemo(
    () => new Map(segments.map((segment) => [segment.sequence, segment])),
    [segments]
  );

  const activeSequence = segmentsBySequence.has(requestedActiveSequence)
    ? requestedActiveSequence
    : initialActiveSequence;

  const activate = useCallback((sequence: string) => {
    const segment = segmentsBySequence.get(sequence);
    if (!segment) return;
    setActiveSequence(sequence);
    if (!map) return;
    map.flyTo(
      L.latLng(segment.coordinates[0], segment.coordinates[1]),
      resolveWebRouteMapFocusZoom(map.getZoom(), viewMode),
      { animate: true, duration: 0.6 }
    );
  }, [map, segmentsBySequence, viewMode]);

  return { activeSequence, activate };
}
