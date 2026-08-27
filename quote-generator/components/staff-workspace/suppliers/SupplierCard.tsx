"use client";

import { memo } from "react";
import { MapPin, CheckCircle2, XCircle, Truck } from "lucide-react";
import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";
import type { SupplierProfile } from "../../../lib/quotationApi.ts";
import { SupplierPreferredStatusBadge } from "../../supplier/SupplierManageDrawer.tsx";

interface Props {
  profile: SupplierProfile;
  onEdit: (profile: SupplierProfile) => void;
  onToggleStatus: (profile: SupplierProfile) => void;
}

export const SupplierCard = memo(function SupplierCard({ profile, onEdit, onToggleStatus }: Props) {
  return (
    <article className="flex flex-col justify-between rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] transition-all hover:border-[var(--color-border-strong)]">
      <div>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className={cn(getTypographyClassName("cardTitle"), "truncate text-[var(--color-on-surface)]")}>{profile.name}</h3>
            <p className={cn(getTypographyClassName("caption"), "mt-0.5 flex items-center gap-1.5 text-[var(--color-muted)]")}>
              <Truck size={14} className="shrink-0 text-[var(--color-accent)]" />
              <span className="truncate capitalize">{profile.supplier_type.replace(/_/g, " ")}</span>
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
          <SupplierPreferredStatusBadge status={profile.preferred_status} />
          {profile.quality_tier ? (
            <span className={cn(getTypographyClassName("caption"), "rounded-full border border-[var(--color-border)] px-2 py-0.5 text-[var(--color-muted)] capitalize")}>
              {profile.quality_tier.replace(/_/g, " ")}
            </span>
          ) : null}
          <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>{profile.default_currency}</span>
        </div>

        {profile.country || profile.city ? (
          <p className={cn(getTypographyClassName("caption"), "mt-2 flex items-center gap-1.5 text-[var(--color-muted)]")}>
            <MapPin size={13} className="shrink-0" />
            <span>{[profile.city, profile.country].filter(Boolean).join(", ")}</span>
          </p>
        ) : null}
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
