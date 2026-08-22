'use client';

import React, { useMemo, useState } from 'react';
import type { FullPageMapProps } from './types.ts';
import { useMapProjection } from './useMapProjection.ts';
import { LuxuryMapGeoCanvas } from './LuxuryMapGeoCanvas.tsx';
import { MapFloatingOverlays } from './MapFloatingOverlays.tsx';
import { cn } from '../../../utils/cn.ts';

export function FullPageEditorialJourneyMap({
  viewModel,
  typography,
  mapColors,
  viewMode,
  className = '',
  onSegmentSelect,
  activeSequence: controlledActiveSequence,
  quotationNumber,
  pageNumber = '03',
  quoteText,
  onRenderStateChange,
}: FullPageMapProps) {
  const [internalActiveSequence, setInternalActiveSequence] = useState(
    viewModel.initialActiveSegment || viewModel.segments[0]?.sequence || '1'
  );

  const activeSequence = controlledActiveSequence ?? internalActiveSequence;

  const handleSelectSegment = (seq: string) => {
    setInternalActiveSequence(seq);
    if (onSegmentSelect) {
      onSegmentSelect(seq);
    }
  };

  const coordinates = useMemo(
    () => viewModel.segments.map((s) => s.coordinates as [number, number]),
    [viewModel.segments]
  );

  const { mapContainerRef, mapInstance, isMapReady, project } = useMapProjection({
    coordinates,
    viewMode,
  });

  const isPdf = viewMode === 'pdf';

  return (
    <div
      className={cn(
        'full-page-editorial-map relative w-full overflow-hidden select-none bg-[var(--color-surface)]',
        isPdf ? 'h-[1123px] min-h-[1123px] max-h-[1123px]' : 'h-[85vh] min-h-[640px] max-h-[960px] rounded-lg',
        className
      )}
    >
      {/* Background Geo Canvas */}
      <LuxuryMapGeoCanvas
        mapInstance={mapInstance}
        mapContainerRef={mapContainerRef}
        segments={viewModel.segments}
        mapColors={mapColors}
        activeSequence={activeSequence}
        isMapReady={isMapReady}
        tileStyle={isPdf ? 'carto-parchment-nolabels-pdf-v1' : 'google-classic-v1'}
        onRenderStateChange={onRenderStateChange}
      />

      {/* Floating Art Direction Overlays */}
      <MapFloatingOverlays
        viewModel={viewModel}
        typography={typography}
        project={project}
        activeSequence={activeSequence}
        onSegmentSelect={handleSelectSegment}
        viewMode={viewMode}
        pageNumber={pageNumber}
        quotationNumber={quotationNumber}
        quoteText={quoteText}
      />

      {/* Luxury Parchment Paper Vignette Overlay */}
      <div
        className="luxury-map-canvas-veil pointer-events-none absolute inset-0 z-5"
        aria-hidden="true"
      />
    </div>
  );
}

export default FullPageEditorialJourneyMap;
