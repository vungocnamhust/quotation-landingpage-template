"use client";

import { useEffect, useRef } from "react";
import dynamic from "next/dynamic";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import type { MediaPickerContext } from "./MediaPicker.tsx";

const MediaPicker = dynamic(() => import("./MediaPicker"), {
  loading: () => (
    <div className="min-h-[32rem] animate-pulse rounded-[var(--radius-card)] bg-[var(--color-surface-muted)]" />
  ),
});

export default function MediaDrawer({
  open,
  onClose,
  onSelect,
  onConfirm,
  context,
  selectionMode = 'single',
  maxSelection = 1,
  initialSelection = [],
}: {
  open: boolean;
  onClose: () => void;
  onSelect?: (r2Key: string) => void;
  onConfirm?: (r2Keys: string[]) => void;
  context?: MediaPickerContext;
  selectionMode?: 'single' | 'multiple';
  maxSelection?: number;
  initialSelection?: string[];
}) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const drawerRef = useRef<HTMLElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (!open) return;
    previousFocusRef.current =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
        return;
      }
      if (event.key !== "Tab" || !drawerRef.current) return;
      const focusable = [
        ...drawerRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      ];
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      }
      if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      previousFocusRef.current?.focus();
    };
  }, [onClose, open]);
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-[color-mix(in_srgb,var(--color-contrast)_38%,transparent)] backdrop-blur-sm"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        ref={drawerRef}
        role="dialog"
        aria-modal="true"
        aria-label="Media library"
        className="media-drawer flex h-full w-full max-w-3xl flex-col overflow-y-auto border-l border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] sm:p-7"
      >
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <h2
              className={cn(
                getTypographyClassName("cardTitle"),
                "text-[var(--color-on-surface)]",
              )}
            >
              Choose quotation media
            </h2>
            <p
              className={cn(
                getTypographyClassName("bodySm"),
                "mt-1 text-[var(--color-muted)]",
              )}
            >
              This selection is saved to the canonical quotation document.
            </p>
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            className={cn(
              getTypographyClassName("buttonSecondary"),
              "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border)] px-4 text-[var(--color-on-surface)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)]",
            )}
          >
            Close
          </button>
        </div>
        <MediaPicker onSelect={onSelect} onConfirm={onConfirm} context={context} selectionMode={selectionMode} maxSelection={maxSelection} initialSelection={initialSelection} />
      </section>
    </div>
  );
}
