'use client';

import {
  createContext,
  startTransition,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import type { ThemeId, ViewMode } from '../display/contracts';
import {
  BRAND_PREFERENCE_KEY,
  type BrandInfo,
  type BrandKey,
  BRANDS_DATA,
  DEFAULT_BRAND_KEY,
} from '../data/brandsData';

interface BrandContextType {
  currentBrandKey: BrandKey;
  currentBrand: BrandInfo;
  themeId: ThemeId;
  previewViewMode: ViewMode | null;
  resolvedViewMode: ViewMode;
  setBrand: (brandKey: BrandKey) => void;
  setPreviewViewMode: (viewMode: ViewMode | null) => void;
  isInspectingTokens: boolean;
  setIsInspectingTokens: (open: boolean) => void;
}

const BrandContext = createContext<BrandContextType | undefined>(undefined);

function persistBrandPreference(brandKey: BrandKey) {
  localStorage.setItem(BRAND_PREFERENCE_KEY, brandKey);
  document.cookie = `${BRAND_PREFERENCE_KEY}=${brandKey}; path=/; max-age=31536000; samesite=lax`;
}

function resolveViewportMode() {
  if (typeof window === 'undefined') {
    return 'desktop' as const;
  }

  const datasetMode = document.documentElement.getAttribute('data-view-mode');
  if (datasetMode === 'desktop' || datasetMode === 'mobile' || datasetMode === 'pdf') {
    return datasetMode;
  }

  return window.matchMedia('(max-width: 767px)').matches ? 'mobile' : 'desktop';
}

export function BrandProvider({
  children,
  initialBrandKey = DEFAULT_BRAND_KEY,
  initialViewMode = null,
}: {
  children: ReactNode;
  initialBrandKey?: BrandKey;
  initialViewMode?: ViewMode | null;
}) {
  const [currentBrandKey, setCurrentBrandKey] = useState<BrandKey>(initialBrandKey);
  const [previewViewMode, setPreviewViewModeState] = useState<ViewMode | null>(initialViewMode);
  const [viewportViewMode, setViewportViewMode] = useState<ViewMode>(() => resolveViewportMode());
  const [isInspectingTokens, setIsInspectingTokens] = useState<boolean>(false);
  const themeId: ThemeId = 'brochure';
  const resolvedViewMode = previewViewMode ?? viewportViewMode;

  useEffect(() => {
    persistBrandPreference(currentBrandKey);
  }, [currentBrandKey]);

  useEffect(() => {
    if (previewViewMode) {
      return;
    }

    const syncViewportMode = () => {
      setViewportViewMode(resolveViewportMode());
    };

    const mediaQuery = window.matchMedia('(max-width: 767px)');
    mediaQuery.addEventListener('change', syncViewportMode);
    window.addEventListener('resize', syncViewportMode);

    return () => {
      mediaQuery.removeEventListener('change', syncViewportMode);
      window.removeEventListener('resize', syncViewportMode);
    };
  }, [previewViewMode]);

  useEffect(() => {
    document.documentElement.setAttribute('data-brand', currentBrandKey);
    document.documentElement.setAttribute('data-theme', themeId);
    document.documentElement.setAttribute('data-view-mode', resolvedViewMode);
  }, [currentBrandKey, resolvedViewMode, themeId]);

  const handleSetBrand = (brandKey: BrandKey) => {
    startTransition(() => {
      setCurrentBrandKey(brandKey);
    });
  };

  const handleSetPreviewViewMode = (viewMode: ViewMode | null) => {
    startTransition(() => {
      setPreviewViewModeState(viewMode);
    });
  };

  return (
    <BrandContext.Provider
      value={{
        currentBrandKey,
        currentBrand: BRANDS_DATA[currentBrandKey],
        themeId,
        previewViewMode,
        resolvedViewMode,
        setBrand: handleSetBrand,
        setPreviewViewMode: handleSetPreviewViewMode,
        isInspectingTokens,
        setIsInspectingTokens,
      }}
    >
      {children}
    </BrandContext.Provider>
  );
}

export function useBrand() {
  const context = useContext(BrandContext);
  if (!context) {
    throw new Error('useBrand must be used within a BrandProvider');
  }
  return context;
}
