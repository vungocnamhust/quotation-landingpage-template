'use client';

import type { Map as LeafletMap, Polyline } from 'leaflet';
import L from 'leaflet';
import { useEffect, useRef } from 'react';
import type { WebRouteMapLayoutPlan } from './layout/contracts.ts';

export function WebRouteMapRouteLayer({
  map,
  plan,
  activeSequence,
  routeColor,
}: {
  map: LeafletMap | null;
  plan: WebRouteMapLayoutPlan | null;
  activeSequence: string;
  routeColor: string;
}) {
  const polylinesRef = useRef<Polyline[]>([]);
  useEffect(() => {
    polylinesRef.current.forEach((polyline) => polyline.remove());
    polylinesRef.current = [];
    if (!map || !plan) return;
    for (const route of plan.routes) {
      const isActive = route.fromSequence === activeSequence || route.toSequence === activeSequence;
      const positions = route.points.map((point) => map.containerPointToLatLng([point.x, point.y]));
      const glow = L.polyline(positions, {
        color: routeColor,
        weight: isActive ? 6 : 4,
        opacity: isActive ? 0.35 : 0.15,
        lineCap: 'round',
        lineJoin: 'round',
        interactive: false,
      }).addTo(map);
      const path = L.polyline(positions, {
        color: routeColor,
        weight: isActive ? 3.5 : 2.5,
        opacity: isActive ? 1 : 0.8,
        dashArray: '6, 6',
        lineCap: 'round',
        lineJoin: 'round',
        interactive: false,
      }).addTo(map);
      polylinesRef.current.push(glow, path);
    }
    return () => {
      polylinesRef.current.forEach((polyline) => polyline.remove());
      polylinesRef.current = [];
    };
  }, [activeSequence, map, plan, routeColor]);
  return null;
}
