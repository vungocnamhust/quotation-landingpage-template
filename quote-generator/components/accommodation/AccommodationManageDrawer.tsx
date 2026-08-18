"use client";

import { useState } from "react";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";
import {
  createAccommodation,
  updateAccommodation,
  updateAccommodationStatus,
  uploadAccommodationAsset,
  type AccommodationProfile,
  type AccommodationProfileInput,
} from "../../lib/quotationApi";
import type { DestinationRef } from "../destination/types";
import AccommodationProfileForm from "../quotation-workspace/AccommodationProfileForm";

export type AccommodationDrawerMode = "create" | "edit" | "manage" | null;

type Props = {
  mode: AccommodationDrawerMode;
  profiles: AccommodationProfile[];
  editingProfile?: AccommodationProfile | null;
  onClose: () => void;
  onSaved: (saved: AccommodationProfile) => void;
  onMutate: () => Promise<unknown>;
};

const blankDraft = (): AccommodationProfileInput => ({
  destinationId: "",
  name: "",
  room_type: null,
  intro: null,
  phone: null,
  display_city: null,
  display_date: null,
  hotel_asset: null,
  room_asset: null,
});

export function AccommodationManageDrawer({
  mode,
  profiles,
  editingProfile,
  onClose,
  onSaved,
  onMutate,
}: Props) {
  const [currentMode, setCurrentMode] = useState<AccommodationDrawerMode>(mode);
  const [editing, setEditing] = useState<AccommodationProfile | null>(editingProfile ?? null);
  const [draft, setDraft] = useState<AccommodationProfileInput>(() =>
    editingProfile
      ? {
          destinationId: editingProfile.destination_id,
          name: editingProfile.name,
          room_type: editingProfile.room_type,
          intro: editingProfile.intro,
          phone: editingProfile.phone,
          display_city: editingProfile.display_city,
          display_date: editingProfile.display_date,
          hotel_asset: editingProfile.hotel_asset,
          room_asset: editingProfile.room_asset,
        }
      : blankDraft()
  );
  const [destinationRef, setDestinationRef] = useState<DestinationRef | null>(
    editingProfile?.destination_ref ?? null
  );
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);

  if (!currentMode) return null;

  const openEdit = (profile: AccommodationProfile) => {
    setEditing(profile);
    setDraft({
      destinationId: profile.destination_id,
      name: profile.name,
      room_type: profile.room_type,
      intro: profile.intro,
      phone: profile.phone,
      display_city: profile.display_city,
      display_date: profile.display_date,
      hotel_asset: profile.hotel_asset,
      room_asset: profile.room_asset,
    });
    setDestinationRef(profile.destination_ref);
    setCurrentMode("edit");
    setMessage("");
  };

  const saveAccommodation = async () => {
    if (!destinationRef || !draft.name.trim()) {
      setMessage("Destination and accommodation name are required.");
      return;
    }
    setPending(true);
    try {
      const input = { ...draft, destinationId: destinationRef.id };
      const saved = editing
        ? await updateAccommodation(editing.id, input)
        : await createAccommodation(input);
      await onMutate();
      onSaved(saved);
      onClose();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Accommodation could not be saved.");
    } finally {
      setPending(false);
    }
  };

  const upload = async (target: "hotel_asset" | "room_asset", file: File) => {
    if (!editing) return;
    setPending(true);
    try {
      const uploaded = await uploadAccommodationAsset(
        file,
        editing.id,
        target === "hotel_asset" ? "exteriors" : "interiors"
      );
      setDraft((current) => ({ ...current, [target]: uploaded.r2Key }));
      setMessage("Asset uploaded. Save profile to apply changes.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Accommodation asset could not be uploaded.");
    } finally {
      setPending(false);
    }
  };

  const toggleStatus = async (profile: AccommodationProfile) => {
    setPending(true);
    try {
      await updateAccommodationStatus(profile.id, !profile.is_active);
      await onMutate();
      setMessage("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Accommodation status could not be updated.");
    } finally {
      setPending(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={currentMode === "manage" ? "Manage Accommodations" : "Accommodation Profile"}
      className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs"
    >
      <div className="h-full w-full max-w-2xl overflow-y-auto border-l border-[var(--color-border-strong)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] sm:p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
              {currentMode === "manage"
                ? "Manage Accommodations"
                : editing
                ? "Edit Accommodation Profile"
                : "Add Accommodation Profile"}
            </h2>
            <p className={cn(getTypographyClassName("bodySm"), "mt-1 text-[var(--color-muted)]")}>
              {currentMode === "manage"
                ? "Catalog of luxury resorts, hotels, and lodges with pre-configured room types."
                : "Profile stay details and hero imagery will be snapshotted into quotations."}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className={cn(
              getTypographyClassName("buttonSecondary"),
              "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] px-3.5 transition-all cursor-pointer"
            )}
          >
            Close
          </button>
        </div>

        {currentMode === "manage" ? (
          <div className="mt-6 flex flex-col gap-3">
            {profiles.map((profile) => (
              <article
                key={profile.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface-white)] p-3 shadow-2xs"
              >
                <div>
                  <span className={cn(getTypographyClassName("bodyMd"), "block text-[var(--color-on-surface)]")}>
                    {profile.name}
                  </span>
                  <span className={cn(getTypographyClassName("caption"), "block text-[var(--color-muted)]")}>
                    {profile.destination}
                    {profile.room_type ? ` · ${profile.room_type}` : ""} · {profile.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => openEdit(profile)}
                    className={cn(
                      getTypographyClassName("buttonSecondary"),
                      "min-h-10 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] px-3 transition-all cursor-pointer"
                    )}
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => void toggleStatus(profile)}
                    className={cn(
                      getTypographyClassName("buttonSecondary"),
                      profile.is_active
                        ? "min-h-10 rounded-[var(--radius-button)] bg-rose-700 !text-white hover:bg-rose-800 px-3 shadow-2xs border border-transparent transition-all cursor-pointer"
                        : "min-h-10 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-3 shadow-2xs border border-transparent transition-all cursor-pointer"
                    )}
                  >
                    {profile.is_active ? "Deactivate" : "Activate"}
                  </button>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <>
            <AccommodationProfileForm
              draft={draft}
              destinationRef={destinationRef}
              profileId={editing?.id ?? null}
              onChange={setDraft}
              onDestinationChange={setDestinationRef}
              onUpload={(target, file) => void upload(target, file)}
            />
            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                disabled={pending}
                onClick={onClose}
                className={cn(
                  getTypographyClassName("buttonSecondary"),
                  "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] px-4 transition-all cursor-pointer"
                )}
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={pending}
                onClick={() => void saveAccommodation()}
                className={cn(
                  getTypographyClassName("buttonPrimary"),
                  "min-h-11 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-5 shadow-md border border-transparent transition-all disabled:opacity-50 cursor-pointer"
                )}
              >
                {pending ? "Saving…" : "Save Accommodation"}
              </button>
            </div>
          </>
        )}

        {message ? (
          <p aria-live="polite" className={cn(getTypographyClassName("bodySm"), "mt-4 text-[var(--color-accent)]")}>
            {message}
          </p>
        ) : null}
      </div>
    </div>
  );
}
