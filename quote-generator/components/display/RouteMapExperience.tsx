'use client';

import type { LatLngExpression, Map as LeafletMap, Marker, Polyline, TileLayer, TileLayerOptions } from 'leaflet';
import L from 'leaflet';
import { useEffect, useMemo, useRef, useState } from 'react';
import type { ViewMode } from '../../display/contracts';
import type { RouteMapViewModel, TypographySlotMap } from '../../display/types';
import { textValue } from '../../display/types';
import { cn } from '../../utils/cn';
import { requireTypographySlot } from '../../display/typographySlots';
import { getTypographyClassName } from '../../config/typography';
import { DisplayTitle, MetaText } from './atoms';

interface RouteMapExperienceProps {
  viewModel: RouteMapViewModel;
  typography: TypographySlotMap;
  mapColors: { route: string; marker?: string; activeMarker?: string };
  viewMode: ViewMode;
}

type TileProvider = {
  id: string;
  url: string;
  options: TileLayerOptions;
};

// Tiles are loaded from the application origin. The server route performs the
// provider fallback, so browser extensions and corporate policies cannot block
// the map merely because a tile image comes from a third-party hostname.
const TILE_PROVIDERS: readonly TileProvider[] = [
  {
    id: 'same-origin-proxy',
    url: '/api/map-tiles/{z}/{x}/{y}?style=google-classic-v1',
    options: {
      attribution: '&copy; Google &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
      maxZoom: 20,
    },
  },
];

function buildClassicMarkerMarkup({
  dayLabel,
  label,
  isActive,
  typographyClassName,
  markerColor,
  activeMarkerColor,
}: {
  dayLabel: string;
  label: string;
  isActive: boolean;
  typographyClassName: string;
  markerColor?: string;
  activeMarkerColor?: string;
}) {
  const badgeBg = isActive ? (activeMarkerColor || markerColor) : markerColor;
  const badgeStyle = badgeBg ? `style="background-color: ${badgeBg} !important;"` : '';
  const labelColor = isActive ? (activeMarkerColor || markerColor) : (markerColor || 'var(--color-accent)');
  const labelStyle = labelColor ? `style="color: ${labelColor} !important;"` : '';

  return `
    <div class="display-route-map-marker display-route-map-marker--classic${isActive ? ' is-active' : ''}">
      <div class="display-route-map-marker__capsule">
        <div class="display-route-map-marker__badge ${typographyClassName}" ${badgeStyle}>${dayLabel}</div>
        <div class="display-route-map-marker__label ${typographyClassName}" ${labelStyle}>${label}</div>
      </div>
      <div class="display-route-map-marker__pointer" ${badgeStyle}></div>
    </div>
  `;
}

function buildMarkerIcon({
  dayLabel,
  label,
  isActive,
  typographyClassName,
  markerColor,
  activeMarkerColor,
}: {
  dayLabel: string;
  label: string;
  isActive: boolean;
  typographyClassName: string;
  markerColor?: string;
  activeMarkerColor?: string;
}) {
  return L.divIcon({
    html: buildClassicMarkerMarkup({ dayLabel, label, isActive, typographyClassName, markerColor, activeMarkerColor }),
    className: 'display-route-map-marker-icon',
    iconSize: [220, 42],
    iconAnchor: [20, 38],
  });
}



function getBezierPoints(p1: [number, number], p2: [number, number], count = 30): LatLngExpression[] {
  const midLat = (p1[0] + p2[0]) / 2;
  const midLng = (p1[1] + p2[1]) / 2;
  const dx = p2[1] - p1[1];
  const dy = p2[0] - p1[0];
  const len = Math.sqrt(dx * dx + dy * dy);
  if (len === 0) return [p1, p2];
  const scale = Math.max(0.04, Math.min(0.25, len * 0.15));
  const ctrlLat = midLat - (dx / len) * scale;
  const ctrlLng = midLng + (dy / len) * scale;
  const points: LatLngExpression[] = [];
  for (let i = 0; i <= count; i++) {
    const t = i / count;
    const lat = (1 - t) * (1 - t) * p1[0] + 2 * (1 - t) * t * ctrlLat + t * t * p2[0];
    const lng = (1 - t) * (1 - t) * p1[1] + 2 * (1 - t) * t * ctrlLng + t * t * p2[1];
    points.push([lat, lng]);
  }
  return points;
}

