"use client";

import { CheckCircle2, XCircle } from "lucide-react";
import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";
import type { SupplierProfile } from "../../../lib/quotationApi.ts";
import type { ColumnDef } from "../../ui/data-view/DataTable.tsx";
import { SupplierPreferredStatusBadge } from "../../supplier/SupplierManageDrawer.tsx";

export function createSupplierColumns(
  onEdit: (profile: SupplierProfile) => void,
  onToggleStatus: (profile: SupplierProfile) => void
): ColumnDef<SupplierProfile>[] {
  return [
    {
      key: "name",
      header: "Supplier Name & Type",
      render: (profile) => (
        <div className="flex flex-col gap-1">
          <h4 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>{profile.name}</h4>
          <p className={cn(getTypographyClassName("caption"), "capitalize text-[var(--color-muted)]")}>
            {profile.supplier_type.replace(/_/g, " ")}
          </p>
        </div>
      ),
    },
    {
      key: "destination",
      header: "Destination",
      render: (profile) => (
        <span className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>
          {[profile.city, profile.country].filter(Boolean).join(", ") || "—"}
        </span>
      ),
    },
    {
      key: "currency",
      header: "Currency",
      render: (profile) => <span className={cn(getTypographyClassName("bodySm"))}>{profile.default_currency}</span>,
    },
    {
      key: "preferred_status",
      header: "Preferred Status",
      render: (profile) => <SupplierPreferredStatusBadge status={profile.preferred_status} />,
    },
    {
      key: "quality_tier",
      header: "Quality Tier",
      render: (profile) => (
        <span className={cn(getTypographyClassName("bodySm"), "capitalize text-[var(--color-muted)]")}>
          {profile.quality_tier ? profile.quality_tier.replace(/_/g, " ") : "—"}
        </span>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (profile) => (
        <span
          className={cn(
            getTypographyClassName("caption"),
            "flex items-center gap-1 rounded-full px-2.5 py-0.5 shrink-0 inline-self-start",
            profile.is_active
              ? "bg-[var(--color-accent-wash)] text-[var(--color-accent)] border border-[color-mix(in_srgb,var(--color-accent)_30%,transparent)] shadow-2xs"
              : "bg-[var(--color-surface-muted)] text-[var(--color-muted)] border border-[var(--color-border)]"
          )}
        >
          {profile.is_active ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
          <span>{profile.is_active ? "Active" : "Inactive"}</span>
        </span>
      ),
    },
    {
      key: "actions",
      header: "Actions",
      headerClassName: "text-right",
      cellClassName: "text-right",
      render: (profile) => (
        <div className="flex items-center justify-end gap-2">
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
      ),
    },
  ];
}
