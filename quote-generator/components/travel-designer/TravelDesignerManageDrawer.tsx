"use client";

import { useState } from "react";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";
import {
  createTravelDesigner,
  setTravelDesignerDefault,
  updateTravelDesigner,
  updateTravelDesignerStatus,
  uploadTravelDesignerPortrait,
  type TravelDesignerInput,
  type TravelDesignerProfile,
} from "../../lib/quotationApi";

export type TravelDesignerDrawerMode = "create" | "edit" | "manage" | null;

type Props = {
  mode: TravelDesignerDrawerMode;
  brandId?: string | null;
  profiles: TravelDesignerProfile[];
  editingProfile?: TravelDesignerProfile | null;
  onClose: () => void;
  onSaved: (saved: TravelDesignerProfile) => void;
  onMutate: () => Promise<unknown>;
};

const blankDraft = (): TravelDesignerInput => ({
  name: "",
  email: "",
  phone: "",
  imageAssetId: null,
  imageUrl: null,
  imageR2Key: null,
});

function initials(name: string) {
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0])
      .join("")
      .toUpperCase() || "TD"
  );
}

export function ProfileAvatar({
  profile,
  size = "md",
}: {
  profile: Pick<TravelDesignerProfile, "name" | "imageUrl">;
  size?: "sm" | "md" | "lg";
}) {
  const sizeClasses = {
    sm: "h-7 w-7",
    md: "h-9 w-9",
    lg: "h-11 w-11",
  };

  return profile.imageUrl ? (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={profile.imageUrl}
      alt=""
      className={cn(sizeClasses[size], "rounded-full border border-[var(--color-border)] object-cover shrink-0")}
    />
  ) : (
    <span
      aria-hidden="true"
      className={cn(
        getTypographyClassName("caption"),
        sizeClasses[size],
        "inline-flex items-center justify-center rounded-full bg-[var(--color-accent-wash)] text-[var(--color-on-surface)] shrink-0"
      )}
    >
      {initials(profile.name)}
    </span>
  );
}

