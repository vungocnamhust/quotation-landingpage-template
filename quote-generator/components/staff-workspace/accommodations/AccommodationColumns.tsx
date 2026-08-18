"use client";

import { MapPin, Phone, CheckCircle2, XCircle } from "lucide-react";
import { getTypographyClassName } from "../../../config/typography";
import { cn } from "../../../utils/cn";
import type { AccommodationProfile } from "../../../lib/quotationApi";
import type { ColumnDef } from "../../ui/data-view/DataTable";

export function createAccommodationColumns(
  onEdit: (profile: AccommodationProfile) => void,
  onToggleStatus: (profile: AccommodationProfile) => void
): ColumnDef<AccommodationProfile>[] {
  return [
    {
      key: "name",
      header: "Accommodation Name & Destination",
      render: (profile) => (
        <div className="flex flex-col gap-1">
          <h4
            className={cn(
              getTypographyClassName("cardTitle"),
              "text-[var(--color-on-surface)]"
            )}
          >
            {profile.name}
          </h4>
          <p
            className={cn(
              getTypographyClassName("caption"),
              "flex items-center gap-1 text-[var(--color-muted)]"
            )}
          >
            <MapPin size={13} className="shrink-0 text-[var(--color-accent)]" />
            <span>{profile.display_city || profile.destination}</span>
          </p>
        </div>
      ),
    },
    {
      key: "room_type",
      header: "Room Type",
      render: (profile) => (
        <div className="flex flex-col gap-1">
          <span className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>
            {profile.room_type || "Standard Room"}
          </span>
        </div>
      ),
    },
    {
      key: "contact",
      header: "Phone / Contact",
      render: (profile) =>
        profile.phone ? (
          <p
            className={cn(
              getTypographyClassName("caption"),
              "flex items-center gap-1.5 text-[var(--color-muted)]"
            )}
          >
            <Phone size={13} className="shrink-0" />
            <span>{profile.phone}</span>
          </p>
        ) : (
          <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
            —
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
              profile.is_active
                ? "text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30"
                : "text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/30"
            )}
          >
            {profile.is_active ? "Deactivate" : "Activate"}
          </button>
        </div>
      ),
    },
  ];
}
