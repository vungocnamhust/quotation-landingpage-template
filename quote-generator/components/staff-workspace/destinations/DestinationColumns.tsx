"use client";

import { MapPin, CheckCircle2, XCircle } from "lucide-react";
import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";
import type { DestinationProfile } from "../../../lib/quotationApi.ts";
import type { ColumnDef } from "../../ui/data-view/DataTable.tsx";

export function createDestinationColumns(
  onEdit: (profile: DestinationProfile) => void,
  onToggleStatus: (profile: DestinationProfile) => void
): ColumnDef<DestinationProfile>[] {
  return [
    {
      key: "name",
      header: "Destination & Slug",
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
          <span
            className={cn(
              getTypographyClassName("caption"),
              "font-mono text-[var(--color-muted)]"
            )}
          >
            slug: {profile.slug}
          </span>
          {profile.matchedFrom ? (
            <span
              className={cn(
                getTypographyClassName("caption"),
                "text-[var(--color-accent)]"
              )}
            >
              Matched: {profile.matchedFrom}
            </span>
          ) : null}
        </div>
      ),
    },
    {
      key: "location",
      header: "Country / Region / Province",
      render: (profile) => (
        <div className="flex flex-col gap-1">
          <span
            className={cn(
              getTypographyClassName("bodySm"),
              "capitalize text-[var(--color-on-surface)]"
            )}
          >
            {profile.countrySlug || "—"}
          </span>
          <div className="flex flex-wrap gap-1">
            {profile.regionSlug ? (
              <span
                className={cn(
                  getTypographyClassName("caption"),
                  "rounded border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-1.5 py-0.5 capitalize text-[var(--color-muted)]"
                )}
              >
                {profile.regionSlug}
              </span>
            ) : null}
            {profile.provinceSlug ? (
              <span
                className={cn(
                  getTypographyClassName("caption"),
                  "rounded border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-1.5 py-0.5 capitalize text-[var(--color-muted)]"
                )}
              >
                {profile.provinceSlug}
              </span>
            ) : null}
          </div>
        </div>
      ),
    },
    {
      key: "coordinates",
      header: "GPS Coordinates",
      render: (profile) => (
        <div className="flex items-center gap-1.5">
          <MapPin size={13} className="shrink-0 text-[var(--color-accent)]" />
          {profile.latitude !== null && profile.longitude !== null ? (
            <span
              className={cn(
                getTypographyClassName("caption"),
                "font-mono text-[var(--color-on-surface)]"
              )}
            >
              {Number(profile.latitude).toFixed(4)}, {Number(profile.longitude).toFixed(4)}
            </span>
          ) : (
            <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
              —
            </span>
          )}
        </div>
      ),
    },
    {
      key: "aliases",
      header: "Aliases",
      render: (profile) =>
        profile.aliases && profile.aliases.length > 0 ? (
          <div className="flex max-w-xs flex-wrap gap-1">
            {profile.aliases.slice(0, 3).map((alias) => (
              <span
                key={alias}
                className={cn(
                  getTypographyClassName("caption"),
                  "rounded-full border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-2 py-0.5 text-[var(--color-on-surface)]"
                )}
              >
                {alias}
              </span>
            ))}
            {profile.aliases.length > 3 ? (
              <span
                className={cn(
                  getTypographyClassName("caption"),
                  "rounded-full border border-dashed border-[var(--color-border)] px-1.5 py-0.5 text-[var(--color-muted)]"
                )}
              >
                +{profile.aliases.length - 3}
              </span>
            ) : null}
          </div>
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
            "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 shrink-0",
            profile.isActive
              ? "bg-[var(--color-accent-wash)] text-[var(--color-accent)] border border-[color-mix(in_srgb,var(--color-accent)_30%,transparent)] shadow-2xs"
              : "bg-[var(--color-surface-muted)] text-[var(--color-muted)] border border-[var(--color-border)]"
          )}
        >
          {profile.isActive ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
          <span>{profile.isActive ? "Active" : "Inactive"}</span>
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
              profile.isActive
                ? "text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30"
                : "text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/30"
            )}
          >
            {profile.isActive ? "Deactivate" : "Activate"}
          </button>
        </div>
      ),
    },
  ];
}
