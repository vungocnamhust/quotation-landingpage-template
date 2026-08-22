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

function getCapsuleTransform(anchor: MarkerAnchorDirection): string {
  switch (anchor) {
    case 'top-center':
    case 'top-elevated':
      return 'translate(-50%, -100%)';
    case 'top-left':
      return 'translate(-100%, -100%)';
    case 'top-right':
      return 'translate(0%, -100%)';
    case 'left':
      return 'translate(-100%, -50%)';
    case 'right':
      return 'translate(0%, -50%)';
    case 'bottom-left':
      return 'translate(-100%, 0%)';
    case 'bottom-right':
      return 'translate(0%, 0%)';
    case 'bottom-center':
      return 'translate(-50%, 0%)';
    default:
      return 'translate(-50%, -100%)';
  }
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
  const dayLabel = textValue(segment.dayLabel) || `Day ${index + 1}`;

  const titleSlot = requireTypographySlot(typography, 'metaPrimary');
  const captionSlot = requireTypographySlot(typography, 'metaSecondary');

  const anchorDirection: MarkerAnchorDirection = placement?.anchorDirection || 'top-center';
  const stemOffset = placement?.stemOffset || { x: 0, y: -10 };

  const minX = Math.min(0, stemOffset.x) - 4;
  const maxX = Math.max(0, stemOffset.x) + 4;
  const minY = Math.min(0, stemOffset.y) - 4;
  const maxY = Math.max(0, stemOffset.y) + 4;
  const svgWidth = Math.max(8, maxX - minX);
  const svgHeight = Math.max(8, maxY - minY);

  const capsuleTransform = getCapsuleTransform(anchorDirection);

  return (
    <div
      className={cn(
        'luxury-destination-marker absolute transition-transform duration-200',
        `luxury-destination-marker--${anchorDirection}`,
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
          'luxury-destination-marker__content relative group cursor-pointer select-none',
          !isInteractive && 'cursor-default'
        )}
      >
        {/* Leader Line / Needle Stem */}
        <svg
          className="luxury-destination-marker__stem pointer-events-none absolute overflow-visible"
          style={{
            left: `${minX}px`,
            top: `${minY}px`,
            width: `${svgWidth}px`,
            height: `${svgHeight}px`,
          }}
          viewBox={`${minX} ${minY} ${svgWidth} ${svgHeight}`}
          aria-hidden="true"
        >
          <line
            x1={0}
            y1={0}
            x2={stemOffset.x}
            y2={stemOffset.y}
            stroke="var(--color-accent)"
            strokeWidth={1.5}
            strokeLinecap="round"
            className="transition-colors duration-200 opacity-85"
          />
        </svg>

        {/* Geographic Ground Dot (Exact GPS Coordinate Center) */}
        <div
          className={cn(
            'luxury-destination-marker__ground-dot absolute left-0 top-0 -translate-x-1/2 -translate-y-1/2 w-2 h-2 rounded-full border border-white shadow-xs transition-transform',
            isActive
              ? 'bg-[var(--color-accent)] ring-2 ring-[var(--color-accent)]/40'
              : 'bg-[var(--color-primary)]'
          )}
          aria-hidden="true"
        />

        {/* Floating Capsule Label */}
        <div
          className="luxury-destination-marker__capsule-wrapper absolute"
          style={{
            left: `${stemOffset.x}px`,
            top: `${stemOffset.y}px`,
            transform: capsuleTransform,
          }}
        >
          <div
            className={cn(
              'luxury-destination-marker__pill flex items-center gap-1.5 px-2.5 py-1 rounded-full backdrop-blur-xs transition-all duration-200 whitespace-nowrap',
              isPdf && 'luxury-destination-marker__pill--pdf'
            )}
          >
            {/* Numbered Circle Dot */}
            <span
              className={cn(
                'luxury-destination-marker__badge flex items-center justify-center w-5 h-5 rounded-full font-mono transition-colors shrink-0',
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
        </div>
      </div>
    </div>
  );
}
