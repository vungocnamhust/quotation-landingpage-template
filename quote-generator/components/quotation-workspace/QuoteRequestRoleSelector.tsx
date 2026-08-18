"use client";

import { User, Briefcase } from "lucide-react";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";
import type { QuoteRequestRole } from "./factsTypes";

type Props = {
  value: QuoteRequestRole;
  onChange: (role: QuoteRequestRole) => void;
};

const ROLES: Array<{
  id: QuoteRequestRole;
  title: string;
  subtitle: string;
  icon: typeof User;
}> = [
  {
    id: "traveller",
    title: "I’m planning a journey",
    subtitle: "For myself, my partner, family or friends.",
    icon: User,
  },
  {
    id: "advisor",
    title: "I’m a Travel Advisor",
    subtitle: "I’m planning a journey for a client.",
    icon: Briefcase,
  },
];

export default function QuoteRequestRoleSelector({ value, onChange }: Props) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <h3 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
          How can we assist you?
        </h3>
        <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>
          Choose the option that best describes your enquiry.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {ROLES.map((role) => {
          const isSelected = value === role.id;
          const Icon = role.icon;
          return (
            <button
              type="button"
              key={role.id}
              onClick={() => onChange(role.id)}
              className={cn(
                "flex items-start gap-3 border p-4 text-left transition-all rounded-[var(--radius-card)] cursor-pointer",
                isSelected
                  ? "border-[var(--color-accent)] bg-[var(--color-accent-wash)] text-[var(--color-accent)] shadow-xs ring-1 ring-[var(--color-accent)]"
                  : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:border-[var(--color-border-strong)] hover:bg-[var(--color-surface-muted)]"
              )}
            >
              <div
                className={cn(
                  "mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full",
                  isSelected
                    ? "bg-[var(--color-accent)] text-white"
                    : "bg-[var(--color-surface-muted)] text-[var(--color-muted)]"
                )}
              >
                <Icon size={18} aria-hidden="true" />
              </div>
              <div className="flex flex-col gap-0.5">
                <span className={cn(getTypographyClassName("cardTitle"))}>
                  {role.title}
                </span>

                <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
                  {role.subtitle}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