function FormField({
  label,
  value,
  type = "text",
  onChange,
  disabled,
}: {
  label: string;
  value: string;
  type?: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  return (
    <label className="flex flex-col gap-2">
      <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>{label}</span>
      <input
        type={type}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        className={cn(
          getTypographyClassName("bodyMd"),
          "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:opacity-60"
        )}
      />
    </label>
  );
}

export function TravelDesignerManageDrawer({
  mode,
  brandId,
  profiles,
  editingProfile,
  onClose,
  onSaved,
  onMutate,
}: Props) {
  const [currentMode, setCurrentMode] = useState<TravelDesignerDrawerMode>(mode);
  const [editing, setEditing] = useState<TravelDesignerProfile | null>(editingProfile ?? null);
  const [draft, setDraft] = useState<TravelDesignerInput>(() =>
    editingProfile
      ? {
          name: editingProfile.name,
          email: editingProfile.email,
          phone: editingProfile.phone,
          imageAssetId: editingProfile.imageAssetId ?? null,
          imageUrl: editingProfile.imageUrl ?? null,
          imageR2Key: editingProfile.imageR2Key ?? null,
        }
      : blankDraft()
  );
  const [portraitFile, setPortraitFile] = useState<File | null>(null);
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);

  if (!currentMode) return null;

  const setDraftField = <K extends keyof TravelDesignerInput>(key: K, next: TravelDesignerInput[K]) =>
    setDraft((current) => ({ ...current, [key]: next }));

  const openEdit = (profile: TravelDesignerProfile) => {
    setEditing(profile);
    setDraft({
      name: profile.name,
      email: profile.email,
      phone: profile.phone,
      imageAssetId: profile.imageAssetId ?? null,
      imageUrl: profile.imageUrl ?? null,
      imageR2Key: profile.imageR2Key ?? null,
    });
    setPortraitFile(null);
    setCurrentMode("edit");
    setMessage("");
  };

  const saveProfile = async () => {
    if (!draft.name.trim() || !draft.email.trim()) {
      setMessage("Name and email are required.");
      return;
    }
    setPending(true);
    try {
      let saved = editing ? await updateTravelDesigner(editing.id, draft) : await createTravelDesigner(draft);
      if (portraitFile) {
        const uploaded = await uploadTravelDesignerPortrait(portraitFile, saved.id);
        saved = await updateTravelDesigner(saved.id, { ...draft, imageR2Key: uploaded.r2Key });
      }
      await onMutate();
      onSaved(saved);
      onClose();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Travel Designer could not be saved.");
    } finally {
      setPending(false);
    }
  };

  const toggleStatus = async (profile: TravelDesignerProfile) => {
    setPending(true);
    try {
      await updateTravelDesignerStatus(profile.id, !profile.isActive);
      await onMutate();
      setMessage("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Travel Designer status could not be changed.");
    } finally {
      setPending(false);
    }
  };

  const makeDefault = async (profile: TravelDesignerProfile) => {
    if (!brandId) {
      setMessage("Choose a brand before setting its default designer.");
      return;
    }
    setPending(true);
    try {
      await setTravelDesignerDefault(brandId, profile.id);
      setMessage(`${profile.name} is now the default for this brand.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Brand default could not be saved.");
    } finally {
      setPending(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={currentMode === "manage" ? "Manage Travel Designers" : "Travel Designer profile"}
      className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs"
    >
      <div className="h-full w-full max-w-xl overflow-y-auto border-l border-[var(--color-border-strong)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] sm:p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
              {currentMode === "manage"
                ? "Manage Travel Designers"
                : editing
                ? "Edit Travel Designer"
                : "Add Travel Designer"}
            </h2>
            <p className={cn(getTypographyClassName("bodySm"), "mt-1 text-[var(--color-muted)]")}>
              {currentMode === "manage"
                ? "Profiles are deactivated instead of deleted."
                : "This profile can be selected for future quotations."}
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
                className="flex flex-wrap items-center gap-3 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface-white)] p-3 shadow-2xs"
              >
                <ProfileAvatar profile={profile} />
                <div className="min-w-0 flex-1">
                  <p className={cn(getTypographyClassName("bodyMd"), "truncate text-[var(--color-on-surface)]")}>
                    {profile.name}
                  </p>
                  <p className={cn(getTypographyClassName("caption"), "truncate text-[var(--color-muted)]")}>
                    {profile.email} · {profile.isActive ? "Active" : "Inactive"}
                  </p>
                </div>
                <button
                  type="button"
                  disabled={pending}
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
                  disabled={pending}
                  onClick={() => void toggleStatus(profile)}
                  className={cn(
                    getTypographyClassName("buttonSecondary"),
                    profile.isActive
                      ? "min-h-10 rounded-[var(--radius-button)] bg-rose-700 !text-white hover:bg-rose-800 px-3 shadow-2xs border border-transparent transition-all cursor-pointer"
                      : "min-h-10 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-3 shadow-2xs border border-transparent transition-all cursor-pointer"
                  )}
                >
                  {profile.isActive ? "Deactivate" : "Reactivate"}
                </button>
                {profile.isActive ? (
                  <button
                    type="button"
                    disabled={pending || !brandId}
                    onClick={() => void makeDefault(profile)}
                    className={cn(
                      getTypographyClassName("buttonSecondary"),
                      "min-h-10 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] px-3 transition-all cursor-pointer"
                    )}
                  >
                    Set default
                  </button>
                ) : null}
              </article>
            ))}
          </div>
        ) : (
          <div className="mt-6 grid gap-4">
            <FormField label="Name" value={draft.name} onChange={(next) => setDraftField("name", next)} disabled={pending} />
            <FormField label="Email" type="email" value={draft.email} onChange={(next) => setDraftField("email", next)} disabled={pending} />
            <FormField label="Phone" value={draft.phone} onChange={(next) => setDraftField("phone", next)} disabled={pending} />
            <label className="flex flex-col gap-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Portrait</span>
              <input
                type="file"
                accept="image/*"
                disabled={pending}
                onChange={(event) => setPortraitFile(event.target.files?.[0] ?? null)}
                className={cn(getTypographyClassName("bodySm"), "min-h-11 text-[var(--color-on-surface)]")}
              />
              <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
                {portraitFile?.name ||
                  (draft.imageUrl ? "Current portrait kept until replaced." : "Optional shared media portrait.")}
              </span>
            </label>
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                disabled={pending}
                onClick={() => void saveProfile()}
                className={cn(
                  getTypographyClassName("buttonPrimary"),
                  "min-h-11 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-5 shadow-md border border-transparent transition-all disabled:opacity-50 cursor-pointer"
                )}
              >
                {pending ? "Saving…" : "Save designer"}
              </button>
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
            </div>
          </div>
        )}

        {message ? (
          <p aria-live="polite" className={cn(getTypographyClassName("bodySm"), "mt-4 text-[var(--color-muted)]")}>
            {message}
          </p>
        ) : null}
      </div>
    </div>
  );
}
