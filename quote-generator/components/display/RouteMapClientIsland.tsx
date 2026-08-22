'use client';

import dynamic from 'next/dynamic';
import { useState } from 'react';
import type { RouteMapViewModel, TypographySlotMap } from '../../display/types.ts';
import { textValue } from '../../display/types.ts';
import type { ViewMode } from '../../display/contracts.ts';
import type { MapRenderState } from './map/types.ts';

const FullPageEditorialJourneyMap = dynamic(
  () => import('./map/FullPageEditorialJourneyMap').then((mod) => mod.FullPageEditorialJourneyMap),
  {
    ssr: false,
    loading: () => (
      <div className="display-route-map__loading animate-pulse bg-[var(--color-surface)] rounded-lg w-full h-[640px]" />
    ),
  }
);

export default function RouteMapClientIsland({
  viewModel,
  typography,
  mapColors,
  viewMode,
  quotationNumber,
  pageNumber,
  quoteText,
}: {
  viewModel: RouteMapViewModel;
  typography: TypographySlotMap;
  mapColors: { route: string; marker?: string; activeMarker?: string; land?: string; ocean?: string };
  viewMode: ViewMode;
  quotationNumber?: string;
  pageNumber?: string;
  quoteText?: string;
}) {
  const islandKey = `${viewMode}:${viewModel.defaultMode}:${viewModel.initialActiveSegment}:${viewModel.segments
    .map((segment) => segment.sequence)
    .join('-')}`;

  if (!viewModel.isInteractiveAvailable) {
    return (
      <div data-map-render-state="unavailable" className="display-route-map__unavailable" role="status">
        {textValue(viewModel.unavailableMessage)}
      </div>
    );
  }

  return (
    <InteractiveRouteMapIsland
      key={islandKey}
      islandKey={islandKey}
      viewModel={viewModel}
      typography={typography}
      mapColors={mapColors}
      viewMode={viewMode}
      quotationNumber={quotationNumber}
      pageNumber={pageNumber}
      quoteText={quoteText}
    />
  );
}

function InteractiveRouteMapIsland({
  islandKey,
  viewModel,
  typography,
  mapColors,
  viewMode,
  quotationNumber,
  pageNumber,
  quoteText,
}: {
  islandKey: string;
  viewModel: RouteMapViewModel;
  typography: TypographySlotMap;
  mapColors: { route: string; marker?: string; activeMarker?: string; land?: string; ocean?: string };
  viewMode: ViewMode;
  quotationNumber?: string;
  pageNumber?: string;
  quoteText?: string;
}) {
  const [mapRenderState, setMapRenderState] = useState<MapRenderState>('loading');

  return (
    <div data-map-render-state={mapRenderState} data-map-render-key={islandKey}>
      <FullPageEditorialJourneyMap
        viewModel={viewModel}
        typography={typography}
        mapColors={mapColors}
        viewMode={viewMode}
        quotationNumber={quotationNumber}
        pageNumber={pageNumber}
        quoteText={quoteText}
        onRenderStateChange={setMapRenderState}
      />
    </div>
  );
}
