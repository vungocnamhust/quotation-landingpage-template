'use client';

import type { LatLngExpression, Map as LeafletMap, Polyline, TileLayer } from 'leaflet';
import L from 'leaflet';
import React, { useEffect, useRef } from 'react';
import type { RouteSegmentViewModel } from '../../../display/types.ts';
import type { MapColors } from './types.ts';

interface LuxuryMapGeoCanvasProps {
  mapInstance: LeafletMap | null;
  mapContainerRef: React.RefObject<HTMLDivElement | null>;
  segments: RouteSegmentViewModel[];
  mapColors: MapColors;
  activeSequence?: string;
  isMapReady: boolean;
}

// Generates an elegant curved geodesic bezier path between two coordinates
function getCurvedRoutePoints(p1: [number, number], p2: [number, number], segmentsCount = 36): LatLngExpression[] {
  const midLat = (p1[0] + p2[0]) / 2;
  const midLng = (p1[1] + p2[1]) / 2;
  const dx = p2[1] - p1[1];
  const dy = p2[0] - p1[0];
  const distance = Math.sqrt(dx * dx + dy * dy);
  if (distance === 0) return [p1, p2];

  // Subtle curvature offset perpendicular to the line
  const curvatureScale = Math.max(0.04, Math.min(0.22, distance * 0.12));
  const ctrlLat = midLat - (dx / distance) * curvatureScale;
  const ctrlLng = midLng + (dy / distance) * curvatureScale;

  const points: LatLngExpression[] = [];
  for (let i = 0; i <= segmentsCount; i++) {
    const t = i / segmentsCount;
    const lat = (1 - t) * (1 - t) * p1[0] + 2 * (1 - t) * t * ctrlLat + t * t * p2[0];
    const lng = (1 - t) * (1 - t) * p1[1] + 2 * (1 - t) * t * ctrlLng + t * t * p2[1];
    points.push([lat, lng]);
  }
  return points;
}

export function LuxuryMapGeoCanvas({
  mapInstance,
  mapContainerRef,
  segments,
  mapColors,
  activeSequence,
  isMapReady,
}: LuxuryMapGeoCanvasProps) {
  const tileLayerRef = useRef<TileLayer | null>(null);
  const polylinesRef = useRef<Polyline[]>([]);

  // Setup Tile Layer
  useEffect(() => {
    if (!mapInstance || !isMapReady) return;

    // Use our server-side proxy route that serves high-availability tiles
    const tileUrl = '/api/map-tiles/{z}/{x}/{y}?style=luxury-editorial-v1';

    tileLayerRef.current?.remove();
    const tileLayer = L.tileLayer(tileUrl, {
      maxZoom: 18,
      attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
      className: 'luxury-map-tile-layer',
    }).addTo(mapInstance);

    tileLayerRef.current = tileLayer;

    return () => {
      tileLayer.remove();
      tileLayerRef.current = null;
    };
  }, [isMapReady, mapInstance]);

  // Render Decorative Curved Route Lines
  useEffect(() => {
    if (!mapInstance || !isMapReady) return;

    // Clear previous polylines
    polylinesRef.current.forEach((p) => p.remove());
    polylinesRef.current = [];

    const coordinates = segments.map((s) => s.coordinates);
    if (coordinates.length < 2) return;

    const routeColor = mapColors.route || 'var(--color-accent)';

    for (let i = 0; i < coordinates.length - 1; i++) {
      const p1 = coordinates[i];
      const p2 = coordinates[i + 1];
      if (!p1 || !p2) continue;

      const pathPoints = getCurvedRoutePoints(p1, p2);
      const isSegmentActive =
        activeSequence === segments[i]?.sequence || activeSequence === segments[i + 1]?.sequence;

      // Soft glow ambient background line
      const bgGlowLine = L.polyline(pathPoints, {
        color: routeColor,
        weight: isSegmentActive ? 7 : 4,
        opacity: isSegmentActive ? 0.35 : 0.18,
        lineCap: 'round',
        lineJoin: 'round',
        interactive: false,
      }).addTo(mapInstance);

      // Foreground dashed trajectory line
      const mainDashedLine = L.polyline(pathPoints, {
        color: routeColor,
        weight: isSegmentActive ? 3.5 : 2.5,
        opacity: isSegmentActive ? 1.0 : 0.85,
        dashArray: '6, 6',
        lineCap: 'round',
        lineJoin: 'round',
        interactive: false,
      }).addTo(mapInstance);

      polylinesRef.current.push(bgGlowLine, mainDashedLine);
    }

    return () => {
      polylinesRef.current.forEach((p) => p.remove());
      polylinesRef.current = [];
    };
  }, [activeSequence, isMapReady, mapColors.route, mapInstance, segments]);

  return (
    <div className="luxury-map-geo-canvas relative w-full h-full overflow-hidden select-none">
      <div
        ref={mapContainerRef}
        className="luxury-map-leaflet-container w-full h-full"
        aria-hidden="true"
      />
    </div>
  );
}
