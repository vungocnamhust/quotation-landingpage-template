'use client';

import React from 'react';
import type { RouteSegmentViewModel, TypographySlotMap } from '../../../display/types.ts';
import { textValue } from '../../../display/types.ts';
import type { ProjectedPoint, ResolvedMarkerPlacement, MarkerAnchorDirection } from './types.ts';
import { getTypographyClassName } from '../../../config/typography.ts';
import { requireTypographySlot } from '../../../display/typographySlots.ts';
import { cn } from '../../../utils/cn.ts';

interface MapDestinationMarkerProps {
  segment: RouteSegmentViewModel;
  index: number;
  projectedPoint: ProjectedPoint;
  isActive: boolean;
  typography: TypographySlotMap;
  placement?: ResolvedMarkerPlacement;
  onSelect?: (sequence: string) => void;
  isInteractive?: boolean;
  isPdf?: boolean;
}

export function MapDestinationMarker({
  segment,
  index,
  projectedPoint,
  isActive,
  typography,
  placement,
  onSelect,
  isInteractive = true,
  isPdf = false,
}: MapDestinationMarkerProps) {
  if (!projectedPoint.visible) {
    return null;
  }

  const cityName = textValue(segment.city);
  const titleSlot = requireTypographySlot(typography, 'metaPrimary');

  // In PDF mode, ALL markers are displayed with prominent standout accent highlight
  const isStandout = isPdf || isActive;

  // Direct badge text from explicit segment fields (dayStart/dayEnd or badgeLabel)
  const badgeText =
    segment.badgeLabel ||
    (segment.dayStart && segment.dayEnd
      ? segment.dayEnd > segment.dayStart
        ? `${segment.dayStart}-${segment.dayEnd}`
        : `${segment.dayStart}`
      : String(index + 1));

  const isMultiChar = badgeText.length > 1;
  const anchorDirection: MarkerAnchorDirection = placement?.anchorDirection || 'right';
  const isLeftAligned = anchorDirection === 'left' || anchorDirection === 'top-left' || anchorDirection === 'bottom-left';

  return (
    <div
      className={cn(
        'luxury-destination-marker absolute transition-transform duration-200 select-none',
        `luxury-destination-marker--${anchorDirection}`,
        isStandout ? 'is-active z-[525]' : 'z-[524] hover:scale-102'
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
          'luxury-destination-marker__content relative group',
          isInteractive ? 'cursor-pointer' : 'cursor-default'
        )}
      >
        {/* Direct Point Capsule: Badge is anchored directly at GPS coordinate (0, 0) */}
        <div
          className={cn(
            'luxury-destination-marker__pill flex items-center gap-1 px-1 py-0.5 rounded-full backdrop-blur-xs transition-all duration-200 whitespace-nowrap shadow-xs',
            isLeftAligned && 'flex-row-reverse',
            isPdf && 'luxury-destination-marker__pill--pdf',
            isStandout && 'border-[var(--color-accent)]'
          )}
          style={{
            // Anchors the badge center precisely at the geographic GPS coordinate (0, 0)
            transform: isLeftAligned ? 'translate(calc(-100% + 8px), -50%)' : 'translate(-8px, -50%)',
          }}
        >
          {/* Numbered Badge Dot (Exact GPS Point Center) */}
          <span
            className={cn(
              'luxury-destination-marker__badge flex items-center justify-center rounded-full font-mono transition-colors shrink-0 ring-1 ring-white/80',
              isMultiChar ? 'min-w-3.5 px-1 h-3' : 'w-3 h-3',
              getTypographyClassName('caption'),
              isStandout
                ? 'bg-[var(--color-accent)] text-white shadow-xs'
                : 'bg-[var(--color-primary)] text-white group-hover:bg-[var(--color-accent)]'
            )}
          >
            {badgeText}
          </span>

          {/* City Name (Single Line) */}
          <span
            className={cn(
              getTypographyClassName(titleSlot),
              'luxury-destination-marker__city font-serif transition-colors px-0.5',
              isStandout
                ? 'text-[var(--color-accent)]'
                : 'text-[var(--color-primary)] group-hover:text-[var(--color-accent)]'
            )}
          >
            {cityName}
          </span>
        </div>
      </div>
    </div>
  );
}
