"use client";

import { useDeferredValue, useMemo, useState } from "react";
import useSWR from "swr";
import { Plus, Search, Building2, MapPin, Calendar, Phone, CheckCircle2, XCircle } from "lucide-react";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";
import {
  createAccommodation,
  listAccommodations,
  updateAccommodation,
  updateAccommodationStatus,
  uploadAccommodationAsset,
  type AccommodationProfile,
  type AccommodationProfileInput,
} from "../../lib/quotationApi";
import AccommodationProfileForm from "../quotation-workspace/AccommodationProfileForm";
import type { DestinationRef } from "../quotation-workspace/DestinationInputs";

const blankInput = (): AccommodationProfileInput => ({
  destinationId: "",
  name: "",
  room_type: null,
  check_in: null,
  check_out: null,
  intro: null,
  phone: null,
  display_city: null,
  display_date: null,
  hotel_asset: null,
  room_asset: null,
});

function profileInput(profile: AccommodationProfile): AccommodationProfileInput {
  return {
    destinationId: profile.destination_id,
    name: profile.name,
    room_type: profile.room_type,
    check_in: profile.check_in,
    check_out: profile.check_out,
    intro: profile.intro,
    phone: profile.phone,
    display_city: profile.display_city,
    display_date: profile.display_date,
    hotel_asset: profile.hotel_asset,
    room_asset: profile.room_asset,
  };
}

