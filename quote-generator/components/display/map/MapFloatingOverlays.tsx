import React from 'react';
import type { RouteMapViewModel, TypographySlotMap } from '../../../display/types.ts';
import { textValue } from '../../../display/types.ts';
import type { ViewMode } from '../../../display/contracts.ts';
import type { ProjectedPoint } from './types.ts';
import { MapGeoLabels } from './MapGeoLabels.tsx';
import { MapDestinationMarker } from './MapDestinationMarker.tsx';
import { BodyCopy, DisplayTitle, Kicker } from '../atoms.tsx';
import { getTypographyClassName } from '../../../config/typography.ts';
import { requireTypographySlot } from '../../../display/typographySlots.ts';
import { cn } from '../../../utils/cn.ts';

interface MapFloatingOverlaysProps {
  viewModel: RouteMapViewModel;
  typography: TypographySlotMap;
  project: (lat: number, lng: number) => ProjectedPoint;
  activeSequence?: string;
  onSegmentSelect?: (sequence: string) => void;
  viewMode: ViewMode;
  pageNumber?: string;
  quotationNumber?: string;
  quoteText?: string;
}

export function MapFloatingOverlays({
  viewModel,
  typography,
  project,
  activeSequence,
  onSegmentSelect,
  viewMode,
  pageNumber = '03',
}: MapFloatingOverlaysProps) {
  const isPdf = viewMode === 'pdf';

  const titleSlot = requireTypographySlot(typography, 'title');
  const bodySlot = requireTypographySlot(typography, 'body');
  const kickerSlot = requireTypographySlot(typography, 'kicker');

  // Compute summary stats for Route Summary
  const totalDestinations = viewModel.segments.length;
  const citiesSequence = viewModel.segments.map((s) => textValue(s.city)).filter(Boolean);

  return (
    <div className="luxury-map-floating-overlays pointer-events-none absolute inset-0 z-[500] flex flex-col justify-between p-6 sm:p-10 select-none">
      {/* ── TOP SECTION: Page Badge & Journey Header ── */}
      <div className="luxury-map-top-overlay flex items-start justify-between z-[510]">
        {/* Left Header Block (Floating on Map) */}
        <div className={cn(
          'luxury-map-header-block max-w-sm sm:max-w-md pointer-events-auto',
          isPdf && 'luxury-map-header-block--pdf'
        )}>
          {/* Page Index Badge */}
          <div className="flex items-center gap-2.5 mb-2.5">
            <div
              className={cn(
                'flex items-center justify-center border border-[var(--color-accent)]/60 px-2 py-0.5 rounded text-[var(--color-accent)]',
                getTypographyClassName('overline')
              )}
            >
              {pageNumber}
            </div>
            <span
              className={cn(
                'text-[var(--color-accent)]',
                getTypographyClassName('overline')
              )}
            >
              JOURNEY MAP
            </span>
          </div>

          {!isPdf ? (
            <div className="mb-1">
              <Kicker variant={kickerSlot} tone="accent">
                {viewModel.kicker || 'GEOGRAPHIC ROUTE'}
              </Kicker>
            </div>
          ) : null}

          {/* Title */}
          <div className="mb-1.5">
            <DisplayTitle as="h2" variant={titleSlot} className="luxury-map-title font-serif drop-shadow-xs">
              {viewModel.title}
            </DisplayTitle>
          </div>

          {/* Lede / Description */}
          {viewModel.description && textValue(viewModel.description) ? (
            <BodyCopy variant={bodySlot} className="luxury-map-lede max-w-sm text-[var(--color-on-surface-muted)] opacity-90 drop-shadow-xs">
              {viewModel.description}
            </BodyCopy>
          ) : null}
        </div>
      </div>

      {/* ── MID SECTION: Projected Geographic Elements & Markers ── */}
      <div className="luxury-map-mid-overlay pointer-events-auto absolute inset-0 z-[520]">
        <MapGeoLabels project={project} visibility={isPdf ? 'islands' : 'all'} />

        {/* Projected Destination Pins / Pills */}
        {viewModel.segments.map((segment, index) => {
          const pt = project(segment.coordinates[0], segment.coordinates[1]);
          return (
            <MapDestinationMarker
              key={segment.sequence || `marker-${index}`}
              segment={segment}
              index={index}
              projectedPoint={pt}
              isActive={activeSequence === segment.sequence}
              typography={typography}
              onSelect={onSegmentSelect}
              isInteractive={!isPdf}
              isPdf={isPdf}
            />
          );
        })}
      </div>

      {/* ── BOTTOM SECTION: Route Summary Flow (Clean without Quote Footer) ── */}
      <div className={cn(
        'luxury-map-bottom-overlay pointer-events-auto z-[530] flex flex-col items-center text-center mt-auto pt-4',
        isPdf && 'luxury-map-bottom-overlay--pdf'
      )}>
        {/* Subtle Decorative Hairline */}
        <div className="w-full max-w-xl h-[1px] bg-gradient-to-r from-transparent via-[var(--color-accent)]/40 to-transparent mb-3" />

        {/* Route City Flow Arrows */}
        {citiesSequence.length > 0 ? (
          <div className="luxury-map-route-flow flex flex-wrap items-center justify-center gap-1.5 sm:gap-2.5 mb-1.5">
            {citiesSequence.map((city, idx) => (
              <React.Fragment key={`city-flow-${idx}`}>
                <span
                  className={cn(
                    'luxury-map-flow-city font-serif text-[var(--color-primary)]',
                    getTypographyClassName('timelineTitle')
                  )}
                >
                  {city}
                </span>
                {idx < citiesSequence.length - 1 ? (
                  <span
                    className={cn(
                      'text-[var(--color-accent)] opacity-70',
                      getTypographyClassName('caption')
                    )}
                  >
                    →
                  </span>
                ) : null}
              </React.Fragment>
            ))}
          </div>
        ) : null}

        {/* Journey Summary Stats */}
        <div
          className={cn(
            'luxury-map-stats-line flex items-center justify-center gap-2 text-[var(--color-on-surface-muted)]',
            getTypographyClassName('caption')
          )}
        >
          <span>{totalDestinations} DESTINATIONS</span>
          <span>·</span>
          <span>CURATED LUXURY ITINERARY</span>
        </div>
      </div>
    </div>
  );
}
