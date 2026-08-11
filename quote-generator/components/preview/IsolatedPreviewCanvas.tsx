"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { X, Monitor, Tablet, Smartphone, FileText, ExternalLink, Minimize2, Maximize2 } from "lucide-react";
import type { DisplayDocument } from "../../display/runtimePageBuilder";
import type { ViewMode } from "../../display/contracts";
import DisplayPage from "../DisplayPage";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";

export type DevicePreset = "desktop" | "tablet" | "mobile" | "pdf";

export interface IsolatedPreviewFrameProps {
  devicePreset: DevicePreset;
  children: React.ReactNode;
  className?: string;
  onClose?: () => void;
}

export function IsolatedPreviewFrame({
  devicePreset,
  children,
  className,
}: IsolatedPreviewFrameProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [iframeMounted, setIframeMounted] = useState(false);

  const [mountNode, setMountNode] = useState<HTMLElement | null>(null);

  useEffect(() => {
    const iframe = iframeRef.current;
    if (!iframe) return;

    const doc = iframe.contentDocument;
    if (!doc) return;

    // Build iframe document structure
    doc.open();
    doc.write(`
      <!DOCTYPE html>
      <html lang="en">
        <head>
          <meta charset="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
        </head>
        <body style="margin: 0; padding: 0; background: transparent; overflow-x: hidden;">
          <div id="preview-root"></div>
        </body>
      </html>
    `);
    doc.close();

    // Sync styles from main document head to iframe head
    const parentStyles = Array.from(
      document.querySelectorAll('style, link[rel="stylesheet"]')
    );
    parentStyles.forEach((node) => {
      doc.head.appendChild(node.cloneNode(true));
    });

    // Copy body dataset and class list for brand/theme inheritance
    doc.body.className = document.body.className;
    Array.from(document.body.attributes).forEach((attr) => {
      if (attr.name.startsWith("data-") || attr.name === "class") {
        doc.body.setAttribute(attr.name, attr.value);
      }
    });

    const rootNode = doc.getElementById("preview-root");
    setMountNode(rootNode);
    setIframeMounted(true);

    // Dynamic style observer to sync newly injected styles (e.g. Next.js HMR or dynamic CSS)
    const observer = new MutationObserver(() => {
      const currentParentStyles = Array.from(
        document.querySelectorAll('style, link[rel="stylesheet"]')
      );
      currentParentStyles.forEach((node) => {
        const identifier = node.textContent || (node as HTMLLinkElement).href;
        const exists = Array.from(doc.head.children).some(
          (child) => child.textContent === node.textContent || (child as HTMLLinkElement).href === (node as HTMLLinkElement).href
        );
        if (!exists && identifier) {
          doc.head.appendChild(node.cloneNode(true));
        }
      });
    });

    observer.observe(document.head, { childList: true, subtree: true });

    return () => {
      observer.disconnect();
    };
  }, [devicePreset]);

  return (
    <div
      className={cn(
        "transition-all duration-300 ease-out bg-[var(--color-surface)] text-[var(--color-on-surface)] overflow-hidden shadow-2xl flex flex-col h-full",
        devicePreset === "mobile"
          ? "w-[375px] my-4 rounded-[36px] border-[10px] border-neutral-800 ring-1 ring-white/10 min-h-[720px] max-h-[92vh]"
          : devicePreset === "tablet"
          ? "w-[768px] my-4 rounded-2xl border-4 border-neutral-800 ring-1 ring-white/10 min-h-[900px] max-h-[95vh]"
          : devicePreset === "pdf"
          ? "w-[800px] my-4 rounded-md border border-neutral-700 min-h-[1100px]"
          : "w-full max-w-6xl my-2 rounded-xl border border-neutral-800 h-full",
        className
      )}
    >
      <iframe
        ref={iframeRef}
        title={`Live Preview Canvas (${devicePreset})`}
        className="w-full h-full min-h-[680px] border-none block"
      />
      {iframeMounted && mountNode ? createPortal(children, mountNode) : null}
    </div>
  );
}

export interface IsolatedPreviewDockProps {
  activeDevice: DevicePreset;
  onDeviceChange: (device: DevicePreset) => void;
  onClose?: () => void;
  publishedUrl?: string | null;
}