export default function WorkspaceAccommodationList() {
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState<"all" | "true" | "false">("all");
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<AccommodationProfile | null>(null);
  const [draft, setDraft] = useState<AccommodationProfileInput>(blankInput);
  const [destinationRef, setDestinationRef] = useState<DestinationRef | null>(null);
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);

  const deferredSearch = useDeferredValue(search);

  const queryKey = ["accommodations", activeFilter, deferredSearch];
  const {
    data: profileResponse,
    error,
    isLoading,
    mutate: mutateProfiles,
  } = useSWR(queryKey, ([, active, query]) =>
    listAccommodations({ active: active as "true" | "false" | "all", query })
  );

  const profiles = useMemo(() => profileResponse?.items ?? [], [profileResponse]);

  const openCreate = () => {
    setEditing(null);
    setDraft(blankInput());
    setDestinationRef(null);
    setMessage("");
    setIsDrawerOpen(true);
  };

  const openEdit = (profile: AccommodationProfile) => {
    setEditing(profile);
    setDraft(profileInput(profile));
    setDestinationRef(profile.destination_ref);
    setMessage("");
    setIsDrawerOpen(true);
  };

  const save = async () => {
    if (!destinationRef || !draft.name.trim()) {
      setMessage("Destination and accommodation name are required.");
      return;
    }
    setPending(true);
    try {
      const input = { ...draft, destinationId: destinationRef.id };
      if (editing) {
        await updateAccommodation(editing.id, input);
      } else {
        await createAccommodation(input);
      }
      await mutateProfiles();
      setIsDrawerOpen(false);
    } catch (err) {
      setMessage(
        err instanceof Error ? err.message : "Accommodation could not be saved."
      );
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
      setMessage("Asset uploaded. Save profile to confirm modifications.");
    } catch (err) {
      setMessage(
        err instanceof Error ? err.message : "Accommodation asset could not be uploaded."
      );
    } finally {
      setPending(false);
    }
  };

  const toggleStatus = async (profile: AccommodationProfile) => {
    setPending(true);
    try {
      await updateAccommodationStatus(profile.id, !profile.is_active);
      await mutateProfiles();
    } catch (err) {
      setMessage(
        err instanceof Error ? err.message : "Status update failed."
      );
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Top Action Bar & Filters */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-3">
          {/* Search Box */}
          <div className="relative min-w-[16rem] flex-1 sm:w-80 sm:flex-none">
            <Search
              size={18}
              className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--color-muted)]"
            />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search accommodations…"
              className={cn(
                getTypographyClassName("bodyMd"),
                "min-h-11 w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] pl-10 pr-4 text-[var(--color-on-surface)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)]"
              )}
            />
          </div>

          {/* Status Filter Pills */}
          <div className="flex items-center rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] p-1 shadow-2xs">
            {(
              [
                { label: "All", value: "all" },
                { label: "Active", value: "true" },
                { label: "Inactive", value: "false" },
              ] as const
            ).map((tab) => (
              <button
                key={tab.value}
                type="button"
                onClick={() => setActiveFilter(tab.value)}
                className={cn(
                  getTypographyClassName("caption"),
                  "rounded-[calc(var(--radius-button)-2px)] px-3 py-1.5 transition-all",
                  activeFilter === tab.value
                    ? "bg-[var(--color-contrast)] text-white shadow-2xs"
                    : "text-[var(--color-muted)] hover:text-[var(--color-on-surface)]"
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* New Accommodation Button */}
        <button
          type="button"
          onClick={openCreate}
          className={cn(
            getTypographyClassName("buttonPrimary"),
            "flex items-center justify-center gap-2 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-4 py-2.5 text-white shadow-xs transition-all hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)]"
          )}
        >
          <Plus size={18} />
          <span>Add accommodation</span>
        </button>
      </div>

      {/* Main Grid / Catalog Display */}
      {error ? (
        <div className="rounded-[var(--radius-card)] border border-rose-200 bg-rose-50/50 p-6 text-center text-rose-700">
          <p className={getTypographyClassName("bodyMd")}>
            Failed to load accommodation catalog. Please try refreshing.
          </p>
        </div>
      ) : isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((idx) => (
            <div
              key={idx}
              className="h-48 animate-pulse rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5"
            />
          ))}
        </div>
      ) : profiles.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-[var(--radius-card)] border border-dashed border-[var(--color-border-strong)] bg-[var(--color-surface)] p-12 text-center">
          <Building2 size={40} className="mb-3 text-[var(--color-muted)]" />
          <h3
            className={cn(
              getTypographyClassName("cardTitle"),
              "text-[var(--color-on-surface)]"
            )}
          >
            No accommodations found
          </h3>
          <p
            className={cn(
              getTypographyClassName("bodySm"),
              "mt-1 max-w-sm text-[var(--color-muted)]"
            )}
          >
            {search
              ? "No accommodations match your search query."
              : "Start by adding your first accommodation profile to the catalog."}
          </p>
          <button
            type="button"
            onClick={openCreate}
            className={cn(
              getTypographyClassName("buttonSecondary"),
              "mt-4 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-4 py-2 text-white shadow-xs transition-all hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)]"
            )}
          >
            Add accommodation
          </button>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {profiles.map((profile) => (
            <article
              key={profile.id}
              className="flex flex-col justify-between rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] transition-all hover:border-[var(--color-border-strong)]"
            >
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
                      <MapPin size={14} className="shrink-0" />
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
                        ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400"
                        : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                    )}
                  >
                    {profile.is_active ? (
                      <CheckCircle2 size={12} />
                    ) : (
                      <XCircle size={12} />
                    )}
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
                      <span className="text-[var(--color-on-surface)]">
                        Room type:
                      </span>
                      <span className="truncate">{profile.room_type}</span>
                    </div>
                  ) : null}

                  {profile.check_in || profile.check_out ? (
                    <div className="flex items-center gap-1.5">
                      <Calendar size={13} className="shrink-0" />
                      <span>
                        In: {profile.check_in || "N/A"} · Out:{" "}
                        {profile.check_out || "N/A"}
                      </span>
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
                  onClick={() => openEdit(profile)}
                  className={cn(
                    getTypographyClassName("buttonSecondary"),
                    "rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 py-1.5 text-[var(--color-on-surface)] transition-all hover:bg-[var(--color-surface-hover)]"
                  )}
                >
                  Edit
                </button>

                <button
                  type="button"
                  onClick={() => void toggleStatus(profile)}
                  className={cn(
                    getTypographyClassName("caption"),
                    "rounded-[var(--radius-button)] px-3 py-1.5 transition-all",
                    profile.is_active
                      ? "text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30"
                      : "text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/30"
                  )}
                >
                  {profile.is_active ? "Deactivate" : "Activate"}
                </button>
              </div>
            </article>
          ))}
        </div>
      )}

      {/* Edit/Create Drawer Modal */}
      {isDrawerOpen ? (
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
                onClick={() => setIsDrawerOpen(false)}
                className={cn(
                  getTypographyClassName("buttonSecondary"),
                  "rounded-[var(--radius-button)] bg-[var(--color-contrast)] px-3.5 py-2 text-white shadow-2xs transition-all hover:opacity-90"
                )}
              >
                Close
              </button>
            </div>

            <AccommodationProfileForm
              draft={draft}
              destinationRef={destinationRef}
              profileId={editing?.id ?? null}
              onChange={setDraft}
              onDestinationChange={setDestinationRef}
              onUpload={(target, file) => void upload(target, file)}
            />

            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setIsDrawerOpen(false)}
                className={cn(
                  getTypographyClassName("buttonSecondary"),
                  "rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-4 py-2.5 text-[var(--color-on-surface)] hover:bg-[var(--color-surface-hover)]"
                )}
              >
                Cancel
              </button>

              <button
                type="button"
                disabled={pending}
                onClick={() => void save()}
                className={cn(
                  getTypographyClassName("buttonPrimary"),
                  "rounded-[var(--radius-button)] bg-[var(--color-accent)] px-5 py-2.5 text-white shadow-md transition-all hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] disabled:opacity-50"
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
      ) : null}
    </div>
  );
}
