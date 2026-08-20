"use client";

import { Monitor, Smartphone, FileText, Eye, Palette } from "lucide-react";
import type { ViewMode } from "../../display/contracts.ts";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";

export interface DesignPreviewToolbarProps {
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  onOpenPreview: () => void;
  themeName?: string;
}

export default function DesignPreviewToolbar({
  viewMode,
  onViewModeChange,
  onOpenPreview,
  themeName = "Brochure",
}: DesignPreviewToolbarProps) {
  const modes: Array<{ id: ViewMode; label: string; icon: React.ComponentType<{ size?: number; className?: string }> }> = [
    { id: "desktop", label: "Desktop", icon: Monitor },
    { id: "mobile", label: "Mobile", icon: Smartphone },
    { id: "pdf", label: "PDF Print", icon: FileText },
  ];

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-3 shadow-2xs">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-1.5 text-[var(--color-muted)]">
          <Palette size={15} aria-hidden="true" />
          <span className={cn(getTypographyClassName("caption"))}>
            {themeName} Theme
          </span>
        </div>

        {/* Segmented View Mode Toggle */}
        <div
          role="group"
          aria-label="Design view mode selector"
          className="flex items-center gap-1 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-1"
        >
          {modes.map((mode) => {
            const Icon = mode.icon;
            const isActive = viewMode === mode.id;
            return (
              <button
                key={mode.id}
                type="button"
                aria-pressed={isActive}
                onClick={() => onViewModeChange(mode.id)}
                className={cn(
                  getTypographyClassName("buttonSecondary"),
                  "flex items-center gap-1.5 min-h-8 rounded-[calc(var(--radius-button)-2px)] px-3 py-1 transition-all cursor-pointer",
                  isActive
                    ? "border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] shadow-2xs"
                    : "border border-transparent text-[var(--color-muted)] hover:text-[var(--color-on-surface)] hover:bg-[var(--color-surface)]/50"
                )}
              >
                <Icon size={14} aria-hidden="true" />
                <span>{mode.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Primary Preview CTA Button */}
      <button
        type="button"
        onClick={onOpenPreview}
        className={cn(
          getTypographyClassName("buttonPrimary"),
          "flex items-center gap-2 min-h-10 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-4 py-2 shadow-sm transition-all cursor-pointer"
        )}
      >
        <Eye size={16} aria-hidden="true" />
        <span>Full-Screen Preview</span>
      </button>
    </div>
  );
}
