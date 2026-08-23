'use client';

import type { Map as LeafletMap } from 'leaflet';
import L from 'leaflet';
import { useCallback, useEffect, useRef, useState } from 'react';
import type { ViewMode } from '@/display/contracts.ts';
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

    // Ensure bounds has sufficient geographic context
    // Only expand if coordinates are clustered tightly in a single localized area (<2.5 deg)
    const southWest = bounds.getSouthWest();
    const northEast = bounds.getNorthEast();
    const latSpan = Math.abs(northEast.lat - southWest.lat);
    const lngSpan = Math.abs(northEast.lng - southWest.lng);

    if (latSpan < 2.5 && lngSpan < 2.5) {
      // Localized trip: expand slightly by ~0.8 deg for breathing room
      bounds.extend(L.latLng(southWest.lat - 0.8, southWest.lng - 0.8));
      bounds.extend(L.latLng(northEast.lat + 0.8, northEast.lng + 0.8));
    }

    // Adaptive padding for vertical A4 portrait / mobile / desktop
    // 8%-10% padding fits the Vietnam route tightly with maximum zoom clarity
    const padRatio = viewMode === 'pdf' ? 0.08 : viewMode === 'mobile' ? 0.10 : 0.10;
    map.fitBounds(bounds.pad(padRatio), {
      maxZoom: isPdf ? 7.2 : 7.5,
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
