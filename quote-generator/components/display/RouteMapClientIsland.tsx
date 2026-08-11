'use client';

import dynamic from 'next/dynamic';
import type { RouteMapViewModel, TypographySlotMap } from '../../display/types';
import { textValue } from '../../display/types';
import type { ViewMode } from '../../display/contracts';

const RouteMapExperience = dynamic(() => import('./RouteMapExperience'), {
  ssr: false,
  loading: () => <div className="display-route-map__loading" />,
});

export default function RouteMapClientIsland({
  viewModel,
  typography,
  mapColors,
  viewMode,
}: {
  viewModel: RouteMapViewModel;
  typography: TypographySlotMap;
  mapColors: { route: string; marker?: string; activeMarker?: string };
  viewMode: Exclude<ViewMode, 'pdf'>;
}) {
  if (!viewModel.isInteractiveAvailable) {
    return <div className="display-route-map__unavailable" role="status">{textValue(viewModel.unavailableMessage)}</div>;
  }

  const islandKey = `${viewMode}:${viewModel.defaultMode}:${viewModel.initialActiveSegment}:${viewModel.segments
    .map((segment) => segment.sequence)
    .join('-')}`;

  return (
    <RouteMapExperience
      key={islandKey}
      viewModel={viewModel}
      typography={typography}
      mapColors={mapColors}
      viewMode={viewMode}
    />
  );
}
