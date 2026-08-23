'use client';

import type { Map as LeafletMap, Polyline, TileLayer } from 'leaflet';
import L from 'leaflet';
import React, { useEffect, useRef } from 'react';
import type { RouteSegmentViewModel } from '../../../display/types.ts';
import type { MapColors, MapRenderState, MapTileStyle } from './types.ts';
import { generateContinuousSmoothSpline } from '../../../lib/rules/mapMarkerLayoutRules.ts';

export const MAP_TILE_RENDER_TIMEOUT_MS = 30_000;

interface LuxuryMapGeoCanvasProps {
  mapInstance: LeafletMap | null;
  mapContainerRef: React.RefObject<HTMLDivElement | null>;
  segments: RouteSegmentViewModel[];
  mapColors: MapColors;
  activeSequence?: string;
  isMapReady: boolean;
  tileStyle: MapTileStyle;
  onRenderStateChange?: (state: MapRenderState) => void;
}

export function LuxuryMapGeoCanvas({
  mapInstance,
  mapContainerRef,
  segments,
  mapColors,
  activeSequence,
  isMapReady,
  tileStyle,
  onRenderStateChange,
}: LuxuryMapGeoCanvasProps) {
  const tileLayerRef = useRef<TileLayer | null>(null);
  const polylinesRef = useRef<Polyline[]>([]);

  // Setup Tile Layer
  useEffect(() => {
    if (!mapInstance || !isMapReady) return;

    // PDF uses a label-free raster so the brochure owns the only visible copy.
    // Screen maps retain their resilient provider chain behind the same-origin route.
    const tileUrl = `/api/map-tiles/{z}/{x}/{y}?style=${tileStyle}`;
    let settled = false;
    const report = (state: Extract<MapRenderState, 'ready' | 'failed'>) => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timeoutId);
      onRenderStateChange?.(state);
    };

    onRenderStateChange?.('loading');

    tileLayerRef.current?.remove();
    const tileLayer = L.tileLayer(tileUrl, {
      maxZoom: 18,
      attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
      className: 'luxury-map-tile-layer',
    });

    tileLayer.once('load', () => report('ready'));
    tileLayer.once('tileerror', () => report('failed'));
    const timeoutId = window.setTimeout(() => report('failed'), MAP_TILE_RENDER_TIMEOUT_MS);
    tileLayer.addTo(mapInstance);

    tileLayerRef.current = tileLayer;

    return () => {
      window.clearTimeout(timeoutId);
      tileLayer.remove();
      tileLayerRef.current = null;
    };
  }, [isMapReady, mapInstance, onRenderStateChange, tileStyle]);

  // Render Decorative Curved Route Lines with Continuous C1 Spline
  useEffect(() => {
    if (!mapInstance || !isMapReady) return;

    // Clear previous polylines
    polylinesRef.current.forEach((p) => p.remove());
    polylinesRef.current = [];

    const coordinates = segments
      .map((s) => s.coordinates)
      .filter((c): c is [number, number] => Array.isArray(c) && c.length === 2);

    if (coordinates.length < 2) return;

    const routeColor = mapColors.route || 'var(--color-accent)';
    const isPdf = tileStyle === 'carto-parchment-nolabels-pdf-v1';

    // Generate full continuous C1 spline path with Adaptive ACMCS Curvature
    const fullSplinePoints = generateContinuousSmoothSpline(coordinates, {
      tension: 0.38,
      samplesPerSegment: 48,
    });

    const isAnyActive = isPdf || Boolean(activeSequence);

    // Soft glow ambient background line across continuous route
    const bgGlowLine = L.polyline(fullSplinePoints, {
      color: routeColor,
      weight: isAnyActive ? 5.5 : 4.0,
      opacity: isAnyActive ? 0.35 : 0.2,
      lineCap: 'round',
      lineJoin: 'round',
      interactive: false,
    }).addTo(mapInstance);

    // Foreground dashed trajectory line
    const mainDashedLine = L.polyline(fullSplinePoints, {
      color: routeColor,
      weight: isAnyActive ? 2.8 : 2.2,
      opacity: isAnyActive ? 1.0 : 0.85,
      dashArray: '6, 6',
      lineCap: 'round',
      lineJoin: 'round',
      interactive: false,
    }).addTo(mapInstance);

    polylinesRef.current.push(bgGlowLine, mainDashedLine);

    return () => {
      polylinesRef.current.forEach((p) => p.remove());
      polylinesRef.current = [];
    };
  }, [activeSequence, isMapReady, mapColors.route, mapInstance, segments, tileStyle]);

  return (
    <div
      className={`luxury-map-geo-canvas${
        tileStyle === 'carto-parchment-nolabels-pdf-v1' ? ' luxury-map-geo-canvas--pdf' : ''
      } relative w-full h-full overflow-hidden select-none`}
    >
      <div
        ref={mapContainerRef}
        className="luxury-map-leaflet-container w-full h-full"
        aria-hidden="true"
      />
    </div>
  );
}
