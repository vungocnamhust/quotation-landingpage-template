"use client";

import { memo } from "react";
import { CheckCircle2, Package, XCircle } from "lucide-react";
import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";
import type { ProductProfile } from "../../../lib/quotationApi.ts";

interface Props {
  profile: ProductProfile;
  onEdit: (profile: ProductProfile) => void;
  onToggleStatus: (profile: ProductProfile) => void;
}

export const ProductCard = memo(function ProductCard({ profile, onEdit, onToggleStatus }: Props) {
  return (
    <article className="flex flex-col justify-between rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] transition-all hover:border-[var(--color-border-strong)]">
      <div>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className={cn(getTypographyClassName("cardTitle"), "truncate text-[var(--color-on-surface)]")}>{profile.title}</h3>
            <p className={cn(getTypographyClassName("caption"), "mt-0.5 flex items-center gap-1.5 text-[var(--color-muted)]")}>
              <Package size={14} className="shrink-0 text-[var(--color-accent)]" />
              <span className="truncate capitalize">
                {profile.category.replace(/_/g, " ")}
                {profile.subcategory ? ` · ${profile.subcategory.replace(/_/g, " ")}` : ""}
              </span>
            </p>
          </div>
          <span
            className={cn(
              getTypographyClassName("caption"),
              "flex items-center gap-1 rounded-full px-2.5 py-0.5 shrink-0",
              profile.is_active
                ? "bg-[var(--color-accent-wash)] text-[var(--color-accent)] border border-[color-mix(in_srgb,var(--color-accent)_30%,transparent)] shadow-2xs"
                : "bg-[var(--color-surface-muted)] text-[var(--color-muted)] border border-[var(--color-border)]"
            )}
          >
            {profile.is_active ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
            <span>{profile.is_active ? "Active" : "Inactive"}</span>
          </span>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className={cn(getTypographyClassName("caption"), "rounded-full border border-[var(--color-border)] px-2 py-0.5 text-[var(--color-muted)] capitalize")}>
            Per {profile.unit.replace(/_/g, " ")} · Per {profile.time_basis}
          </span>
          {!profile.supplier_id ? (
            <span className={cn(getTypographyClassName("caption"), "rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-amber-800")}>
              ⚠ no supplier
            </span>
          ) : null}
        </div>
      </div>

      <div className="mt-4 flex items-center gap-2 border-t border-[var(--color-border)] pt-3">
        <button
          type="button"
          onClick={() => onEdit(profile)}
          className={cn(
            getTypographyClassName("buttonSecondary"),
            "rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 py-1 text-[var(--color-on-surface)] transition-all hover:bg-[var(--color-surface-hover)] cursor-pointer"
          )}
        >
          Edit
        </button>
        <button
          type="button"
          onClick={() => onToggleStatus(profile)}
          className={cn(
            getTypographyClassName("caption"),
            "rounded-[var(--radius-button)] px-2.5 py-1 transition-all cursor-pointer",
            profile.is_active ? "text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30" : "text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/30"
          )}
        >
          {profile.is_active ? "Deactivate" : "Activate"}
        </button>
      </div>
    </article>
  );
});
