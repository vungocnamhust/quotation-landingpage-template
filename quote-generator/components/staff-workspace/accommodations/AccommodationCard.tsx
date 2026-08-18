"use client";

import { memo } from "react";
import { MapPin, Phone, CheckCircle2, XCircle } from "lucide-react";
import { getTypographyClassName } from "../../../config/typography";
import { cn } from "../../../utils/cn";
import type { AccommodationProfile } from "../../../lib/quotationApi";

interface Props {
  profile: AccommodationProfile;
  onEdit: (profile: AccommodationProfile) => void;
  onToggleStatus: (profile: AccommodationProfile) => void;
}

export const AccommodationCard = memo(function AccommodationCard({
  profile,
  onEdit,
  onToggleStatus,
}: Props) {
  return (
    <article className="flex flex-col justify-between rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] transition-all hover:border-[var(--color-border-strong)]">
      <div>
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
                "mt-0.5 flex items-center gap-1.5 text-[var(--color-muted)]"
              )}
            >
              <MapPin size={14} className="shrink-0 text-[var(--color-accent)]" />
              <span className="truncate">
                {profile.display_city || profile.destination}
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

        <div
          className={cn(
            getTypographyClassName("caption"),
            "mt-4 flex flex-col gap-1.5 text-[var(--color-muted)]"
          )}
        >
          {profile.room_type ? (
            <div className="flex items-center justify-between">
              <span className="text-[var(--color-on-surface)]">Room type:</span>
              <span className="truncate">{profile.room_type}</span>
            </div>
          ) : null}

          {profile.phone ? (
            <div className="flex items-center gap-1.5">
              <Phone size={13} className="shrink-0" />
              <span>{profile.phone}</span>
            </div>
          ) : null}

          {profile.intro ? (
            <p
              className={cn(
                getTypographyClassName("caption"),
                "mt-2 line-clamp-2 text-[var(--color-muted)]"
              )}
            >
              “{profile.intro}”
            </p>
          ) : null}
        </div>
      </div>

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
            profile.is_active
              ? "text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30"
              : "text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/30"
          )}
        >
          {profile.is_active ? "Deactivate" : "Activate"}
        </button>
      </div>
    </article>
  );
});
