"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type ZoomLevel = "fit" | 0.5 | 0.75 | 1;

export interface UseViewportScaleOptions {
  targetWidth?: number;
  padding?: number;
  initialZoom?: ZoomLevel;
  enabled?: boolean;
}

export interface ViewportScaleState {
  scale: number;
  zoom: ZoomLevel;
  setZoom: (zoom: ZoomLevel) => void;
  containerRef: React.RefObject<HTMLDivElement | null>;
  containerWidth: number;
  containerHeight: number;
}

export function useViewportScale({
  targetWidth = 1920,
  padding = 32,
  initialZoom = "fit",
  enabled = true,
}: UseViewportScaleOptions = {}): ViewportScaleState {
  const containerRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState<ZoomLevel>(initialZoom);
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });

  const updateDimensions = useCallback(
    (entry?: ResizeObserverEntry) => {
      if (entry) {
        const { width, height } = entry.contentRect;
        setContainerSize((prev) => {
          if (Math.abs(prev.width - width) < 1 && Math.abs(prev.height - height) < 1) {
            return prev;
          }
          return { width, height };
        });
      } else if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setContainerSize((prev) => {
          if (Math.abs(prev.width - rect.width) < 1 && Math.abs(prev.height - rect.height) < 1) {
            return prev;
          }
          return { width: rect.width, height: rect.height };
        });
      }
    },
    []
  );

  useEffect(() => {
    if (!enabled) return;

    const el = containerRef.current;
    if (!el) return;

    updateDimensions();

    let observer: ResizeObserver | null = null;
    if (typeof ResizeObserver !== "undefined") {
      observer = new ResizeObserver((entries) => {
        if (entries[0]) {
          updateDimensions(entries[0]);
        }
      });
      observer.observe(el);
    }

    const handleWindowResize = () => {
      updateDimensions();
    };
    window.addEventListener("resize", handleWindowResize);

    return () => {
      if (observer) {
        observer.disconnect();
      }
      window.removeEventListener("resize", handleWindowResize);
    };
  }, [enabled, updateDimensions]);

  let scale = 1;
  if (enabled && targetWidth > 0) {
    if (zoom === "fit") {
      if (containerSize.width > 0) {
        const availableWidth = Math.max(containerSize.width - padding, 320);
        scale = Math.min(availableWidth / targetWidth, 1);
      } else {
        scale = 1;
      }
    } else {
      scale = zoom;
    }
  }

  return {
    scale,
    zoom,
    setZoom,
    containerRef,
    containerWidth: containerSize.width,
    containerHeight: containerSize.height,
  };
}
