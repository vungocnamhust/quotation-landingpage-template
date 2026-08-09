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
  mapColors: { route: string };
  viewMode: Exclude<ViewMode, 'pdf'>;
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
  index,
  label,
  isActive,
  typographyClassName,
}: {
  index: number;
  label: string;
  isActive: boolean;
  typographyClassName: string;
}) {
  return `
    <div class="display-route-map-marker display-route-map-marker--classic${isActive ? ' is-active' : ''}">
      <div class="display-route-map-marker__badge ${typographyClassName}">${index + 1}</div>
      <div class="display-route-map-marker__label ${typographyClassName}">${label}</div>
    </div>
  `;
}

function buildMarkerIcon({
  index,
  label,
  isActive,
  typographyClassName,
}: {
  index: number;
  label: string;
  isActive: boolean;
  typographyClassName: string;
}) {
  return L.divIcon({
    html: buildClassicMarkerMarkup({ index, label, isActive, typographyClassName }),
    className: 'display-route-map-marker-icon',
    iconSize: [148, 36],
    iconAnchor: [16, 18],
  });
}

function getDistance(c1: [number, number], c2: [number, number]) {
  const R = 6371;
  const dLat = ((c2[0] - c1[0]) * Math.PI) / 180;
  const dLon = ((c2[1] - c1[1]) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((c1[0] * Math.PI) / 180) * Math.cos((c2[0] * Math.PI) / 180) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

function getBezierPoints(p1: [number, number], p2: [number, number], count = 30): LatLngExpression[] {
  const midLat = (p1[0] + p2[0]) / 2;
  const midLng = (p1[1] + p2[1]) / 2;
  const dx = p2[1] - p1[1];
  const dy = p2[0] - p1[0];
  const len = Math.sqrt(dx * dx + dy * dy);
  if (len === 0) return [p1, p2];
  const scale = len * 0.15;
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

        const dist = getDistance(p1, p2);
        const isLongDist = dist > 150;
        const pathPoints = isLongDist ? getBezierPoints(p1, p2) : [p1, p2];

        const poly = L.polyline(pathPoints, {
          color: mapColors.route,
          weight: 3,
          opacity: 0.85,
          dashArray: isLongDist ? '6, 8' : 'none',
        }).addTo(map);

        polylinesRef.current.push(poly);
      }
    }

    viewModel.segments.forEach((segment, index) => {
      const marker = L.marker(segment.coordinates as LatLngExpression, {
        icon: buildMarkerIcon({
          index,
          label: textValue(segment.city),
          isActive: segment.sequence === activeSequence,
          typographyClassName: getTypographyClassName(requireTypographySlot(typography, 'metaSecondary')),
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
      map.flyTo(nextMarker.getLatLng(), Math.max(map.getZoom(), viewMode === 'mobile' ? 6.4 : 7.6), {
        animate: true,
        duration: 0.6,
      });
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
