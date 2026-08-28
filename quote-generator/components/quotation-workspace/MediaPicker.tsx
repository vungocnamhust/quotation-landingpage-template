"use client";

/* R2 previews are thumbnail-sized runtime assets, so Next image optimization is intentionally bypassed. */
/* eslint-disable @next/next/no-img-element */

import { useRef, useState, type KeyboardEvent } from "react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import { normalizeSelection, validateCardinality } from "../../lib/rules/mediaSlotReconciler.ts";
import { useMediaLibrarySearch, type MediaLibraryItem } from "./useMediaLibrarySearch.ts";

export type MediaPickerContext = {
  kind: "destination" | "accommodation" | "team";
  destinationId?: string;
  accommodationName?: string;
  accommodationKind?: "hotel" | "cruise";
  travelDesignerId?: string;
};

export type MediaPickerSize = "sm" | "md" | "lg";
export type MediaPickerVariant = "default" | "compact" | "inline";

export type MediaPickerProps = {
  onSelect?: (r2Key: string) => void;
  onConfirm?: (r2Keys: string[]) => void;
  onSelectFolder?: (folderPrefix: string) => void;
  mode?: "asset" | "folder";
  context?: MediaPickerContext;
  selectionMode?: "single" | "multiple";
  maxSelection?: number;
  minSelection?: number;
  initialSelection?: string[];
  initialPrefix?: string;
  size?: MediaPickerSize;
  variant?: MediaPickerVariant;
};

const GRID_COLUMNS_BY_SIZE: Record<MediaPickerSize, string> = {
  sm: "sm:grid-cols-3 lg:grid-cols-4",
  md: "sm:grid-cols-2 lg:grid-cols-3",
  lg: "sm:grid-cols-2",
};
const THUMBNAIL_HEIGHT_BY_SIZE: Record<MediaPickerSize, string> = {
  sm: "h-20",
  md: "h-28",
  lg: "h-40",
};

