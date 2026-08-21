'use client';

import { useEffect } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useBrand } from '../context/BrandContext.tsx';
import { BRANDS_DATA, type BrandKey } from '../data/brandsData.ts';
import type { ViewMode } from '../display/contracts.ts';

const PREVIEW_MODES: Array<{ value: ViewMode | null; label: string }> = [
  { value: null, label: 'Auto' },
  { value: 'desktop', label: 'Desktop' },
  { value: 'mobile', label: 'Mobile' },
  { value: 'pdf', label: 'PDF' },
];

export default function BrandSwitcherHeader() {
  const {
    currentBrandKey,
    setBrand,
    previewViewMode,
    resolvedViewMode,
    setPreviewViewMode,
    isInspectingTokens,
    setIsInspectingTokens,
  } = useBrand();
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();

  const brands: { key: BrandKey; name: string; icon: string; tag: string }[] = [
    { key: 'vietnam-safar', name: 'Vietnam Safar', icon: '🌿', tag: 'Relaxed Escapes' },
    { key: 'capella-travel', name: 'Capella Travel', icon: '👑', tag: 'Premium Heritage' },
    { key: 'selvara', name: 'Selvara', icon: '🧘', tag: 'Luxury Slow Travel' },
  ];

  useEffect(() => {
    const viewParam = searchParams.get('view');
    if (viewParam === 'desktop' || viewParam === 'mobile' || viewParam === 'pdf') {
      setPreviewViewMode(viewParam);
      return;
    }
    setPreviewViewMode(null);
  }, [searchParams, setPreviewViewMode]);

  const updateViewParam = (viewMode: ViewMode | null) => {
    const params = new URLSearchParams(searchParams.toString());
    if (viewMode) {
      params.set('view', viewMode);
    } else {
      params.delete('view');
    }
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  };

  return (
    <div className="sticky top-0 z-50 w-full border-b border-white/10 bg-black/88 px-4 py-3 text-white backdrop-blur-xl">
      <div className="mx-auto grid max-w-[76rem] gap-3 lg:grid-cols-[1fr_auto_auto] lg:items-center">
        <div className="flex flex-wrap items-center gap-3">
          <span className="inline-flex h-2.5 w-2.5 rounded-full bg-emerald-400" />
          <div className="flex flex-wrap items-center gap-2">
            <span className="typo-overline text-gray-400">Display System:</span>
            <span className="typo-body-sm text-amber-300">
              {BRANDS_DATA[currentBrandKey].name}
            </span>
            <span className="typo-caption text-gray-400">
              {BRANDS_DATA[currentBrandKey].tagline}
            </span>
            <span className="typo-caption rounded-full border border-white/10 px-2 py-1 text-gray-300">
              {previewViewMode ? `Preview ${previewViewMode}` : `Auto ${resolvedViewMode}`}
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 rounded-full border border-white/10 bg-white/10 p-1">
          {brands.map((brand) => {
            const isActive = currentBrandKey === brand.key;
            return (
              <button
                key={brand.key}
                type="button"
                onClick={() => setBrand(brand.key)}
                className={`typo-caption inline-flex min-h-11 items-center gap-2 rounded-full px-3.5 py-2 transition-all ${
                  isActive
                    ? 'bg-amber-500 text-black shadow-lg'
                    : 'text-gray-300 hover:bg-white/10 hover:text-white'
                }`}
              >
                <span>{brand.icon}</span>
                <span>{brand.name}</span>
              </button>
            );
          })}
        </div>

        <div className="flex flex-wrap items-center justify-start gap-2 lg:justify-end">
          <div className="flex items-center gap-1 rounded-full border border-white/10 bg-white/10 p-1">
            {PREVIEW_MODES.map((mode) => {
              const active = (mode.value ?? resolvedViewMode) === (previewViewMode ?? resolvedViewMode)
                && (mode.value === previewViewMode || (!previewViewMode && mode.value === null));

              return (
                <button
                  key={mode.label}
                  type="button"
                  onClick={() => updateViewParam(mode.value)}
                  className={`typo-caption inline-flex min-h-11 items-center rounded-full px-3 py-2 transition-all ${
                    active
                      ? 'bg-white text-black'
                      : 'text-gray-300 hover:bg-white/10 hover:text-white'
                  }`}
                >
                  {mode.label}
                </button>
              );
            })}
          </div>
          <button
            type="button"
            onClick={() => setIsInspectingTokens(!isInspectingTokens)}
            className="typo-button-secondary inline-flex min-h-11 items-center gap-2 rounded-lg border border-amber-400/30 bg-amber-500/20 px-3 py-2 text-amber-200 transition-all hover:bg-amber-500/30"
          >
            <span>{isInspectingTokens ? 'Hide Spec' : 'Theme Spec'}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
