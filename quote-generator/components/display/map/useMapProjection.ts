'use client';

import type { Map as LeafletMap } from 'leaflet';
import L from 'leaflet';
import { useCallback, useEffect, useRef, useState } from 'react';
import type { ViewMode } from '../../../display/contracts.ts';
import type { ProjectedPoint } from './types.ts';

export function useMapProjection({
  coordinates,
  viewMode,
}: {
  coordinates: Array<[number, number]>;
  viewMode: ViewMode;
}) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const [mapInstance, setMapInstance] = useState<LeafletMap | null>(null);
  const [isMapReady, setIsMapReady] = useState(false);
  const [renderVersion, setRenderVersion] = useState(0);

  const triggerUpdate = useCallback(() => {
    setRenderVersion((v) => (v + 1) % 1_000_000);
  }, []);

  // Initialize Map
  useEffect(() => {
    const container = mapContainerRef.current;
    if (!container || coordinates.length === 0) {
      return;
    }

    const isPdf = viewMode === 'pdf';
    const map = L.map(container, {
      zoomControl: false,
      attributionControl: false,
      scrollWheelZoom: !isPdf,
      dragging: !isPdf,
      touchZoom: !isPdf,
      doubleClickZoom: !isPdf,
      boxZoom: !isPdf,
      keyboard: !isPdf,
    });

    const latLngs = coordinates.map(([lat, lng]) => L.latLng(lat, lng));
    const bounds = L.latLngBounds(latLngs);

    // Ensure bounds has sufficient geographic context (spanning country region)
    // If only 1 city or tight coordinates, expand bounds so Vietnam & Indochina context is visible
    const southWest = bounds.getSouthWest();
    const northEast = bounds.getNorthEast();
    const latSpan = Math.abs(northEast.lat - southWest.lat);
    const lngSpan = Math.abs(northEast.lng - southWest.lng);

    if (latSpan < 5 || lngSpan < 4) {
      bounds.extend(L.latLng(8.6, 104.5));
      bounds.extend(L.latLng(22.8, 108.0));
      bounds.extend(L.latLng(16.5, 112.5));
    }

    // Padding customized for vertical A4 portrait / mobile / desktop
    const padRatio = viewMode === 'pdf' ? 0.22 : viewMode === 'mobile' ? 0.20 : 0.22;
    map.fitBounds(bounds.pad(padRatio), {
      maxZoom: isPdf ? 6.2 : 6.8,
      animate: false,
    });

    const updateHandler = () => {
      triggerUpdate();
    };

    map.on('move', updateHandler);
    map.on('zoom', updateHandler);
    map.on('viewreset', updateHandler);
    map.on('resize', updateHandler);

    const resizeObserver = new ResizeObserver(() => {
      requestAnimationFrame(() => {
        map.invalidateSize({ pan: false });
        triggerUpdate();
      });
    });
    resizeObserver.observe(container);

    setMapInstance(map);
    setIsMapReady(true);
    triggerUpdate();

    const initialFrame = requestAnimationFrame(() => {
      map.invalidateSize({ pan: false });
      triggerUpdate();
    });

    return () => {
      cancelAnimationFrame(initialFrame);
      resizeObserver.disconnect();
      map.off('move', updateHandler);
      map.off('zoom', updateHandler);
      map.off('viewreset', updateHandler);
      map.off('resize', updateHandler);
      map.remove();
      setMapInstance(null);
      setIsMapReady(false);
    };
  }, [coordinates, triggerUpdate, viewMode]);

  // Dynamic projection from geographic [lat, lng] to container pixel coordinate [x, y]
  const project = useCallback(
    (lat: number, lng: number): ProjectedPoint => {
      const container = mapContainerRef.current;
      if (!mapInstance || !container) {
        return { x: -9999, y: -9999, visible: false };
      }

      try {
        const point = mapInstance.latLngToContainerPoint(L.latLng(lat, lng));
        const rect = container.getBoundingClientRect();
        const width = rect.width || container.clientWidth || 794;
        const height = rect.height || container.clientHeight || 1123;

        const isInsideViewport =
          point.x >= -100 &&
          point.x <= width + 100 &&
          point.y >= -100 &&
          point.y <= height + 100;

        return {
          x: point.x,
          y: point.y,
          visible: isInsideViewport && Number.isFinite(point.x) && Number.isFinite(point.y),
        };
      } catch {
        return { x: -9999, y: -9999, visible: false };
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [isMapReady, mapInstance, renderVersion]
  );

  return {
    mapContainerRef,
    mapInstance,
    isMapReady,
    project,
    renderVersion,
  };
}
