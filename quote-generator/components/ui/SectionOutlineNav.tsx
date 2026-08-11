"use client";

import { CheckCircle2, AlertCircle, Circle } from "lucide-react";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";

export interface SectionOutlineItem {
  id: string;
  label: string;
  isSelected: boolean;
  isComplete?: boolean;
  status?: "can_thong_tin" | "chua_du_noi_dung" | null;
  badge?: {
    text: string;
    variant?: "draft" | "warning";
  };
}

export interface SectionOutlineNavProps {
  title: string;
  completedCount: number;
  totalCount: number;
  counterLabel?: string;
  items: SectionOutlineItem[];
  onSelect: (id: string) => void;
  ariaLabel?: string;
  footer?: React.ReactNode;
  className?: string;
}

export default function SectionOutlineNav({
  title,
  completedCount,
  totalCount,
  counterLabel = "ready",
  items,
  onSelect,
  ariaLabel,
  footer,
  className,
}: SectionOutlineNavProps) {
  return (
    <aside
      className={cn(
        "rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 flex flex-col gap-3",
        className
      )}
      aria-label={ariaLabel ?? title}
    >
      <div className="flex items-center justify-between pb-3 border-b border-[var(--color-border)]">
        <span
          className={cn(
            getTypographyClassName("overline"),
            "text-[var(--color-muted)]"
          )}
        >
          {title}
        </span>
        <span
          className={cn(
            getTypographyClassName("caption"),
            "text-[var(--color-muted)]"
          )}
        >
          {completedCount}/{totalCount} {counterLabel}
        </span>
      </div>

      <div
        className="flex flex-col gap-1.5"
        role="navigation"
        aria-label={ariaLabel ?? title}
      >
        {items.map((item) => {
          const isComplete =
            item.status === null || (item.status === undefined && Boolean(item.isComplete));
          const isWarning = item.status === "can_thong_tin";

          return (
            <button
              key={item.id}
              type="button"
              aria-current={item.isSelected ? "page" : undefined}
              onClick={() => onSelect(item.id)}
              className={cn(
                getTypographyClassName("buttonSecondary"),
                "group flex items-center justify-between min-h-11 w-full rounded-[var(--radius-button)] px-3.5 py-2.5 text-left transition-all duration-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)] cursor-pointer",
                item.isSelected
                  ? "border border-[var(--color-border-strong)] bg-[var(--color-accent-wash)] text-[var(--color-on-surface)] shadow-2xs"
                  : "border border-transparent text-[var(--color-muted)] hover:bg-[color-mix(in_srgb,var(--color-accent-wash)_35%,transparent)] hover:border-[var(--color-border-strong)] hover:text-[var(--color-on-surface)]"
              )}
            >
              <span className="flex items-center gap-1.5 min-w-0 truncate">
                <span className="truncate">{item.label}</span>
                {item.badge ? (
                  <span
                    className={cn(
                      getTypographyClassName("caption"),
                      "rounded-full px-1.5 py-0.5 shrink-0",
                      item.badge.variant === "warning"
                        ? "bg-amber-500/15 text-amber-700"
                        : "bg-amber-500/15 text-amber-700"
                    )}
                  >
                    {item.badge.text}
                  </span>
                ) : null}
              </span>
              <span className="shrink-0 ml-2 flex items-center">
                {isComplete ? (
                  <CheckCircle2
                    size={16}
                    className={cn(
                      "transition-colors",
                      item.isSelected
                        ? "text-[var(--color-accent)]"
                        : "text-[var(--color-accent)] opacity-80 group-hover:opacity-100"
                    )}
                    aria-hidden="true"
                  />
                ) : isWarning ? (
                  <AlertCircle
                    size={16}
                    className="text-amber-500 transition-colors"
                    aria-hidden="true"
                  />
                ) : (
                  <Circle
                    size={16}
                    className="text-[var(--color-muted)] transition-colors group-hover:text-[var(--color-on-surface)]"
                    aria-hidden="true"
                  />
                )}
              </span>
            </button>
          );
        })}
      </div>

      {footer ? <div className="mt-1">{footer}</div> : null}
    </aside>
  );
}
