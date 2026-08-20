"use client";

import { HeartPulse, Utensils, Moon, Accessibility, Activity, MessageSquare } from "lucide-react";
import DetailSectionCard from "./DetailSectionCard.tsx";
import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";

type Props = {
  dietary?: string | null;
  halal?: string | null;
  mobility?: string | null;
  healthConsiderations?: string | null;
  specialRequirements?: string | null;
};

export default function SpecialRequirementsCard({
  dietary,
  halal,
  mobility,
  healthConsiderations,
  specialRequirements,
}: Props) {
  const hasRequirements = Boolean(
    dietary || halal || mobility || healthConsiderations || specialRequirements
  );

  return (
    <DetailSectionCard
      title="Special, Dietary & Health Requirements"
      subtitle="Allergies, religious diet, mobility accommodations & health considerations"
      icon={<HeartPulse size={18} aria-hidden="true" />}
      headerBadge={
        <span
          className={cn(
            getTypographyClassName("caption"),
            "rounded-full px-2.5 py-0.5 border",
            hasRequirements
              ? "bg-amber-50 text-amber-800 border-amber-200"
              : "bg-[var(--color-surface-muted)] text-[var(--color-muted)] border-[var(--color-border)]"
          )}
        >
          {hasRequirements ? "Action Required" : "None Stated"}
        </span>
      }
    >
      {!hasRequirements ? (
        <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)] p-2")}>
          No special dietary, religious, mobility or medical restrictions were specified for this request.
        </p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {dietary ? (
            <div className="flex flex-col gap-1 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)] flex items-center gap-1.5")}>
                <Utensils size={13} className="text-[var(--color-accent)]" />
                <span>Dietary & Allergies</span>
              </span>
              <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>{dietary}</p>
            </div>
          ) : null}

          {halal ? (
            <div className="flex flex-col gap-1 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)] flex items-center gap-1.5")}>
                <Moon size={13} className="text-[var(--color-accent)]" />
                <span>Halal / Religious Diet</span>
              </span>
              <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>{halal}</p>
            </div>
          ) : null}

          {mobility ? (
            <div className="flex flex-col gap-1 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)] flex items-center gap-1.5")}>
                <Accessibility size={13} className="text-[var(--color-accent)]" />
                <span>Mobility & Accessibility</span>
              </span>
              <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>{mobility}</p>
            </div>
          ) : null}

          {healthConsiderations ? (
            <div className="flex flex-col gap-1 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)] flex items-center gap-1.5")}>
                <Activity size={13} className="text-[var(--color-accent)]" />
                <span>Health Considerations</span>
              </span>
              <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>{healthConsiderations}</p>
            </div>
          ) : null}

          {specialRequirements ? (
            <div className="flex flex-col gap-1 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3 sm:col-span-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)] flex items-center gap-1.5")}>
                <MessageSquare size={13} className="text-[var(--color-accent)]" />
                <span>General Special Notes</span>
              </span>
              <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>{specialRequirements}</p>
            </div>
          ) : null}
        </div>
      )}
    </DetailSectionCard>
  );
}
