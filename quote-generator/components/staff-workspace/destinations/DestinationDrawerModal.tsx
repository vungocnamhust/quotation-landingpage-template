"use client";

import { useEffect, useMemo, useState, type KeyboardEvent } from "react";
import { X, Plus, MapPin, Globe, Compass, Tag, Folder } from "lucide-react";
import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";
import type { DestinationCatalogInput, DestinationProfile } from "../../../lib/quotationApi.ts";
import { generateSlug } from "./useDestinationManager.ts";
import MediaDrawer from "../../quotation-workspace/MediaDrawer.tsx";

interface Props {
  isOpen: boolean;
  editing: DestinationProfile | null;
  draft: DestinationCatalogInput;
  pending: boolean;
  message: string;
  onClose: () => void;
  onDraftChange: (draft: DestinationCatalogInput) => void;
  onSave: () => void;
}

const COUNTRY_OPTIONS = [
  { value: "vietnam", label: "Vietnam" },
  { value: "thailand", label: "Thailand" },
  { value: "cambodia", label: "Cambodia" },
  { value: "laos", label: "Laos" },
];

const REGION_OPTIONS = [
  { value: "north", label: "North" },
  { value: "central", label: "Central" },
  { value: "south", label: "South" },
  { value: "central-highlands", label: "Central Highlands" },
  { value: "mekong", label: "Mekong Delta" },
];

export function DestinationDrawerModal(props: Props) {
  const { isOpen, onClose, editing } = props;

  // Keyboard accessibility: ESC key to close
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Destination profile"
      className="fixed inset-0 z-50 flex justify-end bg-[color-mix(in_srgb,var(--color-contrast)_35%,transparent)]"
    >
      <DestinationDrawerModalContent key={editing?.id ?? "new"} {...props} />
    </div>
  );
}

