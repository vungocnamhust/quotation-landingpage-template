'use client';

import { useEffect } from 'react';
import type { ViewMode } from '../display/contracts.ts';
import { useBrand } from '../context/BrandContext.tsx';

export default function ForceViewMode({ value }: { value: ViewMode }) {
  const { setPreviewViewMode } = useBrand();

  useEffect(() => {
    setPreviewViewMode(value);
    return () => {
      setPreviewViewMode(null);
    };
  }, [setPreviewViewMode, value]);

  return null;
}
