"use client";

import { Compass, Sparkles, AlertTriangle, MessageSquare, PartyPopper } from "lucide-react";
import DetailSectionCard from "./DetailSectionCard";
import DetailField from "./DetailField";
import { getTypographyClassName } from "../../../config/typography";
import { cn } from "../../../utils/cn";

type Props = {
  primaryTheme?: string | null;
  travelPace?: string | null;
  occasion?: string | null;
  priority1?: string | null;
  priority2?: string | null;
  priority3?: string | null;
  mustHave?: string | null;
  avoid?: string | null;
  message?: string | null;
};

export default function TravelStyleCard({
  primaryTheme,
  travelPace,
  occasion,
  priority1,
  priority2,
  priority3,
  mustHave,
  avoid,
  message,
}: Props) {
  const hasPriorities = Boolean(priority1 || priority2 || priority3);

  return (
    <DetailSectionCard
      title="Travel Style & Journey Vision"
      subtitle="Aesthetic direction, journey pace, top priorities & deal-breakers"
      icon={<Compass size={18} aria-hidden="true" />}
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <DetailField
          label="Primary Travel Theme"
          value={primaryTheme || "Living Heritage"}
          badge
          badgeVariant="accent"
        />

        <DetailField
          label="Travel Pace"
          value={travelPace || "Balanced"}
          badge
          badgeVariant="default"
        />

        <DetailField
          label="Special Occasion / Celebration"
          value={occasion}
          icon={<PartyPopper size={13} aria-hidden="true" />}
          emptyFallback="None specified"
        />
      </div>

      {/* Top 3 Priorities List */}
      {hasPriorities ? (
        <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3.5">
          <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)] flex items-center gap-1.5 mb-2")}>
            <Sparkles size={13} className="text-[var(--color-accent)]" aria-hidden="true" />
            <span>Top Journey Priorities</span>
          </span>
          <ul className="flex flex-col gap-1.5 pl-1">
            {priority1 ? (
              <li className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)] flex items-start gap-2")}>
                <span className={cn(getTypographyClassName("caption"), "flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--color-accent-wash)] text-[var(--color-accent)]")}>
                  1
                </span>
                <span>{priority1}</span>
              </li>
            ) : null}
            {priority2 ? (
              <li className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)] flex items-start gap-2")}>
                <span className={cn(getTypographyClassName("caption"), "flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--color-accent-wash)] text-[var(--color-accent)]")}>
                  2
                </span>
                <span>{priority2}</span>
              </li>
            ) : null}
            {priority3 ? (
              <li className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)] flex items-start gap-2")}>
                <span className={cn(getTypographyClassName("caption"), "flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--color-accent-wash)] text-[var(--color-accent)]")}>
                  3
                </span>
                <span>{priority3}</span>
              </li>
            ) : null}
          </ul>
        </div>
      ) : null}

      {/* Must-have vs Avoid Cards */}
      {mustHave || avoid ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {mustHave ? (
            <div className="rounded-[var(--radius-card)] border border-emerald-200 bg-emerald-50/50 p-3">
              <span className={cn(getTypographyClassName("label"), "text-emerald-800 flex items-center gap-1.5 mb-1")}>
                <Sparkles size={13} aria-hidden="true" />
                <span>Must-Have Experiences</span>
              </span>
              <p className={cn(getTypographyClassName("bodySm"), "text-emerald-950 whitespace-pre-wrap")}>
                {mustHave}
              </p>
            </div>
          ) : null}

          {avoid ? (
            <div className="rounded-[var(--radius-card)] border border-rose-200 bg-rose-50/50 p-3">
              <span className={cn(getTypographyClassName("label"), "text-rose-800 flex items-center gap-1.5 mb-1")}>
                <AlertTriangle size={13} aria-hidden="true" />
                <span>Must Avoid / Deal-Breakers</span>
              </span>
              <p className={cn(getTypographyClassName("bodySm"), "text-rose-950 whitespace-pre-wrap")}>
                {avoid}
              </p>
            </div>
          ) : null}
        </div>
      ) : null}

      {/* Special Requests & Journey Vision */}
      {message ? (
        <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3.5">
          <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)] flex items-center gap-1.5 mb-1.5")}>
            <MessageSquare size={13} aria-hidden="true" />
            <span>Special Requests & Journey Vision</span>
          </span>
          <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)] whitespace-pre-wrap")}>
            {message}
          </p>
        </div>
      ) : null}
    </DetailSectionCard>
  );
}