function DestinationDrawerModalContent({
  editing,
  draft,
  pending,
  message,
  onClose,
  onDraftChange,
  onSave,
}: Props) {
  const [aliasInput, setAliasInput] = useState("");
  const [isSlugCustomized, setIsSlugCustomized] = useState(() => Boolean(editing));
  const [isFolderPickerOpen, setIsFolderPickerOpen] = useState(false);

  const defaultPrefix = useMemo(() => {
    const parts = [
      draft.countrySlug || "vietnam",
      draft.regionSlug,
      draft.provinceSlug,
      draft.slug || "destination",
    ].filter(Boolean);
    return `destination/${parts.join("/")}`;
  }, [draft.countrySlug, draft.regionSlug, draft.provinceSlug, draft.slug]);

  const handleNameChange = (name: string) => {
    if (!editing && !isSlugCustomized) {
      const autoSlug = generateSlug(name);
      onDraftChange({ ...draft, canonicalName: name, slug: autoSlug });
    } else {
      onDraftChange({ ...draft, canonicalName: name });
    }
  };

  const handleAddAlias = () => {
    const raw = aliasInput.trim().toLowerCase();
    if (!raw) return;
    // Support comma-separated batch input
    const parts = raw
      .split(",")
      .map((p) => p.trim())
      .filter((p) => Boolean(p) && !draft.aliases.includes(p));

    if (parts.length > 0) {
      onDraftChange({ ...draft, aliases: [...draft.aliases, ...parts] });
    }
    setAliasInput("");
  };

  const handleAliasKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      handleAddAlias();
    }
  };

  const handleRemoveAlias = (aliasToRemove: string) => {
    onDraftChange({
      ...draft,
      aliases: draft.aliases.filter((a) => a !== aliasToRemove),
    });
  };

  return (
    <section className="h-full w-full max-w-2xl overflow-y-auto border-l border-[var(--color-border-strong)] bg-[var(--color-surface)] p-6 shadow-[var(--elevation-card)] flex flex-col justify-between">
        <div>
          {/* Header */}
          <div className="flex items-start justify-between gap-4 border-b border-[var(--color-border)] pb-4">
            <div>
              <h2
                className={cn(
                  getTypographyClassName("cardTitle"),
                  "text-[var(--color-on-surface)]"
                )}
              >
                {editing ? "Edit Destination" : "Add Destination"}
              </h2>
              <p
                className={cn(
                  getTypographyClassName("bodySm"),
                  "mt-1 text-[var(--color-muted)]"
                )}
              >
                Configure primary destination details, coordinates, and search aliases.
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

          {/* Form Fields */}
          <div className="mt-6 flex flex-col gap-5">
            {/* Canonical Name */}
            <div className="flex flex-col gap-1.5">
              <label
                htmlFor="canonical-name-input"
                className={cn(getTypographyClassName("label"), "text-[var(--color-on-surface)]")}
              >
                Canonical Name <span className="text-[var(--color-accent)]">*</span>
              </label>
              <input
                id="canonical-name-input"
                type="text"
                value={draft.canonicalName}
                onChange={(e) => handleNameChange(e.target.value)}
                placeholder="e.g. Hanoi, Da Nang, Siem Reap"
                className={cn(
                  getTypographyClassName("bodyMd"),
                  "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3.5 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:border-[var(--color-accent)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-wash)]"
                )}
              />
              <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
                Official international English destination name.
              </span>
            </div>

            {/* Slug */}
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between">
                <label
                  htmlFor="slug-input"
                  className={cn(getTypographyClassName("label"), "text-[var(--color-on-surface)]")}
                >
                  Slug Identifier <span className="text-[var(--color-accent)]">*</span>
                </label>
                {editing ? (
                  <span
                    className={cn(
                      getTypographyClassName("caption"),
                      "rounded bg-[var(--color-surface-muted)] px-2 py-0.5 text-[var(--color-muted)]"
                    )}
                  >
                    Immutable
                  </span>
                ) : null}
              </div>
              <input
                id="slug-input"
                type="text"
                value={draft.slug}
                disabled={Boolean(editing)}
                onChange={(e) => {
                  setIsSlugCustomized(true);
                  onDraftChange({ ...draft, slug: e.target.value });
                }}
                placeholder="e.g. ha-noi, da-nang"
                className={cn(
                  getTypographyClassName("bodyMd"),
                  "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] px-3.5 font-mono",
                  editing
                    ? "cursor-not-allowed bg-[var(--color-surface-muted)] text-[var(--color-muted)]"
                    : "bg-[var(--color-surface)] text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:border-[var(--color-accent)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-wash)]"
                )}
              />
              <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
                Unique URL slug identifier. Cannot be modified after creation.
              </span>
            </div>

            {/* Country & Region Grid */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {/* Country */}
              <div className="flex flex-col gap-1.5">
                <label
                  htmlFor="country-select"
                  className={cn(
                    getTypographyClassName("label"),
                    "flex items-center gap-1 text-[var(--color-on-surface)]"
                  )}
                >
                  <Globe size={13} className="text-[var(--color-muted)]" />
                  <span>Country</span>
                </label>
                <select
                  id="country-select"
                  value={draft.countrySlug ?? ""}
                  onChange={(e) =>
                    onDraftChange({
                      ...draft,
                      countrySlug: e.target.value || null,
                    })
                  }
                  className={cn(
                    getTypographyClassName("bodyMd"),
                    "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] focus:border-[var(--color-accent)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-wash)]"
                  )}
                >
                  <option value="">-- None --</option>
                  {COUNTRY_OPTIONS.map((c) => (
                    <option key={c.value} value={c.value}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Region */}
              <div className="flex flex-col gap-1.5">
                <label
                  htmlFor="region-input"
                  className={cn(
                    getTypographyClassName("label"),
                    "flex items-center gap-1 text-[var(--color-on-surface)]"
                  )}
                >
                  <Compass size={13} className="text-[var(--color-muted)]" />
                  <span>Region</span>
                </label>
                <input
                  id="region-input"
                  type="text"
                  list="region-presets"
                  value={draft.regionSlug ?? ""}
                  onChange={(e) =>
                    onDraftChange({
                      ...draft,
                      regionSlug: e.target.value || null,
                    })
                  }
                  placeholder="e.g. north, central, south"
                  className={cn(
                    getTypographyClassName("bodyMd"),
                    "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3.5 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:border-[var(--color-accent)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-wash)]"
                  )}
                />
                <datalist id="region-presets">
                  {REGION_OPTIONS.map((r) => (
                    <option key={r.value} value={r.value}>
                      {r.label}
                    </option>
                  ))}
                </datalist>
              </div>
            </div>

            {/* Province */}
            <div className="flex flex-col gap-1.5">
              <label
                htmlFor="province-input"
                className={cn(getTypographyClassName("label"), "text-[var(--color-on-surface)]")}
              >
                Province / City
              </label>
              <input
                id="province-input"
                type="text"
                value={draft.provinceSlug ?? ""}
                onChange={(e) =>
                  onDraftChange({
                    ...draft,
                    provinceSlug: e.target.value || null,
                  })
                }
                placeholder="e.g. ha-noi, da-nang, quang-nam"
                className={cn(
                  getTypographyClassName("bodyMd"),
                  "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3.5 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:border-[var(--color-accent)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-wash)]"
                )}
              />
            </div>

            {/* GPS Coordinates */}
            <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4">
              <div className="flex items-center gap-1.5 text-[var(--color-accent)] mb-3">
                <MapPin size={15} />
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-on-surface)]")}>
                  GPS Coordinates <span className="text-[var(--color-accent)]">*</span>
                </span>
              </div>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="flex flex-col gap-1">
                  <label
                    htmlFor="latitude-input"
                    className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}
                  >
                    Latitude (-90 to 90)
                  </label>
                  <input
                    id="latitude-input"
                    type="number"
                    step="0.0001"
                    min="-90"
                    max="90"
                    value={draft.latitude}
                    onChange={(e) =>
                      onDraftChange({
                        ...draft,
                        latitude: parseFloat(e.target.value) || 0,
                      })
                    }
                    className={cn(
                      getTypographyClassName("bodyMd"),
                      "min-h-10 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 font-mono text-[var(--color-on-surface)] focus:border-[var(--color-accent)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-wash)]"
                    )}
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label
                    htmlFor="longitude-input"
                    className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}
                  >
                    Longitude (-180 to 180)
                  </label>
                  <input
                    id="longitude-input"
                    type="number"
                    step="0.0001"
                    min="-180"
                    max="180"
                    value={draft.longitude}
                    onChange={(e) =>
                      onDraftChange({
                        ...draft,
                        longitude: parseFloat(e.target.value) || 0,
                      })
                    }
                    className={cn(
                      getTypographyClassName("bodyMd"),
                      "min-h-10 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 font-mono text-[var(--color-on-surface)] focus:border-[var(--color-accent)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-wash)]"
                    )}
                  />
                </div>
              </div>
              <span
                className={cn(
                  getTypographyClassName("caption"),
                  "mt-2 block text-[var(--color-muted)]"
                )}
              >
                Required for interactive map routing and distance calculations.
              </span>
            </div>

            {/* Tourism Hub hierarchy (15.2b) */}
            <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4">
              <div className="flex items-center gap-1.5 text-[var(--color-accent)] mb-3">
                <Compass size={15} />
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-on-surface)]")}>
                  Tourism Hub
                </span>
              </div>

              {editing?.mergedIntoId ? (
                <div
                  className={cn(
                    getTypographyClassName("bodyMd"),
                    "mb-3 rounded-[var(--radius-button)] border border-[color-mix(in_srgb,var(--color-accent)_35%,transparent)] bg-[var(--color-accent-wash)] px-3.5 py-2.5 text-[var(--color-accent)]"
                  )}
                >
                  This destination has been merged into{" "}
                  <span className="font-mono">{editing.mergedIntoId}</span>. It stays read-only history — old
                  quotations and media keep pointing here.
                </div>
              ) : null}

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="flex flex-col gap-1">
                  <label
                    htmlFor="destination-type-input"
                    className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}
                  >
                    Destination type
                  </label>
                  <select
                    id="destination-type-input"
                    value={draft.destinationType ?? "city"}
                    onChange={(e) =>
                      onDraftChange({
                        ...draft,
                        destinationType: e.target.value as DestinationCatalogInput["destinationType"],
                      })
                    }
                    className={cn(
                      getTypographyClassName("bodyMd"),
                      "min-h-10 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] focus:border-[var(--color-accent)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-wash)]"
                    )}
                  >
                    <option value="country">Country</option>
                    <option value="region">Region</option>
                    <option value="province">Province</option>
                    <option value="city">City</option>
                    <option value="sub_zone">Sub-zone</option>
                  </select>
                </div>
                <div className="flex flex-col gap-1">
                  <label
                    htmlFor="parent-id-input"
                    className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}
                  >
                    Parent destination id (optional)
                  </label>
                  <input
                    id="parent-id-input"
                    type="text"
                    value={draft.parentId ?? ""}
                    onChange={(e) => onDraftChange({ ...draft, parentId: e.target.value.trim() || null })}
                    placeholder="e.g. dst_quang-ninh"
                    className={cn(
                      getTypographyClassName("bodyMd"),
                      "min-h-10 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 font-mono text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:border-[var(--color-accent)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-wash)]"
                    )}
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label
                    htmlFor="country-code-input"
                    className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}
                  >
                    ISO country code
                  </label>
                  <input
                    id="country-code-input"
                    type="text"
                    maxLength={2}
                    value={draft.countryCode ?? ""}
                    onChange={(e) =>
                      onDraftChange({ ...draft, countryCode: e.target.value.trim().toUpperCase() || null })
                    }
                    placeholder="VN"
                    className={cn(
                      getTypographyClassName("bodyMd"),
                      "min-h-10 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 font-mono text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:border-[var(--color-accent)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-wash)]"
                    )}
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label
                    htmlFor="iata-code-input"
                    className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}
                  >
                    IATA code (optional, not unique)
                  </label>
                  <input
                    id="iata-code-input"
                    type="text"
                    maxLength={3}
                    value={draft.iataCode ?? ""}
                    onChange={(e) => onDraftChange({ ...draft, iataCode: e.target.value.trim().toUpperCase() || null })}
                    placeholder="HAN"
                    className={cn(
                      getTypographyClassName("bodyMd"),
                      "min-h-10 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 font-mono text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:border-[var(--color-accent)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-wash)]"
                    )}
                  />
                </div>
                <div className="flex flex-col gap-1 sm:col-span-2">
                  <label
                    htmlFor="timezone-input"
                    className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}
                  >
                    IANA timezone
                  </label>
                  <input
                    id="timezone-input"
                    type="text"
                    value={draft.timezone ?? ""}
                    onChange={(e) => onDraftChange({ ...draft, timezone: e.target.value.trim() })}
                    placeholder="Asia/Ho_Chi_Minh"
                    className={cn(
                      getTypographyClassName("bodyMd"),
                      "min-h-10 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 font-mono text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:border-[var(--color-accent)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-wash)]"
                    )}
                  />
                </div>
              </div>
            </div>

            {/* R2 Media Folder Prefix */}
            <div className="flex flex-col gap-2 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4">
              <div className="flex items-center justify-between gap-2">
                <label
                  className={cn(
                    getTypographyClassName("label"),
                    "flex items-center gap-1.5 text-[var(--color-on-surface)]"
                  )}
                >
                  <Folder size={14} className="text-[var(--color-accent)]" />
                  <span>R2 Media Folder Prefix</span>
                </label>
                <span
                  className={cn(
                    getTypographyClassName("caption"),
                    "rounded-full px-2 py-0.5 border shrink-0",
                    draft.mediaPrefix
                      ? "bg-[var(--color-accent-wash)] text-[var(--color-accent)] border-[color-mix(in_srgb,var(--color-accent)_30%,transparent)]"
                      : "bg-[var(--color-surface)] text-[var(--color-muted)] border-[var(--color-border)]"
                  )}
                >
                  {draft.mediaPrefix ? "Custom Folder" : "Default Convention"}
                </span>
              </div>

              {/* Frozen / Read-only Display Box */}
              <div className="flex min-h-11 items-center justify-between gap-3 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3.5 py-2">
                <div className="flex items-center gap-2 min-w-0">
                  <Folder size={15} className="shrink-0 text-[var(--color-muted)]" />
                  <span
                    className={cn(
                      getTypographyClassName("bodyMd"),
                      "font-mono truncate",
                      draft.mediaPrefix ? "text-[var(--color-accent)]" : "text-[var(--color-on-surface)]"
                    )}
                    title={draft.mediaPrefix || defaultPrefix}
                  >
                    {draft.mediaPrefix || defaultPrefix}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  {draft.mediaPrefix ? (
                    <button
                      type="button"
                      onClick={() => onDraftChange({ ...draft, mediaPrefix: null })}
                      className={cn(
                        getTypographyClassName("caption"),
                        "rounded-[calc(var(--radius-button)-4px)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-2 py-1 text-[var(--color-muted)] hover:text-[var(--color-on-surface)] transition-colors cursor-pointer"
                      )}
                      title="Reset to standard taxonomy folder convention"
                    >
                      Reset to Default
                    </button>
                  ) : null}
                  <button
                    type="button"
                    onClick={() => setIsFolderPickerOpen(true)}
                    className={cn(
                      getTypographyClassName("buttonSecondary"),
                      "flex items-center gap-1 rounded-[calc(var(--radius-button)-2px)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 py-1 text-[var(--color-on-surface)] hover:bg-[var(--color-surface-hover)] cursor-pointer"
                    )}
                  >
                    <Folder size={13} />
                    <span>Browse R2 Folders</span>
                  </button>
                </div>
              </div>

              <span
                className={cn(
                  getTypographyClassName("caption"),
                  "text-[var(--color-muted)]"
                )}
              >
                {draft.mediaPrefix
                  ? "Custom folder configured. Images will be prioritized from this Cloudflare R2 path."
                  : "Using standard folder convention inferred from country, region, province, and slug."}
              </span>
            </div>

            {/* Folder Picker Modal */}
            <MediaDrawer
              open={isFolderPickerOpen}
              onClose={() => setIsFolderPickerOpen(false)}
              mode="folder"
              initialPrefix={draft.mediaPrefix || defaultPrefix}
              onSelectFolder={(folder) => {
                onDraftChange({ ...draft, mediaPrefix: folder ? folder.trim() : null });
                setIsFolderPickerOpen(false);
              }}
            />

            {/* Aliases Tag Manager */}
            <div className="flex flex-col gap-2">
              <label
                htmlFor="alias-input"
                className={cn(
                  getTypographyClassName("label"),
                  "flex items-center gap-1.5 text-[var(--color-on-surface)]"
                )}
              >
                <Tag size={13} className="text-[var(--color-muted)]" />
                <span>Search Aliases & Variations</span>
              </label>

              {/* Tag Chips */}
              <div className="flex flex-wrap gap-1.5 min-h-8">
                {draft.aliases.map((alias) => (
                  <span
                    key={alias}
                    className={cn(
                      getTypographyClassName("caption"),
                      "inline-flex items-center gap-1 rounded-full border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-2.5 py-1 text-[var(--color-on-surface)]"
                    )}
                  >
                    <span>{alias}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveAlias(alias)}
                      className="ml-0.5 rounded-full p-0.5 text-[var(--color-muted)] hover:bg-[var(--color-surface)] hover:text-[var(--color-accent)] transition-colors cursor-pointer"
                      aria-label={`Remove alias ${alias}`}
                    >
                      <X size={11} aria-hidden="true" />
                    </button>
                  </span>
                ))}
              </div>

              {/* Add Alias Input */}
              <div className="flex gap-2">
                <input
                  id="alias-input"
                  type="text"
                  value={aliasInput}
                  onChange={(e) => setAliasInput(e.target.value)}
                  onKeyDown={handleAliasKeyDown}
                  placeholder="Type an alias and press Enter or comma…"
                  className={cn(
                    getTypographyClassName("bodySm"),
                    "min-h-10 flex-1 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:border-[var(--color-accent)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-wash)]"
                  )}
                />
                <button
                  type="button"
                  onClick={handleAddAlias}
                  className={cn(
                    getTypographyClassName("buttonSecondary"),
                    "flex items-center gap-1 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 py-1.5 text-[var(--color-on-surface)] hover:bg-[var(--color-surface-hover)] cursor-pointer"
                  )}
                >
                  <Plus size={14} />
                  <span>Add</span>
                </button>
              </div>
              <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
                Used for autocomplete matching (e.g. &ldquo;HCMC&rdquo;, &ldquo;Sai Gon&rdquo;, &ldquo;Saigon&rdquo; for Ho Chi Minh City).
              </span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 border-t border-[var(--color-border)] pt-4">
          <div className="flex items-center justify-end gap-3">
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
              {pending ? "Saving…" : editing ? "Save Changes" : "Create Destination"}
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
        </div>
      </section>
  );
}

