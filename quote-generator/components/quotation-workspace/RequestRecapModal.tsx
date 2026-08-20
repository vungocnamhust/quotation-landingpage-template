"use client";

import { useEffect } from "react";
import Link from "next/link";
import { X, ExternalLink, ClipboardList } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import RequestRecapPanel from "./RequestRecapPanel.tsx";
import type { QuoteRequestItem } from "./factsTypes.ts";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  request: QuoteRequestItem | null;
};

export default function RequestRecapModal({ isOpen, onClose, request }: Props) {
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !request) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="request-recap-title"
      className="fixed inset-0 z-50 flex justify-end bg-black/50 backdrop-blur-xs transition-opacity duration-200"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="flex h-full w-full max-w-xl flex-col border-l border-[var(--color-border-strong)] bg-[var(--color-surface)] shadow-2xl animate-in slide-in-from-right duration-300">
        {/* Drawer Header */}
        <div className="flex items-center justify-between border-b border-[var(--color-border)] px-5 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--color-accent-wash)] text-[var(--color-accent)]">
              <ClipboardList size={18} />
            </div>
            <div>
              <h2
                id="request-recap-title"
                className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}
              >
                Inquiry Requirements Recap
              </h2>
              <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
                Original customer request and preferences
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close request recap drawer"
            className="flex h-9 w-9 items-center justify-center rounded-[var(--radius-button)] text-[var(--color-muted)] hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-on-surface)] transition-colors cursor-pointer"
          >
            <X size={20} />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-5">
          <RequestRecapPanel request={request} className="shadow-none border-0 p-0" />
        </div>

        {/* Drawer Footer */}
        <div className="flex items-center justify-between border-t border-[var(--color-border)] bg-[var(--color-surface-muted)] px-5 py-3.5">
          <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
            Request #{request.id.slice(0, 12)}…
          </span>

          <Link
            href={`/workspace/requests/${request.id}`}
            target="_blank"
            rel="noopener noreferrer"
            className={cn(
              getTypographyClassName("buttonSecondary"),
              "flex items-center gap-1.5 min-h-9 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1 text-[var(--color-on-surface)] hover:bg-[var(--color-surface-muted)] shadow-xs transition-colors"
            )}
          >
            <span>Open Original Request</span>
            <ExternalLink size={14} className="text-[var(--color-muted)]" />
          </Link>
        </div>
      </div>
    </div>
  );
}