export default function RouteMapExperience({
  viewModel,
  typography,
  mapColors,
  viewMode,
}: RouteMapExperienceProps) {
  const [activeSequence, setActiveSequence] = useState(viewModel.initialActiveSegment);

  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<LeafletMap | null>(null);
  const tileLayerRef = useRef<TileLayer | null>(null);
  const polylinesRef = useRef<Polyline[]>([]);
  const markerMapRef = useRef<Map<string, Marker>>(new Map());

  const points = useMemo(
    () => viewModel.interactiveMarkers.map((marker) => marker.coordinates as [number, number]),
    [viewModel.interactiveMarkers]
  );

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current || points.length === 0) {
      return;
    }

    const map = L.map(mapContainerRef.current, {
      zoomControl: true,
      attributionControl: true,
      scrollWheelZoom: false,
      dragging: true,
    });

    const bounds = L.latLngBounds(points as LatLngExpression[]);
    map.fitBounds(bounds.pad(viewMode === 'mobile' ? 0.22 : 0.28), {
      maxZoom: 12,
    });

    let providerIndex = 0;
    const addTileLayer = () => {
      const provider = TILE_PROVIDERS[providerIndex];
      if (!provider) {
        return;
      }

      tileLayerRef.current?.remove();
      const tileLayer = L.tileLayer(provider.url, provider.options).addTo(map);
      tileLayer.on('tileerror', () => {
        // A failed tile means this provider cannot render the viewport. Switch
        // the whole layer so every tile comes from a separate provider rather
        // than leaving a patchwork of failed images behind.
        if (tileLayerRef.current !== tileLayer || providerIndex >= TILE_PROVIDERS.length - 1) {
          return;
        }
        providerIndex += 1;
        addTileLayer();
      });
      tileLayerRef.current = tileLayer;
    };
    addTileLayer();

    const observer = new ResizeObserver(() => {
      requestAnimationFrame(() => map.invalidateSize({ pan: false }));
    });
    observer.observe(mapContainerRef.current);

    mapRef.current = map;
    const markerMap = markerMapRef.current;

    const layoutFrame = requestAnimationFrame(() => map.invalidateSize({ pan: false }));

    return () => {
      cancelAnimationFrame(layoutFrame);
      observer.disconnect();
      markerMap.clear();
      polylinesRef.current.forEach((p) => p.remove());
      polylinesRef.current = [];
      tileLayerRef.current = null;
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, [points, viewMode]);

  useEffect(() => {
    if (!mapRef.current) {
      return;
    }

    const map = mapRef.current;

    polylinesRef.current.forEach((p) => p.remove());
    polylinesRef.current = [];
    markerMapRef.current.forEach((marker) => marker.remove());
    markerMapRef.current.clear();

    if (points.length > 1) {
      for (let i = 0; i < points.length - 1; i++) {
        const p1 = points[i];
        const p2 = points[i + 1];
        if (!p1 || !p2) continue;

        const pathPoints = getBezierPoints(p1, p2);
        const segmentSeq = viewModel.segments[i + 1]?.sequence;
        const isActiveSegment = activeSequence === segmentSeq || activeSequence === viewModel.segments[i]?.sequence;

        const bgPoly = L.polyline(pathPoints, {
          color: mapColors.route,
          weight: isActiveSegment ? 6 : 4,
          opacity: isActiveSegment ? 0.35 : 0.15,
        }).addTo(map);

        const poly = L.polyline(pathPoints, {
          color: mapColors.route,
          weight: isActiveSegment ? 3.5 : 2.5,
          opacity: isActiveSegment ? 1 : 0.8,
          dashArray: '6, 6',
        }).addTo(map);

        polylinesRef.current.push(bgPoly, poly);
      }
    }

    viewModel.segments.forEach((segment) => {
      const marker = L.marker(segment.coordinates as LatLngExpression, {
        icon: buildMarkerIcon({
          dayLabel: textValue(segment.dayLabel),
          label: textValue(segment.city),
          isActive: segment.sequence === activeSequence,
          typographyClassName: getTypographyClassName(requireTypographySlot(typography, 'metaSecondary')),
          markerColor: mapColors.marker,
          activeMarkerColor: mapColors.activeMarker,
        }),
      })
        .addTo(map)
        .on('click', () => {
          setActiveSequence(segment.sequence);
        });

      markerMapRef.current.set(segment.sequence, marker);
    });

    const nextMarker = markerMapRef.current.get(activeSequence);
    if (nextMarker) {
      const targetLatLng = nextMarker.getLatLng();
      if (
        targetLatLng &&
        typeof targetLatLng.lat === 'number' &&
        typeof targetLatLng.lng === 'number' &&
        !Number.isNaN(targetLatLng.lat) &&
        !Number.isNaN(targetLatLng.lng)
      ) {
        map.flyTo(targetLatLng, Math.max(map.getZoom(), viewMode === 'mobile' ? 6.4 : 7.6), {
          animate: true,
          duration: 0.6,
        });
      }
    }
  }, [activeSequence, mapColors, points, typography, viewMode, viewModel.segments]);

  return (
    <div className={cn('display-route-map', viewMode === 'mobile' && 'is-mobile')}>
      <div className="display-route-map__screen">
        <div className="display-route-map__screen-map">
          <div className="display-route-map__canvas">
            <div ref={mapContainerRef} className="display-route-map__leaflet" aria-label={textValue(viewModel.overviewAriaLabel)} data-editable={typeof viewModel.overviewAriaLabel === 'string' ? undefined : viewModel.overviewAriaLabel.path} data-edit-owner={typeof viewModel.overviewAriaLabel === 'string' ? undefined : viewModel.overviewAriaLabel.owner} data-edit-mode={typeof viewModel.overviewAriaLabel === 'string' ? undefined : viewModel.overviewAriaLabel.mode} />
          </div>
        </div>

        <div className="display-route-map__screen-timeline">
          <div className="display-route-map__timeline" role="list">
            {viewModel.segments.map((segment) => (
              <button
                key={segment.sequence}
                type="button"
                role="listitem"
                className={cn('display-route-map__timeline-item', activeSequence === segment.sequence && 'is-active')}
                onClick={() => setActiveSequence(segment.sequence)}
                aria-current={activeSequence === segment.sequence ? 'true' : undefined}
              >
                {segment.sidebarLabel ? (
                  <MetaText
                    variant={requireTypographySlot(typography, 'kicker')}
                    tone="accent"
                    className="display-route-map__timeline-duration"
                  >
                    {segment.sidebarLabel}
                  </MetaText>
                ) : null}

                <div className="display-route-map__timeline-copy">
                  <DisplayTitle
                    as="h3"
                    variant={requireTypographySlot(typography, 'metaPrimary')}
                    className="display-route-map__timeline-title"
                  >
                    {segment.city}
                  </DisplayTitle>
                  {segment.hotelName ? (
                    <MetaText
                      variant={requireTypographySlot(typography, 'metaSecondary')}
                      tone="default"
                      className="display-route-map__timeline-hotel"
                    >
                      {segment.hotelName}
                    </MetaText>
                  ) : null}
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
