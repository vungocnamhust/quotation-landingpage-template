'use client';

import type { LatLngExpression, Map as LeafletMap, TileLayer, TileLayerOptions } from 'leaflet';
import L from 'leaflet';
import { useEffect, useMemo, useRef, useState } from 'react';
import type { ViewMode } from '../../../../display/contracts.ts';
import type { RouteMapViewModel, TypographySlotMap } from '../../../../display/types.ts';
import { textValue } from '../../../../display/types.ts';
import { getTypographyClassName } from '../../../../config/typography.ts';
import { requireTypographySlot } from '../../../../display/typographySlots.ts';
import { resolveMapTilePresentationClass } from '../../../../lib/mapTileStyles.ts';
import { cn } from '../../../../utils/cn.ts';
import { DisplayTitle, MetaText } from '../../atoms.tsx';
import { WebRouteMapMarkerLayer } from './WebRouteMapMarkerLayer.ts';
import { WebRouteMapRouteLayer } from './WebRouteMapRouteLayer.ts';
import { addWebRouteMapControls } from './WebRouteMapControls.ts';
import { useWebRouteMapLayout } from './useWebRouteMapLayout.ts';
import { useWebRouteMapInteraction } from './useWebRouteMapInteraction.ts';
import { ensureLeafletPatched } from './leafletPatch.ts';

interface WebRouteMapExperienceProps {
  viewModel: RouteMapViewModel;
  typography: TypographySlotMap;
  mapColors: { route: string; leader?: string; marker?: string; activeMarker?: string };
  viewMode: Exclude<ViewMode, 'pdf'>;
}

type TileProvider = { id: string; url: string; options: TileLayerOptions };

const SCREEN_TILE_STYLE = 'google-classic-v1';
const TILE_PROVIDERS: readonly TileProvider[] = [{
  id: 'same-origin-proxy',
  url: `/api/map-tiles/{z}/{x}/{y}?style=${SCREEN_TILE_STYLE}`,
  options: {
    maxZoom: 20,
  },
}];

export function WebRouteMapExperience({ viewModel, typography, mapColors, viewMode }: WebRouteMapExperienceProps) {
  const [map, setMap] = useState<LeafletMap | null>(null);
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const tileLayerRef = useRef<TileLayer | null>(null);
  const points = useMemo(
    () => viewModel.interactiveMarkers.map((marker) => marker.coordinates as [number, number]),
    [viewModel.interactiveMarkers]
  );
  const coordinatesKey = useMemo(() => points.map((point) => point.join(',')).join('|'), [points]);
  const markerTypographyClassName = getTypographyClassName(requireTypographySlot(typography, 'metaSecondary'));
  const { activeSequence, activate } = useWebRouteMapInteraction({
    map,
    segments: viewModel.segments,
    initialActiveSequence: viewModel.initialActiveSegment,
    viewMode,
  });
  const { plan, status: layoutStatus, error: layoutError, diagnostics } = useWebRouteMapLayout({
    map,
    segments: viewModel.segments,
    typographyClassName: markerTypographyClassName,
    activeSequence,
    maxLeaderLength: viewMode === 'mobile' ? 22 : 28,
    layoutVersion: `${viewMode}:${coordinatesKey}:${markerTypographyClassName}`,
  });

  useEffect(() => {
    const container = mapContainerRef.current;
    if (!container || points.length === 0) return;
    ensureLeafletPatched();
    const instance = L.map(container, {
      zoomControl: false,
      attributionControl: false,
      scrollWheelZoom: false,
      dragging: true,
      touchZoom: true,
      doubleClickZoom: true,
      boxZoom: true,
      keyboard: true,
    });
    const defaultBounds = L.latLngBounds(points as LatLngExpression[]).pad(viewMode === 'mobile' ? 0.22 : 0.28);
    addWebRouteMapControls(instance, defaultBounds);
    instance.fitBounds(defaultBounds, {
      maxZoom: 12,
      animate: false,
    });
    let providerIndex = 0;
    const addTileLayer = () => {
      const provider = TILE_PROVIDERS[providerIndex];
      if (!provider) return;
      tileLayerRef.current?.remove();
      const tileLayer = L.tileLayer(provider.url, {
        ...provider.options,
        className: resolveMapTilePresentationClass(SCREEN_TILE_STYLE) ?? '',
      }).addTo(instance);
      tileLayer.on('tileerror', () => {
        if (tileLayerRef.current !== tileLayer || providerIndex >= TILE_PROVIDERS.length - 1) return;
        providerIndex += 1;
        addTileLayer();
      });
      tileLayerRef.current = tileLayer;
    };
    addTileLayer();
    const observer = new ResizeObserver(() => requestAnimationFrame(() => instance.invalidateSize({ pan: false })));
    observer.observe(container);
    setMap(instance);
    const initialFrame = requestAnimationFrame(() => instance.invalidateSize({ pan: false }));
    return () => {
      cancelAnimationFrame(initialFrame);
      observer.disconnect();
      tileLayerRef.current = null;
      instance.remove();
      setMap(null);
    };
  }, [coordinatesKey, points, viewMode]);

  return (
    <div className={cn('display-route-map', viewMode === 'mobile' && 'is-mobile')} data-layout-status={layoutStatus} data-layout-error={layoutError} data-layout-candidates={diagnostics?.candidateCount}>
      <div className="display-route-map__screen">
        <div className="display-route-map__screen-map">
          <div className="display-route-map__canvas">
            <div
              ref={mapContainerRef}
              className="display-route-map__leaflet"
              aria-label={textValue(viewModel.overviewAriaLabel)}
              data-workspace-interactive="true"
              data-editable={typeof viewModel.overviewAriaLabel === 'string' ? undefined : viewModel.overviewAriaLabel.path}
              data-edit-owner={typeof viewModel.overviewAriaLabel === 'string' ? undefined : viewModel.overviewAriaLabel.owner}
              data-edit-mode={typeof viewModel.overviewAriaLabel === 'string' ? undefined : viewModel.overviewAriaLabel.mode}
            />
            <WebRouteMapRouteLayer map={map} plan={plan} activeSequence={activeSequence} routeColor={mapColors.route} />
            <WebRouteMapMarkerLayer map={map} plan={plan} segments={viewModel.segments} activeSequence={activeSequence} typographyClassName={markerTypographyClassName} leaderColor={mapColors.leader ?? mapColors.route} routeColor={mapColors.route} markerColor={mapColors.marker ?? mapColors.route} activeMarkerColor={mapColors.activeMarker ?? mapColors.route} onSelect={activate} />
          </div>
        </div>
        <div className="display-route-map__screen-timeline">
          <div className="display-route-map__timeline" role="list">
            {viewModel.segments.map((segment) => (
              <button key={segment.sequence} type="button" role="listitem" className={cn('display-route-map__timeline-item', activeSequence === segment.sequence && 'is-active')} onClick={() => activate(segment.sequence)} aria-current={activeSequence === segment.sequence ? 'true' : undefined}>
                {segment.sidebarLabel ? <MetaText variant={requireTypographySlot(typography, 'kicker')} tone="accent" className="display-route-map__timeline-duration">{segment.sidebarLabel}</MetaText> : null}
                <div className="display-route-map__timeline-copy">
                  <DisplayTitle as="h3" variant={requireTypographySlot(typography, 'metaPrimary')} className="display-route-map__timeline-title">{segment.city}</DisplayTitle>
                  {segment.hotelName ? <MetaText variant={requireTypographySlot(typography, 'metaSecondary')} tone="default" className="display-route-map__timeline-hotel">{segment.hotelName}</MetaText> : null}
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default WebRouteMapExperience;