export default function MediaPicker({
  onSelect,
  onConfirm,
  onSelectFolder,
  mode = "asset",
  context,
  selectionMode = "single",
  maxSelection = 1,
  minSelection = 0,
  initialSelection = [],
  initialPrefix,
  size = "md",
  variant = "default",
}: MediaPickerProps) {
  const isFolderMode = mode === "folder";
  const [selected, setSelected] = useState<string[]>(initialSelection);
  const [focusedKey, setFocusedKey] = useState<string | null>(null);
  const tileRefs = useRef(new Map<string, HTMLDivElement>());

  const toggle = (r2Key: string) => setSelected((current) => {
    if (selectionMode === "single") return [r2Key];
    if (current.includes(r2Key)) return current.filter((key) => key !== r2Key);
    return current.length >= maxSelection ? current : [...current, r2Key];
  });

  const {
    prefix, query, deferredQuery, crumbs, items, folders, nextCursor, error,
    message, statusText, activeSync, pending, canUpload, file, setFile,
    setCursor, setQuery, navigate, refreshFromR2, upload, mutate,
  } = useMediaLibrarySearch({
    initialPrefix,
    context,
    isFolderMode,
    onUploaded: (uploadedKey) => setSelected(selectionMode === "single" ? [uploadedKey] : (current) => current.includes(uploadedKey) ? current : [...current, uploadedKey].slice(0, maxSelection)),
  });

  const cardinalityError = isFolderMode ? null : validateCardinality({ minItems: minSelection, maxItems: maxSelection }, normalizeSelection(selected));
  const confirm = () => {
    if (isFolderMode) {
      if (onSelectFolder) onSelectFolder(prefix);
      return;
    }
    if (!selected.length || cardinalityError) return;
    if (onConfirm) onConfirm(selected);
    else if (onSelect) selected.forEach(onSelect);
  };

  const focusTile = (r2Key: string) => {
    setFocusedKey(r2Key);
    tileRefs.current.get(r2Key)?.focus();
  };
  const onTileKeyDown = (event: KeyboardEvent<HTMLDivElement>, index: number, item: MediaLibraryItem) => {
    if (isFolderMode) return;
    const columns = size === "sm" ? 4 : size === "lg" ? 2 : 3;
    const moveBy = (delta: number) => {
      const next = items[index + delta];
      if (next) { event.preventDefault(); focusTile(next.r2Key); }
    };
    switch (event.key) {
      case "Enter":
      case " ":
        event.preventDefault();
        toggle(item.r2Key);
        return;
      case "ArrowRight":
        moveBy(1);
        return;
      case "ArrowLeft":
        moveBy(-1);
        return;
      case "ArrowDown":
        moveBy(columns);
        return;
      case "ArrowUp":
        moveBy(-columns);
        return;
      default:
        return;
    }
  };

  const compact = variant === "compact";
  const inline = variant === "inline";

  return <section className={cn(
    "flex flex-col gap-4",
    inline ? "" : "rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] shadow-2xs",
    inline ? "" : compact ? "p-3" : "p-5"
  )}>
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <p className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
          {isFolderMode ? "R2 Folder Navigator" : "Media library"}
        </p>
        {compact ? null : (
          <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
            {isFolderMode
              ? "Browse Cloudflare R2 folder tree to choose the asset directory for this item."
              : "Only the selected R2 key is saved to the quotation document."}
          </p>
        )}
      </div>
      <button type="button" disabled={pending || activeSync} onClick={refreshFromR2} className={cn(getTypographyClassName("buttonSecondary"), "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] px-4 transition-all disabled:opacity-50")}>{activeSync ? "Refreshing R2…" : "Refresh from R2"}</button>
    </div>
    <p aria-live="polite" className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>{statusText}</p>
    {canUpload ? <div className="flex flex-wrap items-center gap-3"><input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => setFile(event.target.files?.[0] ?? null)} className={cn(getTypographyClassName("bodySm"), "min-h-11 text-[var(--color-on-surface)]")} /><button type="button" disabled={!file || pending} onClick={upload} className={cn(getTypographyClassName("buttonPrimary"), "min-h-11 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-4 shadow-md border border-transparent transition-all disabled:opacity-50")}>Upload to this location</button></div> : context && !isFolderMode ? <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>Complete the linked destination, accommodation or designer before uploading.</p> : null}
    {message ? <p aria-live="polite" className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>{message}</p> : null}
    {error ? <div className="flex flex-wrap items-center gap-3"><p role="alert" className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>{error instanceof Error ? error.message : "Media library could not be loaded."}</p><button type="button" onClick={() => void mutate()} className={cn(getTypographyClassName("buttonSecondary"), "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] px-3 transition-all")}>Retry</button></div> : null}
    <label className="flex flex-col gap-2"><span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Search this folder</span><input value={query} onChange={(event) => setQuery(event.target.value)} className={cn(getTypographyClassName("bodyMd"), "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)]")} /></label>
    <nav className="flex min-h-11 flex-wrap gap-2" aria-label="Media folders">{prefix ? <button type="button" onClick={() => navigate("")} className={cn(getTypographyClassName("buttonSecondary"), "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] px-3 transition-all")}>Library</button> : null}{crumbs.map((crumb, index) => <button type="button" key={`${crumb}-${index}`} onClick={() => navigate(crumbs.slice(0, index + 1).join("/"))} className={cn(getTypographyClassName("buttonSecondary"), "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] px-3 transition-all")}>{crumb}</button>)}</nav>
    {!deferredQuery ? (
      <div className="flex flex-col gap-2">
        <p className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Subfolders</p>
        <div className="grid gap-3 sm:grid-cols-2">
          {folders.map((folder) => (
            <div
              key={folder.prefix}
              className="flex items-center justify-between gap-2 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface-white)] p-2.5 shadow-2xs hover:border-[var(--color-accent)] transition-all"
            >
              <button
                type="button"
                onClick={() => navigate(folder.prefix)}
                className={cn(getTypographyClassName("bodyMd"), "flex-1 text-left text-[var(--color-on-surface)] hover:text-[var(--color-accent)] cursor-pointer truncate")}
              >
                📁 {folder.name}
              </button>
              {isFolderMode ? (
                <button
                  type="button"
                  onClick={() => onSelectFolder?.(folder.prefix)}
                  className={cn(getTypographyClassName("caption"), "rounded-[var(--radius-button)] bg-[var(--color-accent-wash)] px-2.5 py-1 text-[var(--color-accent)] hover:bg-[var(--color-accent)] hover:!text-white transition-colors cursor-pointer shrink-0")}
                >
                  Select folder
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => navigate(folder.prefix)}
                  className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)] hover:text-[var(--color-on-surface)] cursor-pointer")}
                >
                  Open →
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    ) : null}

    {/* Items / Thumbnail preview grid */}
    {items.length > 0 ? (
      <div className="flex flex-col gap-2 border-t border-[var(--color-border)] pt-3">
        <p className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
          {isFolderMode ? `Photos inside this folder (${items.length} indexed files)` : "Images in this folder"}
        </p>
        <div
          role={isFolderMode ? undefined : "listbox"}
          aria-multiselectable={!isFolderMode && selectionMode === "multiple"}
          aria-label={isFolderMode ? undefined : "Media library results"}
          className={cn("grid gap-3", GRID_COLUMNS_BY_SIZE[size])}
        >
          {items.map((item, index) => {
            const checked = selected.includes(item.r2Key);
            const isRovingFocusTarget = focusedKey ? focusedKey === item.r2Key : index === 0;
            return (
              <div
                key={item.r2Key}
                ref={(node) => { if (node) tileRefs.current.set(item.r2Key, node); else tileRefs.current.delete(item.r2Key); }}
                role={isFolderMode ? undefined : "option"}
                aria-selected={isFolderMode ? undefined : checked}
                tabIndex={isFolderMode ? undefined : isRovingFocusTarget ? 0 : -1}
                onFocus={() => setFocusedKey(item.r2Key)}
                onKeyDown={(event) => onTileKeyDown(event, index, item)}
                onClick={() => { if (!isFolderMode) toggle(item.r2Key); }}
                className={cn(
                  "content-visibility-auto rounded-[var(--radius-button)] border p-3 text-left transition-all",
                  !isFolderMode ? "cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)]" : "",
                  checked
                    ? "border-[var(--color-focus)] ring-2 ring-[var(--color-focus)] bg-[var(--color-surface-white)]"
                    : "border-[var(--color-border-strong)] bg-[var(--color-surface)]"
                )}
              >
                {item.previewUrl ? (
                  <img
                    src={item.previewUrl}
                    alt=""
                    loading="lazy"
                    className={cn(THUMBNAIL_HEIGHT_BY_SIZE[size], "w-full object-cover rounded-[var(--radius-button)]")}
                  />
                ) : (
                  <span className={cn(getTypographyClassName("caption"), THUMBNAIL_HEIGHT_BY_SIZE[size], "flex items-center justify-center text-[var(--color-muted)]")}>
                    {item.previewStatus === "pending" || item.previewStatus === "processing" ? "Preparing preview…" : "Preview unavailable"}
                  </span>
                )}
                <span className={cn(getTypographyClassName("bodySm"), "mt-2 block break-all text-[var(--color-on-surface)] truncate")}>
                  {item.fileName}
                </span>
                <span className={cn(getTypographyClassName("caption"), "mt-1 block text-[var(--color-muted)]")}>
                  {item.classification ?? "generic"} · {item.width && item.height ? `${item.width}×${item.height}` : item.previewStatus === "ready" ? "Preview ready" : "Preview pending"}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    ) : null}

    {!error && !folders.length && !items.length ? <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>{deferredQuery ? "No indexed media matches this search." : "No indexed media is available in this folder. Refresh from R2 to load recent files."}</p> : null}
    {nextCursor !== null ? <button type="button" onClick={() => setCursor(nextCursor)} className={cn(getTypographyClassName("buttonSecondary"), "min-h-11 w-fit rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] px-4 transition-all")}>Load more</button> : null}

    <div className="sticky bottom-0 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--color-border-strong)] bg-[var(--color-surface)] pt-3">
      {isFolderMode ? (
        <>
          <div className="flex flex-col min-w-0">
            <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>Active R2 Folder:</span>
            <span className={cn(getTypographyClassName("bodySm"), "font-mono text-[var(--color-on-surface)] truncate")}>
              {prefix ? `/${prefix}` : "/ (Root Directory)"}
            </span>
          </div>
          <button
            type="button"
            onClick={confirm}
            className={cn(
              getTypographyClassName("buttonPrimary"),
              "min-h-11 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-5 shadow-md border border-transparent transition-all cursor-pointer"
            )}
          >
            {prefix ? `Use current folder: /${prefix}` : "Use Root Folder"}
          </button>
        </>
      ) : (
        <>
          <span className={cn(getTypographyClassName("caption"), cardinalityError ? "text-rose-700" : "text-[var(--color-muted)]")}>
            {cardinalityError ?? `${selected.length}/${maxSelection} selected`}
          </span>
          <button type="button" disabled={!selected.length || Boolean(cardinalityError)} onClick={confirm} className={cn(getTypographyClassName("buttonPrimary"), "min-h-11 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-5 shadow-md border border-transparent transition-all disabled:opacity-50")}>{selectionMode === "multiple" ? "Add selected images" : "Use image"}</button>
        </>
      )}
    </div>
  </section>;
}
