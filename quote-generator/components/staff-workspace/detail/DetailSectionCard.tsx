"use client";

import React from "react";
import { getTypographyClassName } from "../../../config/typography";
import { cn } from "../../../utils/cn";

type Props = {
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
  headerBadge?: React.ReactNode;
  headerAction?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
};

export default function DetailSectionCard({
  title,
  subtitle,
  icon,
  headerBadge,
  headerAction,
  children,
  className,
}: Props) {
  return (
    <section
      className={cn(
        "flex flex-col gap-4 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] sm:p-6 transition-all",
        className
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--color-border)] pb-3.5">
        <div className="flex items-center gap-3">
          {icon ? (
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--color-surface-muted)] text-[var(--color-accent)]">
              {icon}
            </div>
          ) : null}
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
                {title}
              </h2>
              {headerBadge ? <span>{headerBadge}</span> : null}
            </div>
            {subtitle ? (
              <p className={cn(getTypographyClassName("caption"), "mt-0.5 text-[var(--color-muted)]")}>
                {subtitle}
              </p>
            ) : null}
          </div>
        </div>

        {headerAction ? <div className="shrink-0">{headerAction}</div> : null}
      </div>

      <div className="flex flex-col gap-4">{children}</div>
    </section>
  );
}
