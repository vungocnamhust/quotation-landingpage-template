'use client';

import React from 'react';
import type { RouteSegmentViewModel, TypographySlotMap } from '../../../display/types.ts';
import { textValue } from '../../../display/types.ts';
import type { ProjectedPoint } from './types.ts';
import { getTypographyClassName } from '../../../config/typography.ts';
import { requireTypographySlot } from '../../../display/typographySlots.ts';
import { cn } from '../../../utils/cn.ts';

interface MapDestinationMarkerProps {
  segment: RouteSegmentViewModel;
  index: number;
  projectedPoint: ProjectedPoint;
  isActive: boolean;
  typography: TypographySlotMap;
  onSelect?: (sequence: string) => void;
  isInteractive?: boolean;
}

export function MapDestinationMarker({
  segment,
  index,
  projectedPoint,
  isActive,
  typography,
  onSelect,
  isInteractive = true,
}: MapDestinationMarkerProps) {
  if (!projectedPoint.visible) {
    return null;
  }

  const cityName = textValue(segment.city);
  const dayLabel = textValue(segment.dayLabel) || `Day ${index + 1}`;

  const titleSlot = requireTypographySlot(typography, 'metaPrimary');
  const captionSlot = requireTypographySlot(typography, 'metaSecondary');

  return (
    <div
      className={cn(
        'luxury-destination-marker absolute -translate-x-1/2 -translate-y-full transition-transform duration-200',
        isActive && 'is-active scale-105 z-[525]',
        !isActive && 'z-[524] hover:scale-102'
      )}
      style={{
        left: `${projectedPoint.x}px`,
        top: `${projectedPoint.y}px`,
      }}
    >
      <div
        role={isInteractive ? 'button' : undefined}
        tabIndex={isInteractive ? 0 : undefined}
        onClick={() => {
          if (isInteractive && onSelect) {
            onSelect(segment.sequence);
          }
        }}
        onKeyDown={(e) => {
          if (isInteractive && onSelect && (e.key === 'Enter' || e.key === ' ')) {
            e.preventDefault();
            onSelect(segment.sequence);
          }
        }}
        className={cn(
          'luxury-destination-marker__content flex flex-col items-center group cursor-pointer text-center select-none',
          !isInteractive && 'cursor-default'
        )}
      >
        {/* Floating Capsule Label */}
        <div className="luxury-destination-marker__pill flex items-center gap-1.5 px-2.5 py-1 rounded-full backdrop-blur-xs transition-all duration-200">
          {/* Numbered Circle Dot */}
          <span
            className={cn(
              'luxury-destination-marker__badge flex items-center justify-center w-5 h-5 rounded-full font-mono transition-colors',
              getTypographyClassName('caption'),
              isActive
                ? 'bg-[var(--color-accent)] text-white shadow-sm'
                : 'bg-[var(--color-primary)] text-white group-hover:bg-[var(--color-accent)]'
            )}
          >
            {index + 1}
          </span>

          {/* City Name & Day Info */}
          <div className="flex flex-col items-start text-left">
            <span
              className={cn(
                getTypographyClassName(titleSlot),
                'luxury-destination-marker__city font-serif transition-colors',
                isActive
                  ? 'text-[var(--color-accent)]'
                  : 'text-[var(--color-primary)] group-hover:text-[var(--color-accent)]'
              )}
            >
              {cityName}
            </span>
            {dayLabel ? (
              <span
                className={cn(
                  getTypographyClassName(captionSlot),
                  'luxury-destination-marker__day text-[var(--color-on-surface-muted)]'
                )}
              >
                {dayLabel}
              </span>
            ) : null}
          </div>
        </div>

        {/* Pin Needle & Ground Dot */}
        <div className="luxury-destination-marker__pin flex flex-col items-center -mt-0.5">
          <div className="w-[1.5px] h-2.5 bg-[var(--color-accent)] opacity-80" />
          <div
            className={cn(
              'w-2 h-2 rounded-full border border-white shadow-xs transition-transform',
              isActive
                ? 'bg-[var(--color-accent)] ring-2 ring-[var(--color-accent)]/40'
                : 'bg-[var(--color-primary)]'
            )}
          />
        </div>
      </div>
    </div>
  );
}
