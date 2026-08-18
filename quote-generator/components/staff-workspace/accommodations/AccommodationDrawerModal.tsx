"use client";

import { getTypographyClassName } from "../../../config/typography";
import { cn } from "../../../utils/cn";
import AccommodationProfileForm from "../../quotation-workspace/AccommodationProfileForm";
import type { AccommodationProfile, AccommodationProfileInput } from "../../../lib/quotationApi";
import type { DestinationRef } from "../../destination/types";

interface Props {
  isOpen: boolean;
  editing: AccommodationProfile | null;
  draft: AccommodationProfileInput;
  destinationRef: DestinationRef | null;
  pending: boolean;
  message: string;
  onClose: () => void;
  onDraftChange: (draft: AccommodationProfileInput) => void;
  onDestinationChange: (dest: DestinationRef | null) => void;
  onUploadAsset: (target: "hotel_asset" | "room_asset", file: File) => void;
  onSave: () => void;
}

export function AccommodationDrawerModal({
  isOpen,
  editing,
  draft,
  destinationRef,
  pending,
  message,
  onClose,
  onDraftChange,
  onDestinationChange,
  onUploadAsset,
  onSave,
}: Props) {
  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Accommodation profile"
      className="fixed inset-0 z-50 flex justify-end bg-[color-mix(in_srgb,var(--color-contrast)_35%,transparent)]"
    >
      <section className="h-full w-full max-w-2xl overflow-y-auto border-l border-[var(--color-border-strong)] bg-[var(--color-surface)] p-6 shadow-[var(--elevation-card)]">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2
              className={cn(
                getTypographyClassName("cardTitle"),
                "text-[var(--color-on-surface)]"
              )}
            >
              {editing ? "Edit Accommodation" : "Add Accommodation"}
            </h2>
            <p
              className={cn(
                getTypographyClassName("bodySm"),
                "mt-1 text-[var(--color-muted)]"
              )}
            >
              Configure hotel details and media assets for use across quotations.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className={cn(
              getTypographyClassName("buttonSecondary"),
              "rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3.5 py-2 text-[var(--color-on-surface)] transition-all hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] cursor-pointer"
            )}
          >
            Close
          </button>
        </div>

        <AccommodationProfileForm
          draft={draft}
          destinationRef={destinationRef}
          profileId={editing?.id ?? null}
          onChange={onDraftChange}
          onDestinationChange={onDestinationChange}
          onUpload={onUploadAsset}
        />

        <div className="mt-6 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className={cn(
              getTypographyClassName("buttonSecondary"),
              "rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-4 py-2.5 text-[var(--color-on-surface)] hover:bg-[var(--color-surface-hover)] cursor-pointer"
            )}
          >
            Cancel
          </button>

          <button
            type="button"
            disabled={pending}
            onClick={onSave}
            className={cn(
              getTypographyClassName("buttonPrimary"),
              "rounded-[var(--radius-button)] bg-[var(--color-accent)] px-5 py-2.5 text-white shadow-md transition-all hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] disabled:opacity-50 cursor-pointer"
            )}
          >
            {pending ? "Saving…" : "Save Accommodation"}
          </button>
        </div>

        {message ? (
          <p
            aria-live="polite"
            className={cn(
              getTypographyClassName("bodySm"),
              "mt-3 text-[var(--color-accent)]"
            )}
          >
            {message}
          </p>
        ) : null}
      </section>
    </div>
  );
}
