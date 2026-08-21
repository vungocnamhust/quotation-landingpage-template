"use client";

import { memo } from "react";
import { MapPin, CheckCircle2, XCircle, Globe, Compass, Folder } from "lucide-react";
import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";
import type { DestinationProfile } from "../../../lib/quotationApi.ts";

interface Props {
  profile: DestinationProfile;
  onEdit: (profile: DestinationProfile) => void;
  onToggleStatus: (profile: DestinationProfile) => void;
}

export const DestinationCard = memo(function DestinationCard({
  profile,
  onEdit,
  onToggleStatus,
}: Props) {
  const visibleAliases = (profile.aliases || []).slice(0, 3);
  const remainingAliasesCount = (profile.aliases || []).length - visibleAliases.length;

  return (
    <article className="flex flex-col justify-between rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] transition-all hover:border-[var(--color-border-strong)]">
      <div>
        {/* Header: Name and Status Badge */}
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3
              className={cn(
                getTypographyClassName("cardTitle"),
                "truncate text-[var(--color-on-surface)]"
              )}
            >
              {profile.name}
            </h3>
            <p
              className={cn(
                getTypographyClassName("caption"),
                "mt-0.5 font-mono text-[var(--color-muted)]"
              )}
            >
              slug: {profile.slug}
            </p>
          </div>
          <span
            className={cn(
              getTypographyClassName("caption"),
              "flex items-center gap-1 rounded-full px-2.5 py-0.5 shrink-0",
              profile.isActive
                ? "bg-[var(--color-accent-wash)] text-[var(--color-accent)] border border-[color-mix(in_srgb,var(--color-accent)_30%,transparent)] shadow-2xs"
                : "bg-[var(--color-surface-muted)] text-[var(--color-muted)] border border-[var(--color-border)]"
            )}
          >
            {profile.isActive ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
            <span>{profile.isActive ? "Active" : "Inactive"}</span>
          </span>
        </div>

        {/* Location pills: Country / Region / Province */}
        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          {profile.countrySlug ? (
            <span
              className={cn(
                getTypographyClassName("caption"),
                "inline-flex items-center gap-1 rounded-[calc(var(--radius-button)-4px)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-2 py-0.5 capitalize text-[var(--color-on-surface)]"
              )}
            >
              <Globe size={11} className="text-[var(--color-muted)]" />
              <span>{profile.countrySlug}</span>
            </span>
          ) : null}

          {profile.regionSlug ? (
            <span
              className={cn(
                getTypographyClassName("caption"),
                "inline-flex items-center gap-1 rounded-[calc(var(--radius-button)-4px)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-2 py-0.5 capitalize text-[var(--color-muted)]"
              )}
            >
              <Compass size={11} className="text-[var(--color-muted)]" />
              <span>{profile.regionSlug}</span>
            </span>
          ) : null}

          {profile.provinceSlug ? (
            <span
              className={cn(
                getTypographyClassName("caption"),
                "rounded-[calc(var(--radius-button)-4px)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-2 py-0.5 capitalize text-[var(--color-muted)]"
              )}
            >
              {profile.provinceSlug}
            </span>
          ) : null}
        </div>

        {/* Coordinates */}
        <div
          className={cn(
            getTypographyClassName("caption"),
            "mt-3.5 flex items-center gap-1.5 text-[var(--color-muted)]"
          )}
        >
          <MapPin size={13} className="shrink-0 text-[var(--color-accent)]" />
          {profile.latitude !== null && profile.longitude !== null ? (
            <span className="font-mono">
              {Number(profile.latitude).toFixed(4)}, {Number(profile.longitude).toFixed(4)}
            </span>
          ) : (
            <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
              No GPS coordinates set
            </span>
          )}
        </div>

        {/* Media Folder */}
        <div
          className={cn(
            getTypographyClassName("caption"),
            "mt-2 flex items-center gap-1.5 text-[var(--color-muted)]"
          )}
        >
          <Folder size={13} className="shrink-0 text-[var(--color-muted)]" />
          <span className="font-mono truncate">
            {profile.mediaPrefix ? (
              <span className="text-[var(--color-accent)]">{profile.mediaPrefix}</span>
            ) : (
              <span>{profile.defaultMediaPrefix || `destination/${profile.slug}`}</span>
            )}
          </span>
        </div>

        {/* Aliases */}
        {profile.aliases && profile.aliases.length > 0 ? (
          <div className="mt-3">
            <span
              className={cn(
                getTypographyClassName("caption"),
                "text-[var(--color-muted)] block mb-1"
              )}
            >
              Aliases:
            </span>
            <div className="flex flex-wrap gap-1">
              {visibleAliases.map((alias) => (
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
              {remainingAliasesCount > 0 ? (
                <span
                  className={cn(
                    getTypographyClassName("caption"),
                    "rounded-full border border-dashed border-[var(--color-border)] px-1.5 py-0.5 text-[var(--color-muted)]"
                  )}
                >
                  +{remainingAliasesCount} more
                </span>
              ) : null}
            </div>
          </div>
        ) : null}
      </div>

      {/* Footer action buttons */}
      <div className="mt-5 flex items-center justify-between border-t border-[var(--color-border)] pt-4">
        <button
          type="button"
          onClick={() => onEdit(profile)}
          className={cn(
            getTypographyClassName("buttonSecondary"),
            "rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 py-1.5 text-[var(--color-on-surface)] transition-all hover:bg-[var(--color-surface-hover)] cursor-pointer"
          )}
        >
          Edit
        </button>

        <button
          type="button"
          onClick={() => onToggleStatus(profile)}
          className={cn(
            getTypographyClassName("caption"),
            "rounded-[var(--radius-button)] px-3 py-1.5 transition-all cursor-pointer",
            profile.isActive
              ? "text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30"
              : "text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/30"
          )}
        >
          {profile.isActive ? "Deactivate" : "Activate"}
        </button>
      </div>
    </article>
  );
});
