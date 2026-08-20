"use client";

import React, { useState } from "react";
import { Copy, Check, ExternalLink } from "lucide-react";
import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";

type Props = {
  label: string;
  value?: React.ReactNode;
  icon?: React.ReactNode;
  href?: string;
  copyable?: boolean;
  copyText?: string;
  badge?: boolean;
  badgeVariant?: "default" | "accent" | "success" | "warning" | "danger";
  emptyFallback?: string;
  className?: string;
};

export default function DetailField({
  label,
  value,
  icon,
  href,
  copyable = false,
  copyText,
  badge = false,
  badgeVariant = "default",
  emptyFallback = "—",
  className,
}: Props) {
  const [copied, setCopied] = useState(false);

  const hasValue = value !== undefined && value !== null && value !== "";
  const displayValue = hasValue ? value : emptyFallback;

  const handleCopy = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const textToCopy = copyText || (typeof value === "string" ? value : "");
    if (textToCopy) {
      navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  };

  const getBadgeClass = () => {
    switch (badgeVariant) {
      case "accent":
        return "bg-[var(--color-accent-wash)] text-[var(--color-accent)] border-[var(--color-accent)]";
      case "success":
        return "bg-emerald-50 text-emerald-700 border-emerald-200";
      case "warning":
        return "bg-amber-50 text-amber-800 border-amber-200";
      case "danger":
        return "bg-rose-50 text-rose-700 border-rose-200";
      default:
        return "bg-[var(--color-surface-muted)] text-[var(--color-on-surface)] border-[var(--color-border)]";
    }
  };

  return (
    <div className={cn("flex flex-col gap-1 border-b border-[var(--color-border)] pb-2.5 last:border-b-0 last:pb-0", className)}>
      <span className={cn(getTypographyClassName("label"), "flex items-center gap-1.5 text-[var(--color-muted)]")}>
        {icon ? <span className="text-[var(--color-muted)] shrink-0">{icon}</span> : null}
        <span>{label}</span>
      </span>

      <div className="flex items-center justify-between gap-2 min-h-[1.5rem]">
        {badge && hasValue ? (
          <span
            className={cn(
              getTypographyClassName("caption"),
              "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 border",
              getBadgeClass()
            )}
          >
            {displayValue}
          </span>
        ) : href && hasValue ? (
          <a
            href={href}
            target={href.startsWith("http") ? "_blank" : undefined}
            rel={href.startsWith("http") ? "noopener noreferrer" : undefined}
            className={cn(
              getTypographyClassName("bodyMd"),
              "flex items-center gap-1 text-[var(--color-accent)] hover:underline truncate"
            )}
          >
            <span>{displayValue}</span>
            {href.startsWith("http") ? <ExternalLink size={12} aria-hidden="true" /> : null}
          </a>
        ) : (
          <span
            className={cn(
              getTypographyClassName("bodyMd"),
              hasValue ? "text-[var(--color-on-surface)]" : "text-[var(--color-muted)]",
              "truncate"
            )}
          >
            {displayValue}
          </span>
        )}

        {copyable && hasValue ? (
          <button
            type="button"
            onClick={handleCopy}
            title="Copy to clipboard"
            className="flex h-6 w-6 shrink-0 items-center justify-center rounded text-[var(--color-muted)] hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-on-surface)] transition-colors cursor-pointer"
          >
            {copied ? (
              <Check size={12} className="text-emerald-600" aria-hidden="true" />
            ) : (
              <Copy size={12} aria-hidden="true" />
            )}
          </button>
        ) : null}
      </div>
    </div>
  );
}