export function IsolatedPreviewDock({
  activeDevice,
  onDeviceChange,
  onClose,
  publishedUrl,
}: IsolatedPreviewDockProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  const devicePresets: Array<{ id: DevicePreset; label: string; icon: React.ComponentType<{ size?: number; className?: string }> }> = [
    { id: "desktop", label: "Desktop (1920px)", icon: Monitor },
    { id: "tablet", label: "Tablet (768px)", icon: Tablet },
    { id: "mobile", label: "Mobile (375px)", icon: Smartphone },
    { id: "pdf", label: "PDF Print (A4)", icon: FileText },
  ];

  const activePreset = devicePresets.find((p) => p.id === activeDevice) ?? devicePresets[0];
  const ActiveIcon = activePreset.icon;

  if (isCollapsed) {
    return (
      <div className="fixed top-4 right-4 z-[10001] flex items-center gap-2 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-2 shadow-2xl backdrop-blur-md animate-in fade-in duration-200">
        <button
          type="button"
          onClick={() => setIsCollapsed(false)}
          title="Expand live preview controls"
          className={cn(
            getTypographyClassName("caption"),
            "flex items-center gap-2 rounded-[var(--radius-button)] bg-[var(--color-surface-muted)] px-3 py-1.5 text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] transition-all cursor-pointer"
          )}
        >
          <ActiveIcon size={14} />
          <span>{activePreset.label}</span>
          <Maximize2 size={12} className="ml-1 text-[var(--color-muted)]" />
        </button>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Close preview"
            className="flex h-7 w-7 items-center justify-center rounded-[var(--radius-button)] text-[var(--color-muted)] hover:bg-rose-500/15 hover:text-rose-600 transition-colors cursor-pointer"
          >
            <X size={14} />
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="fixed top-4 right-4 z-[10001] flex flex-col gap-3 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-4 shadow-2xl backdrop-blur-md max-w-xs text-[var(--color-on-surface)] animate-in fade-in zoom-in-95 duration-200">
      {/* Dock Header */}
      <div className="flex items-center justify-between gap-3 border-b border-[var(--color-border)] pb-2.5">
        <span className={cn(getTypographyClassName("overline"), "text-[var(--color-muted)]")}>
          LIVE PREVIEW DOCK
        </span>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setIsCollapsed(true)}
            title="Collapse dock"
            className="flex h-7 w-7 items-center justify-center rounded-[var(--radius-button)] text-[var(--color-muted)] hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-on-surface)] transition-colors cursor-pointer"
          >
            <Minimize2 size={14} />
          </button>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              title="Close preview"
              className="flex h-7 w-7 items-center justify-center rounded-[var(--radius-button)] text-[var(--color-muted)] hover:bg-rose-500/15 hover:text-rose-600 transition-colors cursor-pointer"
            >
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Device Presets List */}
      <div className="flex flex-col gap-1.5" role="group" aria-label="Device viewports">
        {devicePresets.map((preset) => {
          const Icon = preset.icon;
          const isActive = activeDevice === preset.id;
          return (
            <button
              key={preset.id}
              type="button"
              aria-pressed={isActive}
              onClick={() => onDeviceChange(preset.id)}
              className={cn(
                getTypographyClassName("buttonSecondary"),
                "group flex items-center justify-between min-h-10 w-full rounded-[var(--radius-button)] px-3.5 py-2 text-left transition-all duration-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)] cursor-pointer",
                isActive
                  ? "border border-[var(--color-border-strong)] bg-[var(--color-accent-wash)] text-[var(--color-on-surface)] shadow-2xs"
                  : "border border-transparent text-[var(--color-muted)] hover:bg-[color-mix(in_srgb,var(--color-accent-wash)_35%,transparent)] hover:border-[var(--color-border-strong)] hover:text-[var(--color-on-surface)]"
              )}
            >
              <span className="flex items-center gap-2 min-w-0 truncate">
                <Icon size={14} className="shrink-0" />
                <span className="truncate">{preset.label}</span>
              </span>
            </button>
          );
        })}
      </div>

      {publishedUrl ? (
        <a
          href={publishedUrl}
          target="_blank"
          rel="noopener noreferrer"
          className={cn(
            getTypographyClassName("caption"),
            "flex items-center justify-center gap-1.5 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] py-2 text-[var(--color-muted)] hover:text-[var(--color-on-surface)] hover:bg-[var(--color-surface-hover)] transition-colors"
          )}
        >
          <ExternalLink size={12} />
          <span>Open Public URL</span>
        </a>
      ) : null}
    </div>
  );
}

export interface IsolatedPreviewCanvasProps {
  documentModel: DisplayDocument;
  initialDevicePreset?: DevicePreset;
  publishedUrl?: string | null;
  onClose?: () => void;
  showControlDock?: boolean;
}

export default function IsolatedPreviewCanvas({
  documentModel,
  initialDevicePreset = "desktop",
  publishedUrl,
  onClose,
  showControlDock = true,
}: IsolatedPreviewCanvasProps) {
  const [device, setDevice] = useState<DevicePreset>(initialDevicePreset);

  const resolvedViewMode: ViewMode = device === "pdf" ? "pdf" : device === "mobile" ? "mobile" : "desktop";

  return (
    <div className="relative flex flex-col items-center justify-start w-full h-full min-h-screen bg-neutral-950 p-4 sm:p-6 overflow-y-auto">
      {showControlDock && (
        <IsolatedPreviewDock
          activeDevice={device}
          onDeviceChange={setDevice}
          onClose={onClose}
          publishedUrl={publishedUrl}
        />
      )}

      <IsolatedPreviewFrame devicePreset={device}>
        <DisplayPage documentModel={{ ...documentModel, viewMode: resolvedViewMode }} />
      </IsolatedPreviewFrame>
    </div>
  );
}

// Attach subcomponents for Composite Component Pattern (<IsolatedPreviewCanvas.Frame />, <IsolatedPreviewCanvas.Dock />)
IsolatedPreviewCanvas.Frame = IsolatedPreviewFrame;
IsolatedPreviewCanvas.Dock = IsolatedPreviewDock;
