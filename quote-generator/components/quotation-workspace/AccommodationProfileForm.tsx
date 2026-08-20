"use client";

import { useState } from "react";
import { Image as ImageIcon, X, Upload } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import type { AccommodationProfileInput } from "../../lib/quotationApi.ts";
import { DestinationSelect } from "../destination/DestinationSelect.tsx";
import type { DestinationRef } from "../destination/types.ts";
import MediaDrawer from "./MediaDrawer.tsx";
import { RichTextEditor } from "../ui/RichTextEditor.tsx";

const inputClass = cn(
  getTypographyClassName("bodyMd"),
  "min-h-11 w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)]"
);

export type AccommodationProfileFormProps = {
  draft: AccommodationProfileInput;
  destinationRef: DestinationRef | null;
  profileId: string | null;
  onChange: (next: AccommodationProfileInput) => void;
  onDestinationChange: (next: DestinationRef | null) => void;
  onUpload: (target: "hotel_asset" | "room_asset", file: File) => void;
};

export default function AccommodationProfileForm({
  draft,
  destinationRef,
  profileId,
  onChange,
  onDestinationChange,
  onUpload,
}: AccommodationProfileFormProps) {
  const [activeMediaTarget, setActiveMediaTarget] = useState<
    "hotel_asset" | "room_asset" | null
  >(null);

  const set = <K extends keyof AccommodationProfileInput>(
    key: K,
    value: AccommodationProfileInput[K]
  ) => onChange({ ...draft, [key]: value });

  return (
    <div className="mt-5 grid gap-3 sm:grid-cols-2">
      <div className="sm:col-span-2">
        <DestinationSelect
          label="Accommodation destination"
          value={destinationRef?.name ?? null}
          onChange={(_name, ref) => onDestinationChange(ref ?? null)}
        />
      </div>
      <label className="flex flex-col gap-1.5">
        <span
          className={cn(
            getTypographyClassName("label"),
            "text-[var(--color-muted)]"
          )}
        >
          Accommodation name
        </span>
        <input
          className={inputClass}
          value={draft.name}
          onChange={(event) => set("name", event.target.value)}
        />
      </label>
      <label className="flex flex-col gap-1.5">
        <span
          className={cn(
            getTypographyClassName("label"),
            "text-[var(--color-muted)]"
          )}
        >
          Room type
        </span>
        <input
          className={inputClass}
          value={draft.room_type ?? ""}
          onChange={(event) => set("room_type", event.target.value || null)}
        />
      </label>
      <label className="flex flex-col gap-1.5">
        <span
          className={cn(
            getTypographyClassName("label"),
            "text-[var(--color-muted)]"
          )}
        >
          Phone
        </span>
        <input
          className={inputClass}
          value={draft.phone ?? ""}
          onChange={(event) => set("phone", event.target.value || null)}
        />
      </label>
      <label className="flex flex-col gap-1.5">
        <span
          className={cn(
            getTypographyClassName("label"),
            "text-[var(--color-muted)]"
          )}
        >
          Display city
        </span>
        <input
          className={inputClass}
          value={draft.display_city ?? ""}
          onChange={(event) => set("display_city", event.target.value || null)}
        />
      </label>
      <label className="sm:col-span-2 flex flex-col gap-1.5">
        <span
          className={cn(
            getTypographyClassName("label"),
            "text-[var(--color-muted)]"
          )}
        >
          Introduction
        </span>
        <RichTextEditor
          value={draft.intro ?? ""}
          minHeight="5rem"
          onChange={(val) => set("intro", val || null)}
        />
      </label>

      {/* Property Media Asset Configuration Section */}
      <div className="sm:col-span-2 grid gap-4 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 sm:grid-cols-2">
        {(["hotel_asset", "room_asset"] as const).map((target) => {
          const isSelected = Boolean(draft[target]);
          return (
            <div key={target} className="flex flex-col gap-2">
              <span
                className={cn(
                  getTypographyClassName("label"),
                  "text-[var(--color-muted)]"
                )}
              >
                {target === "hotel_asset" ? "Hotel exterior image" : "Room interior image"}
              </span>

              <div className="flex items-center justify-between gap-2 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] px-3 py-2">
                <span
                  className={cn(
                    getTypographyClassName("caption"),
                    "truncate text-[var(--color-on-surface)]"
                  )}
                >
                  {draft[target] || "No catalog asset selected"}
                </span>

                {isSelected ? (
                  <button
                    type="button"
                    onClick={() => set(target, null)}
                    className="shrink-0 p-1 text-[var(--color-muted)] transition-colors hover:text-rose-600"
                    title="Clear asset"
                  >
                    <X size={16} />
                  </button>
                ) : null}
              </div>

              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setActiveMediaTarget(target)}
                  className={cn(
                    getTypographyClassName("buttonSecondary"),
                    "flex min-h-10 items-center gap-1.5 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] transition-all hover:bg-[var(--color-surface-hover)]"
                  )}
                >
                  <ImageIcon size={15} />
                  <span>Choose from Library</span>
                </button>

                {profileId ? (
                  <label
                    className={cn(
                      getTypographyClassName("buttonSecondary"),
                      "flex min-h-10 cursor-pointer items-center gap-1.5 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] transition-all hover:bg-[var(--color-surface-hover)]"
                    )}
                  >
                    <Upload size={15} />
                    <span>Upload file</span>
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      onChange={(event) => {
                        const file = event.target.files?.[0];
                        if (file) onUpload(target, file);
                      }}
                      className="hidden"
                    />
                  </label>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>

      {/* R2 Media Library Picker Drawer */}
      <MediaDrawer
        open={activeMediaTarget !== null}
        onClose={() => setActiveMediaTarget(null)}
        selectionMode="single"
        initialSelection={
          activeMediaTarget && draft[activeMediaTarget]
            ? [draft[activeMediaTarget]!]
            : []
        }
        context={
          destinationRef?.id
            ? {
                kind: "accommodation",
                destinationId: destinationRef.id,
                accommodationName: draft.name || undefined,
                accommodationKind: "hotel",
              }
            : undefined
        }
        onConfirm={(keys) => {
          if (activeMediaTarget && keys[0]) {
            set(activeMediaTarget, keys[0]);
          }
          setActiveMediaTarget(null);
        }}
        onSelect={(r2Key) => {
          if (activeMediaTarget && r2Key) {
            set(activeMediaTarget, r2Key);
          }
          setActiveMediaTarget(null);
        }}
      />
    </div>
  );
}
