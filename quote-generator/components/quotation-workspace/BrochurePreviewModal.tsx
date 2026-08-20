"use client";

import { useEffect } from "react";
import type { DisplayDocument } from "../../display/runtimePageBuilder.ts";
import type { ViewMode } from "../../display/contracts.ts";
import IsolatedPreviewCanvas, { type DevicePreset } from "../preview/IsolatedPreviewCanvas.tsx";

export interface BrochurePreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  documentModel: DisplayDocument;
  initialViewMode?: ViewMode;
  publishedUrl?: string | null;
}

export default function BrochurePreviewModal({
  isOpen,
  onClose,
  documentModel,
  initialViewMode = "desktop",
  publishedUrl,
}: BrochurePreviewModalProps) {
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const initialPreset: DevicePreset =
    initialViewMode === "mobile" ? "mobile" : initialViewMode === "pdf" ? "pdf" : "desktop";

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Brochure Multi-Device Live Preview"
      className="fixed inset-0 z-[10000] flex flex-col bg-black/90 backdrop-blur-md text-white overflow-hidden animate-in fade-in duration-200"
    >
      <IsolatedPreviewCanvas
        documentModel={documentModel}
        initialDevicePreset={initialPreset}
        publishedUrl={publishedUrl}
        onClose={onClose}
        showControlDock={true}
      />
    </div>
  );
}

