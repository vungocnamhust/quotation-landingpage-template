import React from 'react';
import type { GeoLocationLabel, ProjectedPoint } from './types.ts';
import { getTypographyClassName } from '../../../config/typography.ts';
import { cn } from '../../../utils/cn.ts';

export const CANONICAL_GEO_LABELS: GeoLocationLabel[] = [
  // Countries
  { id: 'geo-vietnam', name: 'VIETNAM', coordinates: [16.2, 107.8], type: 'country' },
  { id: 'geo-laos', name: 'LAOS', coordinates: [18.2, 103.8], type: 'country' },
  { id: 'geo-cambodia', name: 'CAMBODIA', coordinates: [12.6, 104.8], type: 'country' },
  { id: 'geo-thailand', name: 'THAILAND', coordinates: [15.2, 101.2], type: 'country' },
  { id: 'geo-china', name: 'CHINA', coordinates: [25.2, 112.5], type: 'country' },

  // Seas & Gulfs
  {
    id: 'geo-east-sea',
    name: 'BIỂN ĐÔNG',
    subName: 'East Sea',
    coordinates: [14.2, 112.5],
    type: 'sea',
  },
  {
    id: 'geo-tonkin',
    name: 'VỊNH BẮC BỘ',
    subName: 'Gulf of Tonkin',
    coordinates: [19.8, 107.3],
    type: 'sea',
  },
  {
    id: 'geo-thailand-gulf',
    name: 'VỊNH THÁI LAN',
    subName: 'Gulf of Thailand',
    coordinates: [9.5, 101.8],
    type: 'sea',
  },

  // Archipelagos (Hoang Sa & Truong Sa)
  {
    id: 'geo-hoang-sa',
    name: 'Q.Đ HOÀNG SA',
    subName: 'Paracel Islands (Vietnam)',
    coordinates: [16.5, 112.0],
    type: 'island',
    sovereignty: 'Vietnam',
  },
  {
    id: 'geo-truong-sa',
    name: 'Q.Đ TRƯỜNG SA',
    subName: 'Spratly Islands (Vietnam)',
    coordinates: [9.0, 114.5],
    type: 'island',
    sovereignty: 'Vietnam',
  },
];

interface MapGeoLabelsProps {
  project: (lat: number, lng: number) => ProjectedPoint;
  visibility?: 'all' | 'islands';
}

export function MapGeoLabels({ project, visibility = 'all' }: MapGeoLabelsProps) {
  return (
    <div className="luxury-map-geo-labels pointer-events-none absolute inset-0 select-none overflow-hidden" aria-hidden="true">
      {/* Projected Geographic Labels */}
      {CANONICAL_GEO_LABELS.map((item) => {
        if (visibility === 'islands' && item.type !== 'island') return null;
        const pt = project(item.coordinates[0], item.coordinates[1]);
        if (!pt.visible) return null;

        if (item.type === 'country') {
          return (
            <div
              key={item.id}
              className="luxury-geo-label luxury-geo-label--country absolute -translate-x-1/2 -translate-y-1/2"
              style={{ left: `${pt.x}px`, top: `${pt.y}px` }}
            >
              <span
                className={cn(
                  'luxury-geo-label__country-text font-serif text-[var(--color-on-surface-muted)] opacity-70',
                  getTypographyClassName('overline')
                )}
              >
                {item.name}
              </span>
            </div>
          );
        }

        if (item.type === 'sea') {
          return (
            <div
              key={item.id}
              className="luxury-geo-label luxury-geo-label--sea absolute -translate-x-1/2 -translate-y-1/2 text-center"
              style={{ left: `${pt.x}px`, top: `${pt.y}px` }}
            >
              <div
                className={cn(
                  'luxury-geo-label__sea-name font-serif text-[var(--color-accent)] opacity-85',
                  getTypographyClassName('caption')
                )}
              >
                [{item.name}]
              </div>
              {item.subName ? (
                <div
                  className={cn(
                    'luxury-geo-label__sea-sub font-serif text-[var(--color-on-surface-muted)] opacity-75',
                    getTypographyClassName('caption')
                  )}
                >
                  {item.subName}
                </div>
              ) : null}
            </div>
          );
        }

        if (item.type === 'island') {
          return (
            <div
              key={item.id}
              className="luxury-geo-label luxury-geo-label--island absolute -translate-x-1/2 -translate-y-1/2 text-center"
              style={{ left: `${pt.x}px`, top: `${pt.y}px` }}
            >
              <div className="flex items-center justify-center gap-1">
                <span className="text-[var(--color-accent)]">★</span>
                <span
                  className={cn(
                    'luxury-geo-label__island-name font-serif text-[var(--color-primary)]',
                    getTypographyClassName('caption')
                  )}
                >
                  {item.name}
                </span>
              </div>
              {item.subName ? (
                <div
                  className={cn(
                    'luxury-geo-label__island-sub text-[var(--color-on-surface-muted)] opacity-90',
                    getTypographyClassName('caption')
                  )}
                >
                  {item.subName}
                </div>
              ) : null}
            </div>
          );
        }

        return null;
      })}
    </div>
  );
}
